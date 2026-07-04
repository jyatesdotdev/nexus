"""
EDUCATIONAL NOTE: Unified Service Bootstrap
This module provides a single-call entry point for initializing all cross-cutting
concerns (health checks, telemetry, metrics) on any Nexus microservice.
Instead of each service duplicating the same boilerplate, they call one function.
"""
from typing import Any

from .telemetry import setup_telemetry


# ==========================================
# Health Check Handlers
# ==========================================

async def _starlette_health_check(request: Any) -> Any:
    """Standard health check handler for Starlette-based services."""
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok"})


# ==========================================
# Service Bootstrap Functions
# ==========================================

def bootstrap_starlette_service(service_name: str, app: Any) -> None:
    """
    One-call bootstrap for Starlette-based services (A2A, MCP).
    Registers the /health endpoint and initializes telemetry.

    Args:
        service_name: The name used in traces and metrics (e.g. 'a2a-agent').
        app: The Starlette application instance.
    """
    # EDUCATIONAL NOTE: Consistent Health Endpoints
    # [Why] Every service in the Nexus ecosystem exposes /health so that
    # Docker healthchecks and the orchestrator's /system-status can verify liveness.
    app.add_route("/health", _starlette_health_check, methods=["GET"])
    setup_telemetry(service_name=service_name, app=app, app_type="starlette")


def bootstrap_fastapi_service(service_name: str, app: Any) -> None:
    """
    One-call bootstrap for FastAPI-based services (Orchestrator).
    Registers the /health endpoint and initializes telemetry.

    Args:
        service_name: The name used in traces and metrics (e.g. 'orchestrator').
        app: The FastAPI application instance.
    """
    # `app` is deliberately Any (works for any FastAPI instance), so the
    # decorator is untyped to mypy.
    @app.get("/health")  # type: ignore[untyped-decorator]
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    setup_telemetry(service_name=service_name, app=app, app_type="fastapi")
