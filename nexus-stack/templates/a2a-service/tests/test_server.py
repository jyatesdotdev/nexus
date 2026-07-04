import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import TaskStatusUpdateEvent

from server import process_query, __SERVICE_TITLE__AgentExecutor


def test_process_query():
    assert process_query("ping") == "ping"
    assert process_query("ping?") == "ping"
    # The orchestrator appends delegation context after "For context:" — the
    # domain function must strip it.
    assert process_query("ping For context: the user asked nicely") == "ping"
    assert process_query("") == "an empty request"


@pytest.fixture
def mock_context():
    context = MagicMock(spec=RequestContext)
    context.task_id = "test-task"
    context.context_id = "test-context"
    return context


@pytest.fixture
def mock_event_queue():
    queue = AsyncMock(spec=EventQueue)
    return queue


@pytest.mark.asyncio
async def test_execute_two_phase_contract(mock_context, mock_event_queue, monkeypatch):
    """Pins the streaming contract: exactly two TaskStatusUpdateEvents,
    a non-final 'thinking' update followed by a final result."""
    monkeypatch.delenv("EXTERNAL_API_URL", raising=False)
    mock_context.get_user_input.return_value = "ping"

    executor = __SERVICE_TITLE__AgentExecutor()
    await executor.execute(mock_context, mock_event_queue)

    assert mock_event_queue.enqueue_event.call_count == 2

    # 1. Thinking status update
    thinking_event = mock_event_queue.enqueue_event.call_args_list[0][0][0]
    assert isinstance(thinking_event, TaskStatusUpdateEvent)
    assert thinking_event.final is False
    assert "Working on **ping**" in thinking_event.status.message.parts[0].root.text

    # 2. Result status update
    result_event = mock_event_queue.enqueue_event.call_args_list[1][0][0]
    assert isinstance(result_event, TaskStatusUpdateEvent)
    assert result_event.final is True
    assert (
        "processed your request: **ping**"
        in result_event.status.message.parts[0].root.text
    )


@pytest.mark.asyncio
@respx.mock
async def test_execute_with_external_api(mock_context, mock_event_queue, monkeypatch):
    """Demonstrates the respx mocking pattern for the external-API boundary."""
    monkeypatch.setenv("EXTERNAL_API_URL", "https://api.example.test/data")
    mock_context.get_user_input.return_value = "ping"

    respx.get("https://api.example.test/data?q=ping").respond(
        status_code=200, json={"status": "ok"}
    )

    executor = __SERVICE_TITLE__AgentExecutor()
    await executor.execute(mock_context, mock_event_queue)

    result_event = mock_event_queue.enqueue_event.call_args_list[1][0][0]
    assert result_event.final is True
    assert "with external data" in result_event.status.message.parts[0].root.text


@pytest.mark.asyncio
@respx.mock
async def test_execute_external_api_http_error(
    mock_context, mock_event_queue, monkeypatch
):
    monkeypatch.setenv("EXTERNAL_API_URL", "https://api.example.test/data")
    mock_context.get_user_input.return_value = "ping"

    respx.get("https://api.example.test/data?q=ping").respond(status_code=503)

    executor = __SERVICE_TITLE__AgentExecutor()
    await executor.execute(mock_context, mock_event_queue)

    result_event = mock_event_queue.enqueue_event.call_args_list[1][0][0]
    assert (
        "The external service returned status 503."
        in result_event.status.message.parts[0].root.text
    )


@pytest.mark.asyncio
@respx.mock
async def test_execute_external_api_network_error(
    mock_context, mock_event_queue, monkeypatch
):
    monkeypatch.setenv("EXTERNAL_API_URL", "https://api.example.test/data")
    mock_context.get_user_input.return_value = "ping"

    respx.get("https://api.example.test/data?q=ping").mock(
        side_effect=httpx.RequestError("Connection failed", request=MagicMock())
    )

    executor = __SERVICE_TITLE__AgentExecutor()
    await executor.execute(mock_context, mock_event_queue)

    result_event = mock_event_queue.enqueue_event.call_args_list[1][0][0]
    assert (
        "A network error occurred while processing ping: Connection failed"
        in result_event.status.message.parts[0].root.text
    )
