"""
CONCEPT: Agent-to-Agent (A2A) Protocol
This module implements a standalone A2A-compliant sub-agent.
"""

import uvicorn
import uuid
import os
import httpx

# TYPE HINTING: Importing types for static analysis and better IDE support.
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
    TaskState
)

# ==========================================
# 1. A2A Agent Executor
# ==========================================

# INHERITANCE: WeatherAgentExecutor inherits from AgentExecutor.
# WHY: This ensures our class implements the required interface ('execute' and 'cancel' methods)
# so it can be used by the A2A SDK's request handlers.
class WeatherAgentExecutor(AgentExecutor):
    """A sub-agent that provides weather forecasts via the A2A protocol."""
    
    # ASYNC/AWAIT: The 'async' keyword defines a coroutine.
    # HOW: Using 'async def' allows this function to run concurrently.
    # WHY: In a web server, we don't want one request to block others. 'await' tells
    # Python it can pause this function and do other work while waiting for I/O 
    # (like the network request to wttr.in).
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Processes an incoming A2A request.
        """
        user_message = context.get_user_input()
        print(f"A2A Sub-Agent received: {user_message}")
        
        # Simple extraction logic (in a real app, use an LLM or NLP library to extract the city)
        city = "London" # Default
        words = user_message.split()
        if "in" in words:
            try:
                idx = words.index("in")
                city = words[idx + 1].strip("?")
            except IndexError:
                pass
        elif len(words) > 0 and not any(w in user_message.lower() for w in ["what", "how", "weather", "forecast"]):
            # If the user just typed a city name
            city = user_message.strip("?")

        response_text = "I am a specialized Weather Agent. Let me check that for you..."

        try:
            # Send an initial "thinking" message
            thinking_msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.agent,
                parts=[TextPart(text=f"Fetching weather data for **{city}** from wttr.in...\n")]
            )
            # AWAIT: We 'await' the enqueuing of the event because it might involve 
            # asynchronous I/O (like writing to a stream or a database).
            await event_queue.enqueue_event(thinking_msg)

            # CONTEXT MANAGER: 'async with' ensures resources are cleaned up.
            # WHY: Using 'httpx.AsyncClient()' in a context manager automatically closes 
            # the underlying connection pool when the block finishes, preventing memory leaks.
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use wttr.in for a simple, no-auth public API
                resp = await client.get(f"https://wttr.in/{city}?format=j1")
                if resp.status_code == 200:
                    data = resp.json()
                    current = data['current_condition'][0]
                    temp_f = current['temp_F']
                    temp_c = current['temp_C']
                    desc = current['weatherDesc'][0]['value']
                    
                    response_text = f"The current weather in **{city}** is {desc} with a temperature of {temp_f}°F ({temp_c}°C)."
                else:
                    response_text = f"Could not retrieve weather for {city}. The service returned status {resp.status_code}."
        except Exception as e:
            # ERROR HANDLING: Catching exceptions prevents the whole server from crashing.
            response_text = f"An error occurred while fetching the weather: {e}"

        # Construct the final A2A-compliant message
        response = Message(
            message_id=str(uuid.uuid4()),
            role=Role.agent,
            parts=[TextPart(text=response_text)]
        )
        
        # Enqueue the message to send it back to the orchestrator
        await event_queue.enqueue_event(response)
        
        # Signal that the task is complete
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                final=True,
                status=TaskStatus(state=TaskState.completed)
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handles task cancellation if the orchestrator aborts the request."""
        pass

# ==========================================
# 2. Server Configuration
# ==========================================

# ENVIRONMENT VARIABLES: Using os.getenv to read configuration from the system.
# WHY: This is a "12-Factor App" best practice. It allows the same code to run 
# in different environments (development, staging, production) without modification.
HOST = os.getenv("A2A_HOST", "0.0.0.0")
# TYPE CASTING: os.getenv returns a string, so we must convert it to an int for the port.
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
            tags=["weather", "forecast"]
        )
    ],
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"]
)

# 2. Initialize the A2A Request Handler
handler = DefaultRequestHandler(
    agent_executor=WeatherAgentExecutor(),
    task_store=InMemoryTaskStore()
)

# 3. Build the Starlette Application
# HOW: We use A2AStarletteApplication to wrap our handler and agent card into an ASGI app.
# WHY: This automatically handles the JSON-RPC endpoints, routing, and schema validation
# required to comply with the A2A standard over HTTP.
app_builder = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=handler
)
app = app_builder.build()

# MAIN BLOCK: This code only runs if the script is executed directly (not imported).
# WHY: This prevents the server from starting automatically if we just wanted to 
# import some classes or variables from this file in a test or another module.
if __name__ == "__main__":
    print(f"Starting A2A Weather Sub-Agent on {HOST}:{PORT}...")
    # uvicorn.run: Starts the ASGI server to listen for incoming HTTP requests.
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True)
