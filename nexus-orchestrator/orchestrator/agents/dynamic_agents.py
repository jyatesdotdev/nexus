import logging
import re

import httpx
from google.adk.agents.llm_agent import LlmAgent as Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from orchestrator.registry.agent_registry import AgentRegistry
from orchestrator.config import MCP_SERVER_URLS, A2A_AGENT_URLS
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Standard location of an A2A agent card (per the A2A protocol spec).
AGENT_CARD_WELL_KNOWN_PATH = "/.well-known/agent-card.json"
# Keep startup snappy: an unreachable A2A service should cost a few seconds
# at most, then be skipped.
A2A_DISCOVERY_TIMEOUT_SECONDS = 3.0

# EDUCATIONAL NOTE: Distributed Trace Context Propagation
# [Why] To link traces across different microservices, we must explicitly extract
# the current OpenTelemetry trace context and inject it as HTTP headers
# (e.g., 'traceparent') into outgoing requests made by the ADK tools.
# ADK sometimes loses the native OTel context in background threads, so we
# fallback to a session-mapped TRACE_STORE defined in orchestrator.middleware.
def get_propagated_headers(user_id: str, session_id: str = None) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {user_id}"}
    try:
        from opentelemetry.propagate import inject
        inject(headers)

        # Fallback to cached headers if inject found an empty OTel context
        if "traceparent" not in headers and session_id:
            from orchestrator.middleware import TRACE_STORE
            if session_id in TRACE_STORE:
                headers.update(TRACE_STORE[session_id])
    except ImportError:
        pass
    return headers


def _agent_card_url(url: str) -> str:
    """Resolves a configured A2A URL to its agent-card URL.

    Entries in A2A_AGENT_URLS may be plain service base URLs
    (http://a2a-agent:8001) or, for backward compatibility with the legacy
    A2A_AGENT_URL setting, full agent-card URLs already ending in
    /.well-known/agent-card.json — both resolve to the same card URL.
    """
    if AGENT_CARD_WELL_KNOWN_PATH in url:
        return url
    return url.rstrip("/") + AGENT_CARD_WELL_KNOWN_PATH


def _fetch_agent_card(card_url: str) -> Optional[Dict[str, Any]]:
    """Fetches and parses an agent card, returning None on any failure.

    EDUCATIONAL NOTE: Graceful Degradation at Startup
    [Why] The orchestrator boots inside docker-compose alongside the A2A
    services; if one of them is down or misconfigured we log and skip it so
    the rest of the fleet still comes up — a crash here would take the whole
    entry point down because agents are registered at import time.
    """
    try:
        response = httpx.get(card_url, timeout=A2A_DISCOVERY_TIMEOUT_SECONDS)
        response.raise_for_status()
        card = response.json()
        if not isinstance(card, dict):
            raise ValueError(f"agent card is not a JSON object: {card!r}")
        return card
    except Exception as exc:
        logger.warning(
            "A2A discovery: could not fetch agent card at %s (%s) -- skipping this agent",
            card_url,
            exc,
        )
        return None


def _sanitize_agent_name(raw_name: str, fallback: str) -> str:
    """Converts a human-readable card name into a valid ADK agent identifier.

    E.g. 'Weather Sub-Agent' -> 'weather_sub_agent'. ADK requires agent names
    to be valid Python identifiers; falls back to the legacy naming scheme
    when the card name cannot be sanitized into one.
    """
    candidate = re.sub(r"[^0-9a-zA-Z_]+", "_", raw_name.strip().lower()).strip("_")
    if candidate and candidate[0].isdigit():
        candidate = f"a2a_{candidate}"
    return candidate if candidate.isidentifier() else fallback


# This approach allows for dynamic registration based on config,
# but it requires being called during app initialization.
def register_dynamic_agents() -> None:
    for i, mcp_url in enumerate(MCP_SERVER_URLS):
        name = "mcp_agent" if len(MCP_SERVER_URLS) == 1 else f"mcp_agent_{i}"

        def create_mcp_agent(url: str = mcp_url, agent_name: str = name) -> Agent:
            # EDUCATIONAL NOTE: Tool Confirmation
            # [Why] require_confirmation=False allows the agent to execute tools
            # without manual user approval. For sensitive operations like 'delete_user',
            # you would typically set this to True.
            mcp_toolset = McpToolset(
                connection_params=SseConnectionParams(url=url),
                require_confirmation=False,
                header_provider=lambda ctx: get_propagated_headers(ctx.user_id, getattr(ctx, "session_id", None))
            )
            return Agent(
                name=agent_name,
                instruction=f"You are an HR assistant connecting to MCP server at {url}. Use its tools to query or modify the database.",
                description=f"HR assistant specialized in employee database queries and modifications via MCP server at {url}.",
                tools=[mcp_toolset],
            )

        AgentRegistry.register(name)(create_mcp_agent)

    # EDUCATIONAL NOTE: Config-Driven A2A Discovery
    # [Why] Instead of hardwiring each remote agent's identity in code, we ask
    # every configured A2A endpoint to describe itself via its agent card
    # (name + description). The root agent's routing prompt is generated from
    # these descriptions, so onboarding a new A2A service to the stack only
    # requires appending its URL to A2A_AGENT_URLS — no orchestrator change.
    used_names: set[str] = set()
    for i, a2a_url in enumerate(A2A_AGENT_URLS):
        # Legacy naming scheme, used when the card has no usable name.
        fallback_name = (
            "weather_a2a_agent" if len(A2A_AGENT_URLS) == 1 else f"a2a_agent_{i}"
        )
        card_url = _agent_card_url(a2a_url)
        card = _fetch_agent_card(card_url)
        if card is None:
            continue  # unreachable endpoint: logged inside _fetch_agent_card

        name = _sanitize_agent_name(str(card.get("name", "")), fallback_name)
        if name in used_names:
            name = f"{name}_{i}"  # two cards with the same name: keep both routable
        used_names.add(name)

        description = str(
            card.get("description")
            or f"A remote sub-agent connecting to A2A card at {card_url}."
        )

        def create_a2a_agent(
            url: str = card_url,
            agent_name: str = name,
            agent_description: str = description,
        ) -> RemoteA2aAgent:
            return RemoteA2aAgent(
                name=agent_name,
                agent_card=url,
                description=agent_description,
                a2a_request_meta_provider=lambda ctx, msg: get_propagated_headers(ctx.user_id, getattr(ctx, "session_id", None))
            )

        AgentRegistry.register(name)(create_a2a_agent)
