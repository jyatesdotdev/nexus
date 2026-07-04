import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import TaskStatusUpdateEvent

from server import extract_city, WeatherAgentExecutor


def test_extract_city():
    assert extract_city("Weather in Tokyo") == "Tokyo"
    assert extract_city("weather in New York?") == "New York"
    assert extract_city("Paris") == "Paris"
    assert extract_city("What is the forecast?") == "London"


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
@respx.mock
async def test_weather_agent_success(mock_context, mock_event_queue):
    mock_context.get_user_input.return_value = "Weather in Berlin"

    mock_response = {
        "current_condition": [
            {"temp_F": "68", "temp_C": "20", "weatherDesc": [{"value": "Sunny"}]}
        ]
    }

    respx.get("https://wttr.in/Berlin?format=j1").respond(
        status_code=200, json=mock_response
    )

    executor = WeatherAgentExecutor()
    await executor.execute(mock_context, mock_event_queue)

    # Assert events were enqueued
    # EDUCATIONAL NOTE: We now enqueue 2 TaskStatusUpdateEvents (thinking and final result)
    # instead of 3 mixed events, which is more efficient and protocol-compliant.
    assert mock_event_queue.enqueue_event.call_count == 2

    # 1. Thinking status update
    thinking_event = mock_event_queue.enqueue_event.call_args_list[0][0][0]
    assert isinstance(thinking_event, TaskStatusUpdateEvent)
    assert thinking_event.final is False
    assert "Fetching weather data for **Berlin**" in thinking_event.status.message.parts[0].root.text

    # 2. Result status update
    result_event = mock_event_queue.enqueue_event.call_args_list[1][0][0]
    assert isinstance(result_event, TaskStatusUpdateEvent)
    assert result_event.final is True
    assert (
        "The current weather in **Berlin** is Sunny with a temperature of 68°F (20°C)."
        in result_event.status.message.parts[0].root.text
    )


@pytest.mark.asyncio
@respx.mock
async def test_weather_agent_api_error(mock_context, mock_event_queue):
    mock_context.get_user_input.return_value = "Atlantis"

    respx.get("https://wttr.in/Atlantis?format=j1").respond(status_code=404)

    executor = WeatherAgentExecutor()
    await executor.execute(mock_context, mock_event_queue)

    # Check the final event's message
    result_event = mock_event_queue.enqueue_event.call_args_list[1][0][0]
    assert (
        "Could not retrieve weather for Atlantis. The service returned status 404."
        in result_event.status.message.parts[0].root.text
    )


@pytest.mark.asyncio
@respx.mock
async def test_weather_agent_parse_error(mock_context, mock_event_queue):
    mock_context.get_user_input.return_value = "ErrorCity"

    respx.get("https://wttr.in/ErrorCity?format=j1").respond(
        status_code=200, json={"wrong_format": True}
    )

    executor = WeatherAgentExecutor()
    await executor.execute(mock_context, mock_event_queue)

    result_event = mock_event_queue.enqueue_event.call_args_list[1][0][0]
    assert (
        "Could not parse weather data for ErrorCity." in result_event.status.message.parts[0].root.text
    )


@pytest.mark.asyncio
@respx.mock
async def test_weather_agent_network_error(mock_context, mock_event_queue):
    mock_context.get_user_input.return_value = "NetworkErrorCity"

    respx.get("https://wttr.in/NetworkErrorCity?format=j1").mock(
        side_effect=httpx.RequestError("Connection failed", request=MagicMock())
    )

    executor = WeatherAgentExecutor()
    await executor.execute(mock_context, mock_event_queue)

    result_event = mock_event_queue.enqueue_event.call_args_list[1][0][0]
    assert (
        "A network error occurred while fetching the weather: Connection failed"
        in result_event.status.message.parts[0].root.text
    )
