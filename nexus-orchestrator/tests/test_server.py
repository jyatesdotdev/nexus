import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add root directory to path so we can import the orchestrator package
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from orchestrator.app import app
from orchestrator.config import APP_NAME

from google.adk.errors.not_found_error import NotFoundError

client = TestClient(app)

def test_app_name_is_valid_identifier():
    """Ensure APP_NAME is a valid Python identifier (no hyphens)."""
    assert APP_NAME.isidentifier(), f"APP_NAME '{APP_NAME}' must be a valid identifier"

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_system_status_endpoint():
    # This might return Offline if containers aren't actually running during unit test,
    # but the endpoint itself should respond.
    response = client.get("/system-status")
    assert response.status_code == 200
    data = response.json()
    assert "orchestrator" in data
    assert "mcp_servers" in data
    assert "a2a_agents" in data

def test_run_sse_invalid_app():
    # Test that it raises NotFoundError for wrong app name
    # Note: TestClient by default raises exceptions that occur in the app
    with pytest.raises(NotFoundError):
        client.post("/run_sse", json={
            "app_name": "wrong_app",
            "user_id": "test_user",
            "session_id": "test_session",
            "new_message": {"role": "user", "parts": [{"text": "hello"}]}
        })
