# EDUCATIONAL NOTE: Offline A2A Discovery for the Unit Suite
# [Why] Importing orchestrator.app builds the root agent at import time, and
# A2A discovery (orchestrator/agents/dynamic_agents.py) fetches each agent
# card over HTTP during that build. The unit suite is 100% isolated (no
# network), so this conftest performs the very first `import orchestrator.app`
# itself with httpx.get patched to return the same card nexus-a2a serves in
# production. Every later `import orchestrator.app` in a test module reuses
# the cached module, so no test ever touches the network. Tests that re-run
# discovery (importlib.reload / register_dynamic_agents) must patch httpx.get
# themselves.
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MOCK_WEATHER_CARD = {
    "name": "Weather Sub-Agent",
    "description": "Provides localized weather forecasts via A2A.",
}


def make_card_response(card: dict) -> MagicMock:
    """Builds a mock httpx.Response carrying an agent card."""
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = card
    return response


with patch("httpx.get", return_value=make_card_response(MOCK_WEATHER_CARD)):
    import orchestrator.app  # noqa: F401
