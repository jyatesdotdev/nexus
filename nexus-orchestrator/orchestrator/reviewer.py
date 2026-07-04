from typing import Any, AsyncGenerator, List, Optional

from google.adk.agents.llm_agent import LlmAgent as Agent
from google.adk.events import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import Content, Part

# Key under which the review outcome travels in Event.custom_metadata.
# Shared with app.run_chat_loop (CLI rendering); clients that only render
# content text (the demo script, nexus-ui) ignore the notice event entirely.
REVIEW_METADATA_KEY = "nexus_review"


# EDUCATIONAL NOTE: Runner Decorators (Governance Pipeline)
# [Why] ADK Runners are wrapped, not subclassed: each wrapper intercepts
# run_async and forwards everything else via __getattr__, so cross-cutting
# concerns (loop detection, reviewer enforcement) compose like middleware
# around any Runner implementation.
class LoopDetectionRunner:
    """Detects infinite loops between sub-agents."""
    def __init__(self, runner: Any):
        self._runner = runner

    async def run_async(self, *args: Any, **kwargs: Any) -> Any:
        author_sequence: List[str] = []
        async for event in self._runner.run_async(*args, **kwargs):
            if hasattr(event, "author") and getattr(event, "author", None):
                author = event.author
                if not author_sequence or author_sequence[-1] != author:
                    author_sequence.append(author)
                    if len(author_sequence) > 10:
                        print("Loop detected in agent messages!")
            yield event

    def __getattr__(self, name: str) -> Any:
        return getattr(self._runner, name)


