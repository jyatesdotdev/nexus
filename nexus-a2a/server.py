"""
CONCEPT: Agent-to-Agent (A2A) Protocol
This module implements a standalone A2A-compliant sub-agent.
"""

import uvicorn
import uuid
import os
import httpx

# EDUCATIONAL NOTE: Importing types for static analysis and better IDE support.
# WHY: Type hints (e.g., ': RequestContext') help developers understand what data
# structures are expected, making the code more maintainable and less error-prone.
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
    Message,
    TextPart,
    Role,
    TaskStatusUpdateEvent,
    TaskStatus,
    TaskState,
)

# ==========================================
# 1. A2A Agent Executor
# ==========================================


def extract_city(user_message: str) -> str:
    """
    Extracts the city name from a given natural language user message.

    Args:
        user_message (str): The text input from the user.

    Returns:
        str: The extracted city name as a string, or 'London' as a fallback.
    """
    city = "London"
    words = user_message.split()
    if "in" in words:
        try:
            idx = words.index("in")
            city = " ".join(words[idx + 1 :]).strip("?")
        except IndexError:
            pass
    elif len(words) > 0 and not any(
        w in user_message.lower() for w in ["what", "how", "weather", "forecast"]
    ):
        city = user_message.strip("?")
    return city


# EDUCATIONAL NOTE: WeatherAgentExecutor inherits from AgentExecutor.
# WHY: This ensures our class implements the required interface ('execute' and 'cancel' methods)
# so it can be used by the A2A SDK's request handlers.
class WeatherAgentExecutor(AgentExecutor):
    """A sub-agent that provides weather forecasts via the A2A protocol."""

    # EDUCATIONAL NOTE: The 'async' keyword defines a coroutine.
    # HOW: Using 'async def' allows this function to run concurrently.
    # WHY: In a web server, we don't want one request to block others. 'await' tells
    # Python it can pause this function and do other work while waiting for I/O
    # (like the network request to wttr.in).
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Processes an incoming A2A request by fetching weather data.

        Args:
            context (RequestContext): The A2A request context containing the user's input.
            event_queue (EventQueue): The queue to which A2A events are sent.
        """
        user_message = context.get_user_input()
        print(f"A2A Sub-Agent received: {user_message}")

        city = extract_city(user_message)
        response_text = "I am a specialized Weather Agent. Let me check that for you..."

        try:
            # Send an initial "thinking" message
            thinking_msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.agent,
                parts=[TextPart(text=f"Fetching weather data for **{city}** from wttr.in...\n")],  # type: ignore[list-item]
            )
            # EDUCATIONAL NOTE: We 'await' the enqueuing of the event because it might involve
            # asynchronous I/O (like writing to a stream or a database).
            await event_queue.enqueue_event(thinking_msg)

            # EDUCATIONAL NOTE: 'async with' ensures resources are cleaned up.
            # WHY: Using 'httpx.AsyncClient()' in a context manager automatically closes
            # the underlying connection pool when the block finishes, preventing memory leaks.
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use wttr.in for a simple, no-auth public API
                resp = await client.get(f"https://wttr.in/{city}?format=j1")
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        current = data["current_condition"][0]
                        temp_f = current["temp_F"]
                        temp_c = current["temp_C"]
                        desc = current["weatherDesc"][0]["value"]
                        response_text = f"The current weather in **{city}** is {desc} with a temperature of {temp_f}°F ({temp_c}°C)."
                    except (KeyError, IndexError, ValueError):
                        response_text = f"Could not parse weather data for {city}. The service returned an unexpected format."
                else:
                    response_text = f"Could not retrieve weather for {city}. The service returned status {resp.status_code}."
        except httpx.RequestError as req_err:
            response_text = (
                f"A network error occurred while fetching the weather: {req_err}"
            )
        except Exception as e:
            # EDUCATIONAL NOTE: Catching exceptions prevents the whole server from crashing.
            response_text = (
                f"An unexpected error occurred while processing the request: {e}"
            )

        # Construct the final A2A-compliant message
        response = Message(
            message_id=str(uuid.uuid4()),
            role=Role.agent,
            parts=[TextPart(text=response_text)],  # type: ignore[list-item]
        )

        # Enqueue the message to send it back to the orchestrator
        await event_queue.enqueue_event(response)

        # Signal that the task is complete
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                final=True,
                status=TaskStatus(state=TaskState.completed),
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handles task cancellation if the orchestrator aborts the request."""
        pass


# ==========================================
# 2. Server Configuration
# ==========================================

# EDUCATIONAL NOTE: Using os.getenv to read configuration from the system.
# WHY: This is a "12-Factor App" best practice. It allows the same code to run
# in different environments (development, staging, production) without modification.
HOST = os.getenv("A2A_HOST", "0.0.0.0")
# EDUCATIONAL NOTE: os.getenv returns a string, so we must convert it to an int for the port.
PORT = int(os.getenv("A2A_PORT", "8001"))
PUBLIC_URL = os.getenv("A2A_PUBLIC_URL", f"http://a2a-agent:{PORT}")

# 1. Define the Agent's "Business Card"
# HOW: We create an AgentCard object detailing the agent's metadata and skills.
# WHY: This is the core of the A2A discovery protocol. It tells the Root Orchestrator
# exactly what this sub-agent can do, avoiding the need to hardcode routing logic
# and schemas in the orchestrator.
agent_card = AgentCard(
    name="Weather Sub-Agent",
    description="Provides localized weather forecasts via A2A.",
    url=PUBLIC_URL,
    version="1.0.0",
    skills=[
        AgentSkill(
            description="Returns current weather conditions.",
            id="weather_forecast",
            name="Weather Forecast",
            examples=["What is the weather like?", "Give me a forecast"],
            tags=["weather", "forecast"],
        )
    ],
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
)

# 2. Initialize the A2A Request Handler
handler = DefaultRequestHandler(
    agent_executor=WeatherAgentExecutor(), task_store=InMemoryTaskStore()
)

# 3. Build the Starlette Application
# HOW: We use A2AStarletteApplication to wrap our handler and agent card into an ASGI app.
# WHY: This automatically handles the JSON-RPC endpoints, routing, and schema validation
# required to comply with the A2A standard over HTTP.
app_builder = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
app = app_builder.build()

# EDUCATIONAL NOTE: This code only runs if the script is executed directly (not imported).
# WHY: This prevents the server from starting automatically if we just wanted to
# import some classes or variables from this file in a test or another module.
if __name__ == "__main__":
    print(f"Starting A2A Weather Sub-Agent on {HOST}:{PORT}...")
    # uvicorn.run: Starts the ASGI server to listen for incoming HTTP requests.
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True)
