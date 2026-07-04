import pytest
from fastapi.testclient import TestClient
import os
import sys
from unittest.mock import patch, AsyncMock
from typing import Any

# Add root directory to path so we can import the orchestrator package
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from orchestrator.app import root_agent, session_service, memory_service
from orchestrator.server import create_app_instance
from orchestrator.config import APP_NAME

from google.adk.errors.not_found_error import NotFoundError

app = create_app_instance(root_agent, session_service, memory_service)
client = TestClient(app, raise_server_exceptions=False)


def test_app_name_is_valid_identifier() -> None:
    """Ensure APP_NAME is a valid Python identifier (no hyphens)."""
    assert APP_NAME.isidentifier(), f"APP_NAME '{APP_NAME}' must be a valid identifier"


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("httpx.AsyncClient.head", new_callable=AsyncMock)
@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_system_status_endpoint(mock_get: Any, mock_head: Any) -> None:
    mock_head.return_value.status_code = 200
    mock_get.return_value.status_code = 200
    # This might return Offline if containers aren't actually running during unit test,
    # but the endpoint itself should respond.
    response = client.get("/system-status")
    assert response.status_code == 200
    data = response.json()
    assert "orchestrator" in data
    assert "mcp_server" in data
    assert "a2a_agent" in data


def test_run_sse_invalid_app() -> None:
    # Test that it returns 404 for wrong app name
    # We must use a valid mock JWT token to pass the identity middleware
    valid_token = "eyJ.test_user.signature"
    response = client.post(
        "/run_sse",
        json={
            "app_name": "wrong_app",
            "user_id": valid_token,
            "session_id": "test_session",
            "new_message": {"role": "user", "parts": [{"text": "hello"}]},
        },
    )
    assert response.status_code == 404
