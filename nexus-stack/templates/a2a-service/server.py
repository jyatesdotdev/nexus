"""
CONCEPT: Agent-to-Agent (A2A) Protocol
This module implements the __SERVICE_TITLE__ sub-agent — a standalone
A2A-compliant service scaffolded from nexus-stack/templates/a2a-service
(modeled on the canonical nexus-a2a weather agent).
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
# 1. Domain Logic (pure function)
# ==========================================


def process_query(user_message: str) -> str:
    """Turns the raw user message into this agent's query/answer.

    EDUCATIONAL NOTE: Pure Domain Functions
    [Why] Keeping the agent's capability in a plain function (no I/O, no A2A
    types) makes it trivially unit-testable — the same pattern as nexus-a2a's
    extract_city().
    """
    # The orchestrator may append delegation context after a literal
    # "For context:" marker; strip it so domain logic only sees the user's
    # actual request.
    clean_message = user_message.split("For context:")[0].strip()

    # TODO: Implement your agent's real capability here. The scaffold just
    # echoes the cleaned request back so the service works end-to-end on day
    # one; replace this with your parsing/computation, and use
    # _fetch_external_data below if you need an upstream API.
    return clean_message.strip("?.,!") or "an empty request"


# ==========================================
# 2. A2A Agent Executor
# ==========================================


class __SERVICE_TITLE__AgentExecutor(AgentExecutor):
    """A sub-agent that handles __SERVICE_NAME__ requests via the A2A protocol."""

    async def _fetch_external_data(self, base_url: str, query: str) -> Dict[str, Any]:
        """Helper method to fetch supporting data from an external API.

        EDUCATIONAL NOTE: Extracting I/O logic into helpers keeps the protocol
        code clean and gives tests a single httpx boundary to mock with respx
        (see tests/test_server.py). Point EXTERNAL_API_URL at your upstream
        service — or delete this helper if your capability is purely local.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}?q={query}")
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()
            return data

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Processes an incoming A2A request with two-phase streaming."""
        user_message = context.get_user_input()
        print(f"__SERVICE_TITLE__ sub-agent received: {user_message}")

        # EDUCATIONAL NOTE: Identity Propagation
        # [Why] The orchestrator forwards the caller's mock JWT in the A2A
        # message metadata; parsing it here (via nexus-common) demonstrates
        # end-to-end identity across service boundaries.
        identity = IdentityContext(context.metadata.get("Authorization"))
        print(f"__SERVICE_TITLE__ sub-agent authenticated as: {identity.user_id}")

        query = process_query(user_message)
        response_text = "I am the __SERVICE_TITLE__ agent. Let me handle that..."
        structured_data: Optional[Dict[str, Any]] = None

        try:
            # Phase 1 of the two-phase streaming contract: a non-final
            # "thinking" update (final=False, state=working) so the user gets
            # immediate feedback while the real work happens.
            thinking_msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.agent,
                parts=[TextPart(text=f"*(Authenticated as {identity.user_id})* Working on **{query}**...\n")],  # type: ignore[list-item]
            )
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    task_id=context.task_id or "",
                    context_id=context.context_id or "",
                    final=False,
                    status=TaskStatus(state=TaskState.working, message=thinking_msg),
                )
            )

            # Optional enrichment: when EXTERNAL_API_URL is set, fetch
            # supporting data from it. Unset (the default), the scaffold
            # answers locally so a fresh agent works without any upstream.
            external_api_url = os.getenv("EXTERNAL_API_URL", "")
            if external_api_url:
                data = await self._fetch_external_data(external_api_url, query)
                response_text = (
                    f"__SERVICE_TITLE__ agent processed **{query}** "
                    f"with external data: {data}"
                )
            else:
                response_text = (
                    f"__SERVICE_TITLE__ agent processed your request: **{query}**"
                )

            # EDUCATIONAL NOTE: Structured Metadata for Generative UI
            # [Why] The Nexus UI renders bespoke widgets keyed off this "type"
            # field (see nexus-ui's generative widgets); plain text alone
            # would lose that capability. Extend this dict with your fields.
            structured_data = {
                "type": "__SERVICE_SNAKE___result",
                "query": query,
            }

        except httpx.HTTPStatusError as e:
            response_text = (
                f"Could not process {query}. "
                f"The external service returned status {e.response.status_code}."
            )
        except httpx.RequestError as e:
            response_text = f"A network error occurred while processing {query}: {e}"
        except Exception as e:
            # The executor never raises to the caller: every failure becomes a
            # final message so the orchestrator's task lifecycle stays clean.
            response_text = f"An unexpected error occurred: {e}"

        # Phase 2: the final A2A-compliant message (final=True, completed).
        response = Message(
            message_id=str(uuid.uuid4()),
            role=Role.agent,
            parts=[TextPart(text=response_text)],  # type: ignore[list-item]
            metadata={"structured_data": structured_data} if structured_data else {},
        )
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
# 3. Server Configuration
# ==========================================

HOST = os.getenv("__SERVICE_UPPER___HOST", "0.0.0.0")
PORT = int(os.getenv("__SERVICE_UPPER___PORT", "__PORT__"))
# The Docker network name, not localhost: the URL must be reachable from the
# orchestrator's network namespace on nexus-net.
PUBLIC_URL = os.getenv("__SERVICE_UPPER___PUBLIC_URL", f"http://__SERVICE_NAME__-agent:{PORT}")

agent_card = AgentCard(
    # EDUCATIONAL NOTE: The card `name` is not cosmetic. The orchestrator
    # discovers A2A agents dynamically from A2A_AGENT_URLS: it fetches each
    # URL's agent card and registers one sub-agent per card, deriving the
    # orchestrator-side agent name from this value (e.g.
    # "__SERVICE_TITLE__ Sub-Agent" -> __SERVICE_SNAKE___sub_agent).
    # Renaming the card renames the agent the LLM routes to.
    name="__SERVICE_TITLE__ Sub-Agent",
    description="Handles __SERVICE_NAME__ requests via A2A.",
    url=PUBLIC_URL,
    version="0.1.0",
    skills=[
        AgentSkill(
            description="Processes __SERVICE_NAME__ queries.",
            id="__SERVICE_SNAKE___capability",
            name="__SERVICE_TITLE__ Capability",
            examples=["Ask the __SERVICE_TITLE__ agent something"],
            tags=["__SERVICE_NAME__"],
        )
    ],
    capabilities=AgentCapabilities(streaming=True),
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
)

handler = DefaultRequestHandler(
    agent_executor=__SERVICE_TITLE__AgentExecutor(), task_store=InMemoryTaskStore()
)

app_builder = A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
app = app_builder.build()

# Adds GET /health plus OpenTelemetry traces and Prometheus metrics — the
# shared bootstrap every Nexus Python service uses.
bootstrap_starlette_service(service_name="__SERVICE_NAME__-agent", app=app)

if __name__ == "__main__":
    print(f"Starting __SERVICE_TITLE__ Sub-Agent on {HOST}:{PORT}...")
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True)
