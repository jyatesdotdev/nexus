# EDUCATIONAL NOTE: HTTP-Level Testing Without a Network
# [Why] FastAPI's TestClient drives the full ASGI stack (CORS, identity
# middleware, trace-id header, routing) in-process, so we can assert on real
# HTTP responses — including SSE endpoint error paths and response headers —
# without starting a server or calling any model.
from fastapi.testclient import TestClient
import os
import sys
from unittest.mock import patch, AsyncMock, MagicMock
from typing import Any

# Add root directory to path so we can import the orchestrator package
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from orchestrator.app import root_agent, session_service, memory_service
from orchestrator.server import create_app_instance
from orchestrator.config import APP_NAME

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


# ==========================================
# X-Trace-Id response header (UI contract)
# ==========================================

def _post_run_sse(user_id: str) -> Any:
    return client.post(
        "/run_sse",
        json={
            "app_name": "wrong_app",  # 404s before any model call: no network
            "user_id": user_id,
            "session_id": "trace_header_session",
            "new_message": {"role": "user", "parts": [{"text": "hello"}]},
        },
        headers={"Origin": "http://localhost:5173"},
    )


def _assert_well_formed_trace_id(value: str) -> None:
    assert len(value) == 32
    assert value == value.lower()
    int(value, 16)  # raises ValueError if not hex


def test_run_sse_response_carries_trace_id_header() -> None:
    response = _post_run_sse("eyJ.test_user.signature")
    assert "X-Trace-Id" in response.headers
    _assert_well_formed_trace_id(response.headers["X-Trace-Id"])


def test_run_sse_rejection_also_carries_trace_id_header() -> None:
    response = _post_run_sse("not-a-valid-token")
    assert response.status_code == 401
    assert "X-Trace-Id" in response.headers
    _assert_well_formed_trace_id(response.headers["X-Trace-Id"])


def test_trace_id_header_is_cors_exposed() -> None:
    # The UI runs on a different origin (localhost:5173 vs :8080); browsers
    # only let cross-origin JS read headers listed in
    # Access-Control-Expose-Headers, which CORSMiddleware adds when the
    # request has an Origin header.
    response = _post_run_sse("eyJ.test_user.signature")
    exposed = response.headers.get("Access-Control-Expose-Headers", "")
    assert "X-Trace-Id" in exposed


def test_get_current_trace_id_uses_active_otel_span() -> None:
    from orchestrator.middleware import get_current_trace_id

    fake_span = MagicMock()
    fake_span.get_span_context.return_value.trace_id = 0x0123456789ABCDEF0123456789ABCDEF
    with patch("opentelemetry.trace.get_current_span", return_value=fake_span):
        assert get_current_trace_id() == "0123456789abcdef0123456789abcdef"


def test_get_current_trace_id_falls_back_when_no_span() -> None:
    from orchestrator.middleware import get_current_trace_id

    # An unset TracerProvider yields the INVALID span (trace_id == 0); the
    # helper must still return a well-formed random id, never all-zeros.
    fake_span = MagicMock()
    fake_span.get_span_context.return_value.trace_id = 0
    with patch("opentelemetry.trace.get_current_span", return_value=fake_span):
        trace_id = get_current_trace_id()
        _assert_well_formed_trace_id(trace_id)
        assert trace_id != "0" * 32
