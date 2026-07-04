import os
import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from google.genai import types

# Add root directory to path to import the orchestrator package
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from orchestrator.reviewer import REVIEW_METADATA_KEY, ReviewerEnforcementRunner

from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.memory.base_memory_service import BaseMemoryService
from google.adk.agents.base_agent import BaseAgent
from google.adk.sessions.session import Session

# EDUCATIONAL NOTE: Mocking async generators vs. coroutines.
# [Why] `Runner.run_async` is called (not awaited) and returns an async
# generator that the caller iterates with `async for`. A plain MagicMock
# return value cannot be iterated that way (and awaiting a MagicMock raises
# "TypeError: 'MagicMock' object can't be awaited"), so we give run_async a
# side_effect that returns a real async generator. Anything the code truly
# awaits (e.g. session_service methods) must be an AsyncMock instead.


def _async_gen(*events):
    """Build an async generator yielding the given events."""

    async def gen(*args, **kwargs):
        for event in events:
            yield event

    return gen


def _make_event(author: str, text: str, partial: bool = False) -> MagicMock:
    return MagicMock(
        author=author,
        content=types.Content(parts=[types.Part(text=text)]),
        partial=partial,
    )


def _text_of(event) -> str:
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return ""
    return "".join(p.text or "" for p in content.parts)


@pytest.fixture
def mock_runner():
    runner = MagicMock()

    # Use spec to mirror the real service interfaces; awaited methods are AsyncMock
    runner.session_service = MagicMock(spec=BaseSessionService)
    mock_session = MagicMock(spec=Session)
    mock_session.events = []
    mock_session.state = {}
    runner.session_service.get_session = AsyncMock(return_value=mock_session)
    runner.session_service.append_event = AsyncMock()

    runner.memory_service = MagicMock(spec=BaseMemoryService)

    runner.app_name = "test_app"
    runner.agent.name = "root_agent"
    runner.auto_create_session = True
    return runner


@pytest.fixture
def mock_reviewer_agent():
    # Use spec to pass Pydantic validation
    agent = MagicMock(spec=BaseAgent)
    agent.name = "reviewer_agent"
    return agent


async def _collect(enforcement_runner, prompt="Hello"):
    events = []
    async for event in enforcement_runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=types.Content(parts=[types.Part(text=prompt)]),
    ):
        events.append(event)
    return events


@pytest.mark.asyncio
async def test_reviewer_enforcement_approved(mock_runner, mock_reviewer_agent):
    """
    EDUCATIONAL NOTE: Test Programmatic Reviewer Enforcement (APPROVED)
    The draft streams through unchanged; the verdict is emitted as a
    content-less metadata notice, never as answer text.
    """
    enforcement_runner = ReviewerEnforcementRunner(mock_runner, mock_reviewer_agent)

    mock_runner.run_async = MagicMock(
        side_effect=_async_gen(_make_event("some_sub_agent", "This is a good response."))
    )

    # ReviewerEnforcementRunner builds a brand-new Runner for the review step;
    # patch the Runner class so no real ADK internals (which await real
    # session/memory services) are exercised.
    with patch("orchestrator.reviewer.Runner") as mock_runner_cls:
        review_runner = mock_runner_cls.return_value
        review_runner.run_async = MagicMock(
            side_effect=_async_gen(_make_event("reviewer_agent", "APPROVED"))
        )
        events = await _collect(enforcement_runner)

    # Draft event + one content-less review notice; no verdict text in stream.
    assert len(events) == 2
    assert "This is a good response." in _text_of(events[0])
    notice = events[1]
    assert notice.author == "reviewer_agent"
    assert _text_of(notice) == ""
    assert notice.custom_metadata[REVIEW_METADATA_KEY]["verdict"] == "approved"
    assert "APPROVED" in notice.custom_metadata[REVIEW_METADATA_KEY]["critique"]

    # Approved -> no revision cycle: the wrapped runner ran exactly once.
    assert mock_runner.run_async.call_count == 1

    # The review runner is built around the reviewer agent and the buffered
    # draft is embedded in the review prompt.
    assert mock_runner_cls.call_args.kwargs["agent"] is mock_reviewer_agent
    review_message = review_runner.run_async.call_args.kwargs["new_message"]
    assert "This is a good response." in review_message.parts[0].text


def _revision_setup(mock_runner_cls, critique, revised_events):
    """Wire the patched Runner class for a REVISION scenario.

    The production code constructs TWO fresh Runners on the revision path:
    first the review runner (in `_run_review`), then the revision runner
    (isolated scratch session). `side_effect` hands each construction its
    own mock, in that order.
    """
    review_runner = MagicMock()
    review_runner.run_async = MagicMock(
        side_effect=_async_gen(_make_event("reviewer_agent", critique))
    )
    revision_runner = MagicMock()
    revision_runner.run_async = MagicMock(side_effect=_async_gen(*revised_events))
    mock_runner_cls.side_effect = [review_runner, revision_runner]
    return review_runner, revision_runner


