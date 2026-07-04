"""
CONCEPT: Agent-to-Agent (A2A) Protocol
This module implements a standalone A2A-compliant sub-agent.
"""

import uvicorn
import uuid
import os
import httpx
from typing import Optional, Dict, Any
from nexus_common import bootstrap_starlette_service, IdentityContext

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
    """
    clean_message = user_message.split("For context:")[0].strip()
    
    city = "London"
    words = clean_message.split()
    if "in" in words:
        try:
            idx = words.index("in")
            city = " ".join(words[idx + 1 :]).strip("?.,!")
        except IndexError:
            pass
    elif len(words) > 0 and not any(
        w in clean_message.lower() for w in ["what", "how", "weather", "forecast"]
    ):
        city = clean_message.strip("?.,!")
    
    return city if city else "London"


class WeatherAgentExecutor(AgentExecutor):
    """A sub-agent that provides weather forecasts via the A2A protocol."""

    async def _fetch_weather_data(self, city: str) -> Dict[str, Any]:
        """
        Helper method to fetch weather data from wttr.in.
        [EDUCATIONAL NOTE] Extracting I/O logic into helpers makes the protocol code cleaner.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://wttr.in/{city}?format=j1")
            resp.raise_for_status()
            return resp.json()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Processes an incoming A2A request by fetching weather data.
        """
        user_message = context.get_user_input()
        print(f"A2A Sub-Agent received: {user_message}")
        
        identity = IdentityContext(context.metadata.get("Authorization"))
        print(f"A2A Sub-Agent authenticated with: {identity.user_id}")

        city = extract_city(user_message)
        response_text = "I am a specialized Weather Agent. Let me check that for you..."
        weather_metadata: Optional[Dict[str, Any]] = None

        try:
            # Send an initial "thinking" message
            thinking_msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.agent,
                parts=[TextPart(text=f"*(Authenticated as {identity.user_id})* Fetching weather data for **{city}** from wttr.in...\n")],  # type: ignore[list-item]
            )
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id or "",
                    context_id=context.context_id or "",
                    final=False,
                    status=TaskStatus(state=TaskState.working, message=thinking_msg),
                )
            )

            # Fetch data using our helper
            data = await self._fetch_weather_data(city)
            current = data["current_condition"][0]
            temp_f = current["temp_F"]
            temp_c = current["temp_C"]
            desc = current["weatherDesc"][0]["value"]
            
            response_text = f"The current weather in **{city}** is {desc} with a temperature of {temp_f}°F ({temp_c}°C)."

            # EDUCATIONAL NOTE: Explicit Variable Mapping
            # [Why] Avoiding the 'locals()' anti-pattern ensures the code is explicit,
            # type-safe, and easier for learners to follow.
            weather_metadata = {
                "type": "weather_forecast",
                "city": city,
                "temp_f": temp_f,
                "temp_c": temp_c,
                "description": desc,
                "humidity": current.get("humidity"),
                "wind_speed": current.get("windspeedKmph"),
            }

        except httpx.HTTPStatusError as e:
            response_text = f"Could not retrieve weather for {city}. The service returned status {e.response.status_code}."
        except httpx.RequestError as e:
            response_text = f"A network error occurred while fetching the weather: {e}"
        except (KeyError, IndexError, TypeError):
            # EDUCATIONAL NOTE: Explicit Parse-Error Handling
            # [Why] wttr.in can return 200 OK with an unexpected JSON shape. Catching
            # the specific lookup errors (KeyError/IndexError/TypeError) raised while
            # extracting fields — instead of letting them fall through to the generic
            # handler — gives callers a clear, actionable message and keeps the
            # generic branch reserved for truly unexpected failures.
            response_text = f"Could not parse weather data for {city}."
        except Exception as e:
            response_text = f"An unexpected error occurred: {e}"

        # Construct the final A2A-compliant message
        response = Message(
            message_id=str(uuid.uuid4()),
            role=Role.agent,
            parts=[TextPart(text=response_text)],  # type: ignore[list-item]
            metadata={"structured_data": weather_metadata} if weather_metadata else {}
        )

        # Signal completion
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                final=True,
                status=TaskStatus(state=TaskState.completed, message=response),
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handles task cancellation if the orchestrator aborts the request."""
        pass


# ==========================================
# 2. Server Configuration
# ==========================================

HOST = os.getenv("A2A_HOST", "0.0.0.0")
PORT = int(os.getenv("A2A_PORT", "8001"))
PUBLIC_URL = os.getenv("A2A_PUBLIC_URL", f"http://a2a-agent:{PORT}")

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

handler = DefaultRequestHandler(
    agent_executor=WeatherAgentExecutor(), task_store=InMemoryTaskStore()
)

app_builder = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
app = app_builder.build()

bootstrap_starlette_service(service_name="a2a-agent", app=app)

if __name__ == "__main__":
    print(f"Starting A2A Weather Sub-Agent on {HOST}:{PORT}...")
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True)
