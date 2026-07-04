from typing import AsyncGenerator, List, Any
from google.adk.runners import Runner
from google.genai.types import Content, Part
from google.adk.agents.llm_agent import LlmAgent as Agent


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
    EDUCATIONAL NOTE: Programmatic Reviewer Enforcement
    [Why] While prompt-based instructions are helpful, code-level enforcement 
    guarantees that the Critic/Reviewer pattern is followed. This middleware
    intercepts the final response from the orchestrator and passes it to the
    QA agent for mandatory validation.
    """
    def __init__(self, runner: Runner, reviewer_agent: Agent):
        self._runner = runner
        self._reviewer_agent = reviewer_agent

    async def run_async(
        self, user_id: str, session_id: str, new_message: Content, **kwargs
    ) -> AsyncGenerator[Any, None]:
        # 1. Capture the output of the sub-agents
        full_response_text = ""
        last_event = None
        
        # We run the internal agents. We still stream events to the user (optional),
        # but we buffer the final text for review.
        async for event in self._runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message, **kwargs):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        # In a real system, you might want to only buffer 'model' responses, 
                        # but ADK events already distinguish authors.
                        if event.author != "reviewer_agent":
                            full_response_text += part.text
            last_event = event
            yield event # Stream it as normal for the 'thought process'

        # 2. Programmatic Review Step
        # If we have a response and it's not already from the reviewer, review it.
        if full_response_text and last_event.author != "reviewer_agent":
            review_prompt = (
                f"REVIEW REQUEST:\n"
                f"The following response was generated for the user. Does it meet our quality standards?\n"
                f"If yes, reply with 'APPROVED'. If no, provide the reason for REVISION.\n\n"
                f"Response: \"{full_response_text}\""
            )
            
            review_message = Content(parts=[Part(text=review_prompt)])
            
            # Use a new runner instance specifically for the reviewer_agent
            # This ensures the review is recorded in the session history if desired.
            review_runner = Runner(
                app_name=self._runner.app_name,
                agent=self._reviewer_agent,
                session_service=self._runner.session_service,
                memory_service=self._runner.memory_service,
                auto_create_session=self._runner.auto_create_session
            )
            
            async for review_event in review_runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=review_message,
            ):
                yield review_event

    def __getattr__(self, name):
        """EDUCATIONAL NOTE: Delegate all other calls to the underlying Runner."""
        return getattr(self._runner, name)


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
