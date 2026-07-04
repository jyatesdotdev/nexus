# EDUCATIONAL NOTE: Testing Config-Driven A2A Discovery
# [Why] These tests exercise orchestrator/agents/dynamic_agents.py's startup
# discovery: one agent registered per reachable agent card (name/description
# taken from the card), unreachable endpoints logged and skipped. All HTTP is
# mocked (httpx.get) — the suite never touches the network.
import importlib
import os
import sys
from unittest.mock import patch

import httpx

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from conftest import make_card_response
from orchestrator.registry.agent_registry import AgentRegistry


def _run_discovery_with(env: dict, get_side_effect) -> list:
    """Reloads config + dynamic_agents under `env`, runs discovery, returns agents."""
    import orchestrator.config
    import orchestrator.agents.dynamic_agents as dynamic_agents

    try:
        with patch.dict(os.environ, env), patch("httpx.get", side_effect=get_side_effect):
            importlib.reload(orchestrator.config)
            dynamic_agents = importlib.reload(dynamic_agents)
            AgentRegistry.clear()
            dynamic_agents.register_dynamic_agents()
            return AgentRegistry.get_all_agents()
    finally:
        # Restore default config for subsequent test modules.
        importlib.reload(orchestrator.config)
        importlib.reload(dynamic_agents)


def test_multi_agent_discovery_uses_card_name_and_description() -> None:
    cards = {
        "http://weather-svc:8001/.well-known/agent-card.json": {
            "name": "Weather Sub-Agent",
            "description": "Provides localized weather forecasts via A2A.",
        },
        "http://stock-svc:8002/.well-known/agent-card.json": {
            "name": "Stock Ticker Agent",
            "description": "Real-time stock quotes over A2A.",
        },
    }

    requested_urls = []

    def fake_get(url, **kwargs):
        requested_urls.append(url)
        return make_card_response(cards[url])

    agents = _run_discovery_with(
        {
            # First entry is a bare base URL, second already points at the
            # card — both forms must resolve to the well-known card URL.
            "A2A_AGENT_URLS": "http://weather-svc:8001,http://stock-svc:8002/.well-known/agent-card.json",
            "MCP_SERVER_URLS": "http://mcp1:8000/sse",
        },
        fake_get,
    )

    names = {agent.name for agent in agents}
    assert "weather_sub_agent" in names  # sanitized from "Weather Sub-Agent"
    assert "stock_ticker_agent" in names  # sanitized from "Stock Ticker Agent"

    by_name = {agent.name: agent for agent in agents}
    assert (
        by_name["weather_sub_agent"].description
        == "Provides localized weather forecasts via A2A."
    )
    assert by_name["stock_ticker_agent"].description == "Real-time stock quotes over A2A."

    # The bare base URL must have been expanded to the well-known card path.
    assert "http://weather-svc:8001/.well-known/agent-card.json" in requested_urls
    assert "http://stock-svc:8002/.well-known/agent-card.json" in requested_urls


def test_unreachable_endpoint_is_skipped_without_crashing() -> None:
    def fake_get(url, **kwargs):
        if "down-svc" in url:
            raise httpx.ConnectError("connection refused")
        return make_card_response(
            {"name": "Weather Sub-Agent", "description": "Weather via A2A."}
        )

    agents = _run_discovery_with(
        {
            "A2A_AGENT_URLS": "http://weather-svc:8001,http://down-svc:9999",
            "MCP_SERVER_URLS": "http://mcp1:8000/sse",
        },
        fake_get,
    )

    names = {agent.name for agent in agents}
    # The reachable agent is registered; the dead one is skipped, not fatal.
    assert "weather_sub_agent" in names
    assert not any("down" in name for name in names)


def test_single_url_card_without_name_falls_back_to_legacy_name() -> None:
    def fake_get(url, **kwargs):
        return make_card_response({"description": "An anonymous remote agent."})

    agents = _run_discovery_with(
        {
            "A2A_AGENT_URLS": "http://weather-svc:8001",
            "MCP_SERVER_URLS": "http://mcp1:8000/sse",
        },
        fake_get,
    )

    names = {agent.name for agent in agents}
    assert "weather_a2a_agent" in names  # legacy single-URL fallback name


def test_default_config_registers_weather_agent() -> None:
    """Backward compatibility: with default env, the weather agent is registered."""

    def fake_get(url, **kwargs):
        # Default A2A_AGENT_URLS already points at the card; it must be used as-is.
        assert url.endswith("/.well-known/agent-card.json")
        assert url.count("/.well-known/agent-card.json") == 1
        return make_card_response(
            {
                "name": "Weather Sub-Agent",
                "description": "Provides localized weather forecasts via A2A.",
            }
        )

    agents = _run_discovery_with({}, fake_get)
    names = {agent.name for agent in agents}
    assert "weather_sub_agent" in names