@pytest.mark.asyncio
async def test_reviewer_enforcement_revision_triggers_revised_answer(
    mock_runner, mock_reviewer_agent
):
    """
    EDUCATIONAL NOTE: Test Programmatic Reviewer Enforcement (REVISION)
    Streaming enforcement cannot retract already-streamed text, so on REVISION
    the runner emits the critique as a metadata notice and then runs exactly
    ONE revision cycle — the stream must END with a real revised answer. The
    revision runs in an ISOLATED scratch session (fresh Runner + in-memory
    session service), never through the wrapped runner's user session.
    """
    enforcement_runner = ReviewerEnforcementRunner(mock_runner, mock_reviewer_agent)

    mock_runner.run_async = MagicMock(
        side_effect=_async_gen(_make_event("some_sub_agent", "This response is bad."))
    )

    with patch("orchestrator.reviewer.Runner") as mock_runner_cls:
        review_runner, revision_runner = _revision_setup(
            mock_runner_cls,
            "REVISION: The tone is unprofessional.",
            [_make_event("some_sub_agent", "This is the revised answer.")],
        )
        events = await _collect(enforcement_runner)

    assert len(events) == 3
    # 1) draft, 2) content-less notice carrying the critique, 3) revised answer.
    assert "This response is bad." in _text_of(events[0])
    notice = events[1]
    assert _text_of(notice) == ""
    assert notice.custom_metadata[REVIEW_METADATA_KEY]["verdict"] == "revision"
    assert "unprofessional" in notice.custom_metadata[REVIEW_METADATA_KEY]["critique"]
    assert "This is the revised answer." in _text_of(events[2])

    # The raw critique text must never appear as content in the stream.
    assert all("REVISION:" not in _text_of(e) for e in events)

    # The wrapped runner (user session) ran ONLY for the draft; the revision
    # went through a separate Runner, and it is NOT re-reviewed.
    assert mock_runner.run_async.call_count == 1
    assert review_runner.run_async.call_count == 1
    assert revision_runner.run_async.call_count == 1
    revision_message = revision_runner.run_async.call_args.kwargs["new_message"]
    assert "The tone is unprofessional." in revision_message.parts[0].text
    assert "Hello" in revision_message.parts[0].text  # original request included

    # The revision runner is built around the SAME root agent but an isolated
    # in-memory session service — never the user's persistent one.
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    revision_build = mock_runner_cls.call_args_list[1].kwargs
    assert revision_build["agent"] is mock_runner.agent
    assert isinstance(revision_build["session_service"], InMemorySessionService)
    assert revision_build["session_service"] is not mock_runner.session_service


@pytest.mark.asyncio
async def test_revision_scaffolding_never_persists_in_user_session(
    mock_runner, mock_reviewer_agent
):
    """
    EDUCATIONAL NOTE: QA Scaffolding Must Not Persist as User History
    An earlier version re-ran the wrapped runner in the USER session, so the
    synthetic "automated QA retry" prompt was persisted as a user event —
    later turns and history replays could see pipeline scaffolding. The user
    session must gain exactly ONE event from a revision: the revised model
    answer, appended via the session service API.
    """
    from google.adk.events import Event as AdkEvent
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    # A user session with real prior history (the incident shape).
    user_session = MagicMock(spec=Session)
    user_session.state = {}
    user_session.events = [
        AdkEvent(
            author="user",
            content=types.Content(
                role="user",
                parts=[types.Part(text="Who is in the engineering department?")],
            ),
        ),
        AdkEvent(
            author="root_agent",
            content=types.Content(role="model", parts=[types.Part(text="Alice.")]),
        ),
    ]
    mock_runner.session_service.get_session = AsyncMock(return_value=user_session)

    enforcement_runner = ReviewerEnforcementRunner(mock_runner, mock_reviewer_agent)
    mock_runner.run_async = MagicMock(
        side_effect=_async_gen(
            _make_event(
                "weather_sub_agent",
                "The current weather in the engineering department is 81F.",
            )
        )
    )

    with patch("orchestrator.reviewer.Runner") as mock_runner_cls:
        _, revision_runner = _revision_setup(
            mock_runner_cls,
            "REVISION: 'the engineering department' is not a location.",
            [_make_event("weather_sub_agent", "Which city would you like?")],
        )
        events = await _collect(enforcement_runner, prompt="What's the weather like?")

    # The stream still ends with the revised answer.
    assert "Which city would you like?" in _text_of(events[-1])

    # The synthetic prompt went ONLY to the isolated revision runner.
    revision_message = revision_runner.run_async.call_args.kwargs["new_message"]
    assert "automated QA retry" in revision_message.parts[0].text

    # Exactly ONE write-back to the user session: the revised MODEL answer.
    # No user-authored scaffolding event is ever appended.
    append_calls = mock_runner.session_service.append_event.await_args_list
    assert len(append_calls) == 1
    appended_session, appended_event = append_calls[0].args
    assert appended_session is user_session
    assert appended_event.author == "weather_sub_agent"  # never "user"
    appended_text = "".join(p.text or "" for p in appended_event.content.parts)
    assert appended_text == "Which city would you like?"
    assert "automated QA retry" not in appended_text

    # The scratch session was seeded (via the service API) with copies of the
    # user's history — and contains no scaffolding either at seed time.
    scratch_service = mock_runner_cls.call_args_list[1].kwargs["session_service"]
    assert isinstance(scratch_service, InMemorySessionService)
    scratch_session = await scratch_service.get_session(
        app_name="test_app", user_id="test_user", session_id="test_session"
    )
    assert [e.author for e in scratch_session.events] == ["user", "root_agent"]
    # The user's own session object was never mutated by the seeding.
    assert len(user_session.events) == 2