class ReviewerEnforcementRunner:
    """
    EDUCATIONAL NOTE: Programmatic Reviewer Enforcement (Streaming-Safe)
    [Why] While prompt-based instructions are helpful, code-level enforcement
    guarantees that the Critic/Reviewer pattern is followed. This middleware
    intercepts the final response from the orchestrator and passes it to the
    QA agent for mandatory validation.

    [Why streaming changes the design] Enforcement on a streaming path cannot
    retract text the user has already seen, and SSE clients (the demo script,
    nexus-ui) treat the LAST non-partial content event as the authoritative
    answer. So the raw reviewer verdict must never be emitted as a content
    event — an earlier version did exactly that, and every user-facing answer
    became "REVISION: ...". The semantics are therefore:

      1. Stream the draft answer through unchanged.
      2. Review it OUT-OF-BAND (isolated in-memory session — see below).
      3. Emit ONE content-less notice event whose custom_metadata carries the
         verdict + critique. Text-rendering clients skip it; the CLI and
         curious UIs can surface it as a system-level notice.
      4. If the verdict is REVISION, run exactly ONE revision cycle in an
         ISOLATED scratch session seeded from the user's history, stream its
         events, and append only the revised ANSWER to the user's session —
         see run_async step 4. The revision is not re-reviewed: a stubborn
         reviewer must not be able to loop the pipeline forever.

    [Why the review is isolated] The review runner gets fresh InMemory
    session/memory services instead of the user's persistent session. If the
    review ran inside the user's session (as it originally did), every turn
    would append "REVIEW REQUEST ..." user events and verdict model events to
    persistent history, and two bugs follow: later turns' reviews get
    contaminated by earlier topics, and the buffered draft text the reviewer
    sees stops matching what the user saw.
    """
    def __init__(self, runner: Runner, reviewer_agent: Agent):
        self._runner = runner
        self._reviewer_agent = reviewer_agent

    async def run_async(
        self, user_id: str, session_id: str, new_message: Content, **kwargs: Any
    ) -> AsyncGenerator[Any, None]:
        # 1. Stream the draft answer unchanged while buffering its
        # authoritative text for review.
        draft_text = ""
        async for event in self._runner.run_async(
            user_id=user_id, session_id=session_id, new_message=new_message, **kwargs
        ):
            draft_text += self._authoritative_text(event)
            yield event

        if not draft_text.strip():
            return

        # 2. Out-of-band review.
        user_request = _content_text(new_message)
        verdict = await self._run_review(user_id, session_id, user_request, draft_text)
        approved = self._is_approved(verdict)

        # 3. Content-less notice event: metadata only, never answer text.
        yield Event(
            author="reviewer_agent",
            custom_metadata={
                REVIEW_METADATA_KEY: {
                    "verdict": "approved" if approved else "revision",
                    "critique": verdict,
                }
            },
        )

        if approved:
            return

        # 4. Exactly one revision cycle, run OUT-OF-BAND like the review.
        #
        # EDUCATIONAL NOTE: QA Scaffolding Must Not Persist as User History
        # [Why] An earlier version re-ran the wrapped runner in the USER
        # session, so the synthetic "For context: this is an automated QA
        # retry..." message was persisted by the session service as a USER
        # event — pipeline scaffolding that later turns and history replays
        # could see (and that Redis session forensics did see). Instead, the
        # revision now runs in a throwaway InMemorySessionService seeded —
        # via the BaseSessionService API, so it works identically for
        # Redis/Postgres-backed sessions — with a copy of the user session's
        # events. Its events still stream to the client (the stream must end
        # with a real answer), but only ONE thing is written back to the
        # user's persistent session: a model event carrying the revised
        # answer, appended through session_service.append_event.
        #
        # EDUCATIONAL NOTE: Prompt Shape Matters Downstream
        # [Why] The revision message may be re-delegated verbatim to remote
        # sub-agents that parse it naively (nexus-a2a's extract_city reads the
        # words after "in"!). So the message leads with the ORIGINAL user
        # request and appends the QA critique after the "For context:" marker,
        # which downstream parsers in this workspace are documented to strip
        # (see nexus-a2a/AGENTS.md).
        revision_prompt = (
            f"{user_request}\n"
            "For context: this is an automated QA retry, not a new end-user "
            "message. A quality reviewer rejected the previous draft with this "
            f"critique: {verdict}\n"
            "Produce the corrected FINAL answer to the request above. Reply "
            "with the revised answer only — do not mention the review process."
        )
        # Only run_config is forwarded (invocation_id/state_delta from the
        # original request must not be replayed).
        revision_kwargs = {}
        if "run_config" in kwargs:
            revision_kwargs["run_config"] = kwargs["run_config"]

        session_service = self._runner.session_service
        user_session = await session_service.get_session(
            app_name=self._runner.app_name, user_id=user_id, session_id=session_id
        )

        # Seed the scratch session through the service API only: create it,
        # then replay copies of the user's events with append_event (which
        # also rebuilds session state from the events' state deltas).
        scratch_service = InMemorySessionService()  # type: ignore[no-untyped-call]
        scratch_session = await scratch_service.create_session(
            app_name=self._runner.app_name,
            user_id=user_id,
            session_id=session_id,
            state=dict(user_session.state) if user_session else None,
        )
        for past_event in user_session.events if user_session else []:
            await scratch_service.append_event(
                scratch_session, past_event.model_copy(deep=True)
            )

        revision_runner = Runner(
            app_name=self._runner.app_name,
            agent=self._runner.agent,
            session_service=scratch_service,
            memory_service=self._runner.memory_service,
        )

        # Stream the revision; the LAST authoritative content event is what
        # SSE clients display as the answer, so that is what gets persisted.
        revised_text = ""
        revised_author = getattr(self._runner.agent, "name", None) or "root_agent"
        async for event in revision_runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=Content(role="user", parts=[Part(text=revision_prompt)]),
            **revision_kwargs,
        ):
            text = self._authoritative_text(event)
            if text.strip():
                revised_text = text
                revised_author = getattr(event, "author", None) or revised_author
            yield event

        # Persist ONLY the revised answer to the user's session. The event is
        # rebuilt clean (author + text) so no revision-run actions/state
        # deltas leak into persistent history.
        if revised_text.strip() and user_session is not None:
            await session_service.append_event(
                user_session,
                Event(
                    author=revised_author,
                    content=Content(role="model", parts=[Part(text=revised_text)]),
                ),
            )

    @staticmethod
    def _authoritative_text(event: Any) -> str:
        """Text of a non-partial, non-reviewer event ('' otherwise).

        EDUCATIONAL NOTE: Partial vs Authoritative Events
        [Why] In SSE streaming mode ADK yields both incremental deltas
        (partial=True) AND a final aggregate event carrying the full text.
        Summing text across ALL events therefore doubles the draft — which is
        exactly the bug that made the reviewer complain every response was
        "repetitive". Only non-partial events count.
        """
        if getattr(event, "partial", False):
            return ""
        if getattr(event, "author", None) == "reviewer_agent":
            return ""
        return _content_text(getattr(event, "content", None))

    async def _run_review(
        self, user_id: str, session_id: str, user_request: str, draft_text: str
    ) -> str:
        """Runs the reviewer agent in an isolated session; returns its verdict text."""
        review_prompt = (
            "REVIEW REQUEST:\n"
            f'The user asked: "{user_request}"\n'
            "The following draft response was generated for the user. Does it "
            "answer the request and meet our quality standards?\n"
            "If yes, reply with 'APPROVED'. If no, reply with 'REVISION: <reason>'.\n\n"
            f'Draft response: "{draft_text}"'
        )
        # Fresh in-memory services: the review must never touch the user's
        # persistent session (see class docstring).
        review_runner = Runner(
            app_name=self._runner.app_name,
            agent=self._reviewer_agent,
            session_service=InMemorySessionService(),  # type: ignore[no-untyped-call]
            memory_service=InMemoryMemoryService(),  # type: ignore[no-untyped-call]
            auto_create_session=True,
        )
        verdict = ""
        async for review_event in review_runner.run_async(
            user_id=user_id,
            session_id=f"review_{session_id}",
            new_message=Content(role="user", parts=[Part(text=review_prompt)]),
        ):
            if not getattr(review_event, "partial", False):
                verdict += _content_text(getattr(review_event, "content", None))
        return verdict.strip()

    @staticmethod
    def _is_approved(verdict: str) -> bool:
        # Fail open on an empty verdict (reviewer produced nothing): in a lab
        # setting an unreviewed answer beats an infinite wait or a dropped one.
        if not verdict:
            return True
        normalized = verdict.upper()
        if "REVISION" in normalized:
            return False
        return "APPROVED" in normalized

    def __getattr__(self, name: str) -> Any:
        """EDUCATIONAL NOTE: Delegate all other calls to the underlying Runner."""
        return getattr(self._runner, name)


