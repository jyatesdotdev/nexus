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


# EDUCATIONAL NOTE: Why Naive Extraction Fails in a Multi-Agent Context
# [Why] This agent rarely sees what the human literally typed: it sees a
# message COMPOSED BY ANOTHER LLM (the root orchestrator), which may splice
# earlier conversation topics into the delegated text. A real incident: after
# an HR question about "the engineering department", the user asked "What's
# the weather like?" with no location; the orchestrator's delegated message
# contained "in the engineering department", the old "grab the words after
# 'in'" heuristic latched onto it, and wttr.in fuzzy-geocoded that nonsense
# string into a confident (and wrong) forecast. The fix is NOT smarter NLP —
# it is refusing to guess: when no confident location is present, return None
# and let the executor ask for clarification instead of inventing one.

# Tokens that signal the "in ..." clause is about org structure, people, or
# time — not geography. Deliberately small and readable: false negatives just
# produce a polite clarification question, which is the safe failure mode.
_NON_PLACE_WORDS = frozenset(
    {
        "department",
        "team",
        "office",
        "meeting",
        "room",
        "company",
        "organization",
        "engineering",
        "marketing",
        "sales",
        "finance",
        "hr",
        "morning",
        "afternoon",
        "evening",
        "minute",
        "minutes",
        "hour",
        "hours",
        "general",
        "charge",
        "case",
        "fact",
        "order",
        "that",
        "this",
        "it",
        "there",
        "here",
    }
)

# Trailing time words that ride along with a real place ("in Tokyo today").
_TEMPORAL_WORDS = frozenset(
    {"today", "tomorrow", "tonight", "now", "currently", "later", "please"}
)

_LEADING_ARTICLES = ("the", "a", "an")

_PUNCT = "?.,!'\""


def extract_city(user_message: str) -> Optional[str]:
    """
    Extracts a city/place name from a natural language message.

    Returns None when no confident location is present — callers must then
    ask the user for clarification instead of guessing (see the EDUCATIONAL
    NOTE above for the incident that motivated this contract).
    """
    clean_message = user_message.split("For context:")[0].strip()

    candidate = ""
    words = clean_message.split()
    if "in" in words:
        idx = words.index("in")
        candidate = " ".join(words[idx + 1 :])
    elif len(words) > 0 and not any(
        w in clean_message.lower() for w in ["what", "how", "weather", "forecast"]
    ):
        candidate = clean_message

    tokens = candidate.strip(_PUNCT + " ").split()

    # "in Tokyo today" -> "Tokyo"; "in the UK" -> "UK".
    while tokens and tokens[-1].lower().strip(_PUNCT) in _TEMPORAL_WORDS:
        tokens.pop()
    while tokens and tokens[0].lower() in _LEADING_ARTICLES:
        tokens.pop(0)

    if not tokens:
        return None
    if any(t.lower().strip(_PUNCT) in _NON_PLACE_WORDS for t in tokens):
        return None

    return " ".join(tokens).strip(_PUNCT)


def resolved_area_matches(candidate: str, data: Dict[str, Any]) -> bool:
    """
    Sanity-checks that wttr.in resolved the candidate to a plausible area.

    EDUCATIONAL NOTE: Validate What the Upstream API Resolved
    [Why] wttr.in FUZZY-geocodes its path segment: an arbitrary string never
    404s, it just resolves to *some* nearest area, and the j1 payload happily
    reports real weather for it. So extraction guards alone are not enough —
    a nonsense candidate that slips through would still yield a confident
    forecast for an unrelated place. The j1 payload echoes what was resolved
    in `nearest_area` (areaName/region/country) and `request`; a loose,
    case-insensitive token overlap between the candidate and those names is a
    cheap second line of defense. Missing/malformed `nearest_area` counts as
    a match: we cannot validate, and blocking would break older payloads
    (and the mocked happy-path tests).
    """
    resolved_names: list[str] = []
    try:
        area = data["nearest_area"][0]
        for key in ("areaName", "region", "country"):
            for entry in area.get(key) or []:
                value = entry.get("value")
                if value:
                    resolved_names.append(str(value).lower())
    except (KeyError, IndexError, TypeError, AttributeError):
        return True
    if not resolved_names:
        return True

    candidate_tokens = {
        t.strip(_PUNCT) for t in candidate.lower().split() if t.strip(_PUNCT)
    }
    resolved_tokens: set[str] = set()
    for name in resolved_names:
        resolved_tokens.update(
            t.strip(_PUNCT) for t in name.replace(",", " ").split()
        )
    return bool(candidate_tokens & resolved_tokens)


CLARIFICATION_TEXT = (
    "I couldn't identify a specific location in your request. "
    "Which city or place would you like the weather for? "
    "(e.g. 'What is the weather in Tokyo?')"
)


class WeatherAgentExecutor(AgentExecutor):
    """A sub-agent that provides weather forecasts via the A2A protocol."""

    async def _enqueue_status(
        self,
        context: RequestContext,
        event_queue: EventQueue,
        *,
        final: bool,
        text: str,
    ) -> None:
        """Enqueues one TaskStatusUpdateEvent carrying a plain text message."""
        message = Message(
            message_id=str(uuid.uuid4()),
            role=Role.agent,
            parts=[TextPart(text=text)],  # type: ignore[list-item]
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id or "",
                context_id=context.context_id or "",
                final=final,
                status=TaskStatus(
                    state=TaskState.completed if final else TaskState.working,
                    message=message,
                ),
            )
        )

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

        # EDUCATIONAL NOTE: Refuse to Guess
        # [Why] When no confident location is present we keep the two-phase
        # streaming contract (one non-final "thinking" update, one final
        # update) but the final message ASKS for a location instead of
        # inventing one. A2A also has TaskState.input_required for this; we
        # stay with `completed` to preserve the simple two-event contract the
        # orchestrator and tests rely on.
        if city is None:
            thinking_text = (
                f"*(Authenticated as {identity.user_id})* Looking for a "
                "location in the request...\n"
            )
            await self._enqueue_status(
                context, event_queue, final=False, text=thinking_text
            )
            await self._enqueue_status(
                context, event_queue, final=True, text=CLARIFICATION_TEXT
            )
            return

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

            # Second line of defense: wttr.in never 404s a fuzzy string, so
            # verify the resolved nearest_area plausibly matches what was
            # asked before reporting it (see resolved_area_matches).
            if not resolved_area_matches(city, data):
                await self._enqueue_status(
                    context,
                    event_queue,
                    final=True,
                    text=(
                        f'I couldn\'t confidently resolve "{city}" to a real '
                        "place (the weather service matched it to an "
                        "unrelated area). Which city or place would you like "
                        "the weather for?"
                    ),
                )
                return

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