@pytest.mark.asyncio
async def test_reviewer_buffers_only_authoritative_text(
    mock_runner, mock_reviewer_agent
):
    """
    EDUCATIONAL NOTE: Partial vs Authoritative Events
    In SSE streaming mode ADK yields incremental deltas (partial=True) AND a
    final aggregate event with the full text. Buffering both doubled the draft
    the reviewer saw ("the response is repetitive" on every request). Only the
    non-partial text may be buffered.
    """
    enforcement_runner = ReviewerEnforcementRunner(mock_runner, mock_reviewer_agent)

    mock_runner.run_async = MagicMock(
        side_effect=_async_gen(
            _make_event("some_sub_agent", "The answer is ", partial=True),
            _make_event("some_sub_agent", "42.", partial=True),
            _make_event("some_sub_agent", "The answer is 42."),  # final aggregate
        )
    )

    with patch("orchestrator.reviewer.Runner") as mock_runner_cls:
        review_runner = mock_runner_cls.return_value
        review_runner.run_async = MagicMock(
            side_effect=_async_gen(_make_event("reviewer_agent", "APPROVED"))
        )
        await _collect(enforcement_runner)

    review_message = review_runner.run_async.call_args.kwargs["new_message"]
    assert review_message.parts[0].text.count("The answer is 42.") == 1


@pytest.mark.asyncio
async def test_review_runs_in_isolated_session(mock_runner, mock_reviewer_agent):
    """
    EDUCATIONAL NOTE: Out-of-Band Review
    The review must never touch the user's persistent session: recording the
    REVIEW REQUEST / verdict there contaminated every later turn's review with
    earlier topics. The review Runner gets fresh in-memory services and a
    dedicated session id.
    """
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService

    enforcement_runner = ReviewerEnforcementRunner(mock_runner, mock_reviewer_agent)
    mock_runner.run_async = MagicMock(
        side_effect=_async_gen(_make_event("some_sub_agent", "A fine draft."))
    )

    with patch("orchestrator.reviewer.Runner") as mock_runner_cls:
        review_runner = mock_runner_cls.return_value
        review_runner.run_async = MagicMock(
            side_effect=_async_gen(_make_event("reviewer_agent", "APPROVED"))
        )
        await _collect(enforcement_runner)

    build_kwargs = mock_runner_cls.call_args.kwargs
    assert isinstance(build_kwargs["session_service"], InMemorySessionService)
    assert isinstance(build_kwargs["memory_service"], InMemoryMemoryService)
    assert build_kwargs["session_service"] is not mock_runner.session_service
    run_kwargs = review_runner.run_async.call_args.kwargs
    assert run_kwargs["session_id"] == "review_test_session"


@pytest.mark.asyncio
async def test_empty_verdict_fails_open(mock_runner, mock_reviewer_agent):
    """A reviewer that produces no text must not block or mangle the answer."""
    enforcement_runner = ReviewerEnforcementRunner(mock_runner, mock_reviewer_agent)
    mock_runner.run_async = MagicMock(
        side_effect=_async_gen(_make_event("some_sub_agent", "A fine draft."))
    )

    with patch("orchestrator.reviewer.Runner") as mock_runner_cls:
        review_runner = mock_runner_cls.return_value
        review_runner.run_async = MagicMock(side_effect=_async_gen())
        events = await _collect(enforcement_runner)

    assert len(events) == 2
    assert events[1].custom_metadata[REVIEW_METADATA_KEY]["verdict"] == "approved"
    assert mock_runner.run_async.call_count == 1  # no revision cycle