def _content_text(content: Optional[Content]) -> str:
    """Concatenated text parts of a Content ('' when absent)."""
    if not content or not content.parts:
        return ""
    return "".join(part.text for part in content.parts if part.text)


def build_governed_runner(runner: Any, agent: Any, enforce_review: bool) -> Any:
    """
    Wraps a raw ADK Runner in the standard governance pipeline:
    Runner -> LoopDetectionRunner -> ReviewerEnforcementRunner.

    EDUCATIONAL NOTE: Single Wrapping Seam
    [Why] Both execution paths — the CLI/evals path (app.get_runner) and the
    HTTP path (server.GovernedAdkWebServer) — must apply the exact same
    governance pipeline, otherwise UI traffic silently bypasses the reviewer
    while CLI traffic gets reviewed. Centralizing the wrapping here guarantees
    the two paths cannot drift apart.

    The reviewer step is applied only when `enforce_review` is True (driven by
    the REVIEWER_ENFORCEMENT config flag) AND the agent actually has a
    sub-agent literally named "reviewer_agent" (a load-bearing string shared
    with agents/core_agents.py).
    """
    governed: Any = LoopDetectionRunner(runner)
    if enforce_review:
        sub_agents = getattr(agent, "sub_agents", None) or []
        reviewer_agent = next(
            (a for a in sub_agents if a.name == "reviewer_agent"), None
        )
        if reviewer_agent:
            governed = ReviewerEnforcementRunner(governed, reviewer_agent)
    return governed
