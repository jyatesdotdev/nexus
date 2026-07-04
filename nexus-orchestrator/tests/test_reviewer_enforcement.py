import os
import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from google.genai import types

# Add root directory to path to import the orchestrator package
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from orchestrator.reviewer import ReviewerEnforcementRunner

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


def _make_event(author: str, text: str) -> MagicMock:
    return MagicMock(
        author=author,
        content=types.Content(parts=[types.Part(text=text)]),
        partial=False,
    )


@pytest.fixture
def mock_runner():
    runner = MagicMock()

    # Use spec to mirror the real service interfaces; awaited methods are AsyncMock
    runner.session_service = MagicMock(spec=BaseSessionService)
    mock_session = MagicMock(spec=Session)
    mock_session.events = []
    runner.session_service.get_session = AsyncMock(return_value=mock_session)

    runner.memory_service = MagicMock(spec=BaseMemoryService)

    runner.app_name = "test_app"
    runner.auto_create_session = True
    return runner


@pytest.fixture
def mock_reviewer_agent():
    # Use spec to pass Pydantic validation
    agent = MagicMock(spec=BaseAgent)
    agent.name = "reviewer_agent"
    return agent


@pytest.mark.asyncio
async def test_reviewer_enforcement_approved(mock_runner, mock_reviewer_agent):
    """
    EDUCATIONAL NOTE: Test Programmatic Reviewer Enforcement (APPROVED)
    Verify that when the reviewer approves, the original response is still returned.
    """
    enforcement_runner = ReviewerEnforcementRunner(mock_runner, mock_reviewer_agent)

    # The wrapped runner streams the orchestrator/sub-agent output
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

        events = []
        async for event in enforcement_runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=types.Content(parts=[types.Part(text="Hello")]),
        ):
            events.append(event)

    # We expect 2 events: the original one and the reviewer's approval
    assert len(events) == 2
    assert "This is a good response." in events[0].content.parts[0].text
    assert "APPROVED" in events[1].content.parts[0].text
    assert events[1].author == "reviewer_agent"

    # The review runner must be built around the reviewer agent and the
    # buffered response must be embedded in the review prompt.
    assert mock_runner_cls.call_args.kwargs["agent"] is mock_reviewer_agent
    review_message = review_runner.run_async.call_args.kwargs["new_message"]
    assert "This is a good response." in review_message.parts[0].text


@pytest.mark.asyncio
async def test_reviewer_enforcement_revision_needed(mock_runner, mock_reviewer_agent):
    """
    EDUCATIONAL NOTE: Test Programmatic Reviewer Enforcement (REVISION)
    Verify that when the reviewer requests a revision, the critique is returned.
    """
    enforcement_runner = ReviewerEnforcementRunner(mock_runner, mock_reviewer_agent)

    mock_runner.run_async = MagicMock(
        side_effect=_async_gen(_make_event("some_sub_agent", "This response is bad."))
    )

    with patch("orchestrator.reviewer.Runner") as mock_runner_cls:
        review_runner = mock_runner_cls.return_value
        review_runner.run_async = MagicMock(
            side_effect=_async_gen(
                _make_event("reviewer_agent", "REVISION: The tone is unprofessional.")
            )
        )

        events = []
        async for event in enforcement_runner.run_async(
            user_id="test_user",
            session_id="test_session",
            new_message=types.Content(parts=[types.Part(text="Hello")]),
        ):
            events.append(event)

    assert len(events) == 2
    assert "REVISION:" in events[1].content.parts[0].text
    assert "The tone is unprofessional." in events[1].content.parts[0].text
    assert events[1].author == "reviewer_agent"
