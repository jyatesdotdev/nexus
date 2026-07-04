# EDUCATIONAL NOTE: Import-Time Configuration & Reload Testing
# [Why] orchestrator.config reads env vars at import time and orchestrator.app
# builds the agent tree at import time, so testing alternate configurations
# requires patching the environment and reloading those modules in dependency
# order (config -> dynamic_agents -> app), then reloading back afterwards so
# later test modules see the default configuration again.
import importlib
import os
import sys
from unittest.mock import patch

# Add root directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from conftest import make_card_response


def _reload_app_modules() -> None:
    """Reloads config-dependent modules so they pick up the current env."""
    import orchestrator.config
    import orchestrator.agents.dynamic_agents
    import orchestrator.app

    importlib.reload(orchestrator.config)
    importlib.reload(orchestrator.agents.dynamic_agents)
    importlib.reload(orchestrator.app)


def test_multi_agent_initialization() -> None:
    # Mock environment variables for multiple MCP and A2A agents
    mock_env = {
        "MCP_SERVER_URLS": "http://mcp1:8000/sse,http://mcp2:8000/sse",
        "A2A_AGENT_URLS": "http://a2a1:8001,http://a2a2:8001,http://a2a3:8001",
        "GEMINI_API_KEY": "dummy_key",
    }

    try:
        # A2A discovery fetches each agent card at registration time; the
        # mocked cards deliberately carry NO name so the legacy fallback
        # naming scheme (a2a_agent_0, a2a_agent_1, ...) is exercised here.
        # Card-derived naming is covered in tests/test_a2a_discovery.py.
        anonymous_card = {"description": "A mocked remote agent."}
        with patch.dict(os.environ, mock_env), patch(
            "httpx.get", return_value=make_card_response(anonymous_card)
        ):
            # We need to reload the config module to pick up the new env vars
            _reload_app_modules()

            from orchestrator.app import initialize_agents
            root_agent = initialize_agents()

            sub_agent_names = [agent.name for agent in root_agent.sub_agents]
            print(f"Sub-agent names: {sub_agent_names}")

            # Core agents: sensor_agent, metric_agent, api_agent, parsing_agent, system_agent (5)
            # MCP agents: mcp_agent_0, mcp_agent_1 (2)
            # A2A agents: a2a_agent_0, a2a_agent_1, a2a_agent_2 (3)
            # Total: 10

            assert "sensor_agent" in sub_agent_names
            assert "metric_agent" in sub_agent_names
            assert "api_agent" in sub_agent_names
            assert "parsing_agent" in sub_agent_names
            assert "system_agent" in sub_agent_names

            assert "mcp_agent_0" in sub_agent_names
            assert "mcp_agent_1" in sub_agent_names

            assert "a2a_agent_0" in sub_agent_names
            assert "a2a_agent_1" in sub_agent_names
            assert "a2a_agent_2" in sub_agent_names

            assert "reviewer_agent" in sub_agent_names

            assert len(sub_agent_names) == 11
    finally:
        # Reload with the original (restored) environment so later test
        # modules see default config instead of this test's URLs.
        with patch(
            "httpx.get",
            return_value=make_card_response(
                {"name": "Weather Sub-Agent", "description": "Weather via A2A."}
            ),
        ):
            _reload_app_modules()
