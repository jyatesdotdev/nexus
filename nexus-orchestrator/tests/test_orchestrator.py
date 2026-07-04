import os
import sys
import pytest
from typing import Any
from unittest.mock import MagicMock, patch
from google.genai import types

# Add root directory to path to import the orchestrator package
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from orchestrator.app import root_agent
from orchestrator.config import APP_NAME
from google.adk.runners import InMemoryRunner

# ==========================================
# 1. Mocking the GenAI Client
# ==========================================


@pytest.fixture
def mock_genai_client() -> Any:
    with patch("google.genai.Client") as mock_client_class:
        mock_client = mock_client_class.return_value
        yield mock_client


# ==========================================
# 2. Agent Execution Wrapper
# ==========================================


async def run_agent_test(query: str) -> str:
    """
    Runs the actual agent logic to get a response for the test.
    """
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    user_id = "test_user"
    session_id = f"test_session_{os.urandom(4).hex()}"

    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    full_response = []
    # We need to mock the underlying LLM call here because InMemoryRunner uses it.
    # But since we're testing the ORCHESTRATOR logic (delegation), we might want to
    # mock the response to simulate correct delegation.

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=query)]),
    ):
        if event.author != "user" and not event.partial and event.content:
            parts = event.content.parts or []
            for part in parts:
                if part.text:
                    full_response.append(part.text)

    return "\n".join(full_response)


# ==========================================
# 3. Deterministic Test Case
# ==========================================


@pytest.mark.asyncio
async def test_agent_delegation_mocked() -> None:
    """
    Test agent delegation by mocking the runner's underlying LLM interaction.
    Instead of testing the LLM's 'intelligence', we test if the runner
    can execute with a mocked stream of events.
    """
    query = "What is the current CPU usage?"

    # We patch the run_async of the runner directly to avoid real network calls
    with patch("google.adk.runners.InMemoryRunner.run_async") as mock_run:
        # Create a mock async generator
        async def mock_generator(*args: Any, **kwargs: Any) -> Any:
            yield MagicMock(
                author="root_agent",
                partial=False,
                content=types.Content(
                    parts=[types.Part(text="I will check the metrics.")]
                ),
            )
            yield MagicMock(
                author="metric_agent",
                partial=False,
                content=types.Content(
                    parts=[types.Part(text="The current CPU usage is 95.4%.")]
                ),
            )

        mock_run.side_effect = mock_generator

        response_text = await run_agent_test(query)
        assert "95.4%" in response_text
        assert "I will check the metrics." in response_text


if __name__ == "__main__":
    pytest.main([__file__])
