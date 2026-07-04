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
      4. If the verdict is REVISION, run exactly ONE revision cycle through
         the wrapped runner (same user session), so the stream always ends
         with a real answer. The revision is not re-reviewed: a stubborn
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

        # 4. Exactly one revision cycle through the wrapped runner. The
        # corrective instruction and the revised answer become regular events
        # in the user's real session, so history stays coherent for later
        # turns. Only run_config is forwarded (invocation_id/state_delta from
        # the original request must not be replayed).
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
        revision_kwargs = {}
        if "run_config" in kwargs:
            revision_kwargs["run_config"] = kwargs["run_config"]
        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=Content(role="user", parts=[Part(text=revision_prompt)]),
            **revision_kwargs,
        ):
            yield event

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
