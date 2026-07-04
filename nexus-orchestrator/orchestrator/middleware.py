import json
from typing import Dict, Any, Callable, Awaitable
from fastapi import Request, Response
from starlette.requests import Request as StarletteRequest
from nexus_common import verify_token # type: ignore

from orchestrator.config import APP_NAME, DEFAULT_USER_ID

# EDUCATIONAL NOTE: Global Trace Context Store
# [Why] ADK loses OpenTelemetry contextvars when running sub-agents asynchronously.
# TRACE_STORE provides a request-scoped fallback mapped to the session_id,
# ensuring the orchestrator's trace ID is propagated to all downstream agents.
TRACE_STORE: Dict[str, Dict[str, str]] = {}

def setup_middleware(app: Any, session_service: Any) -> None:
    """
    Sets up the identity and session validation middleware for the FastAPI app.
    """
    
    # EDUCATIONAL NOTE: Security & Identity Middleware
    # This middleware acts as our 'Security Gateway'. Before any request reaches
    # the Root Agent, we validate the mock JWT token and ensure the session exists.
    # EDUCATIONAL NOTE: [Why] Auto-Session Creation is implemented here to ensure 
    # a seamless first-run experience for UI users when using a persistent backend (Redis/PG).
    @app.middleware("http") # type: ignore
    async def validate_identity_and_session(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # We only strictly enforce validation on the core execution endpoint
        if request.url.path == "/run_sse" and request.method == "POST":
            # [Fix] Robust body replaying for Starlette/FastAPI middleware
            body = await request.body()
            
            async def receive() -> Dict[str, Any]:
                return {"type": "http.request", "body": body, "more_body": False}
            
            # Create a new request object with the same scope but our custom receive
            request = StarletteRequest(request.scope, receive=receive)
            
            try:
                data = json.loads(body)
                token = data.get("user_id", "")
                
                # 1. Identity Validation
                if not verify_token(token):
                    return Response(
                        content="INVALID_IDENTITY: Please provide a valid Nexus JWT token.", 
                        status_code=401
                    )
                
                # 2. Session Auto-Creation
                session_id = data.get("session_id")
                user_id = data.get("user_id", DEFAULT_USER_ID)
                if session_id:
                    # Capture and store the current trace context for this session
                    # This ensures propagation even if the OTel context is lost inside the ADK runner.
                    from opentelemetry.propagate import inject
                    trace_headers: Dict[str, str] = {}
                    inject(trace_headers)
                    if trace_headers:
                        TRACE_STORE[session_id] = trace_headers

                    # EDUCATIONAL NOTE: [Why] ADK session services take keyword-only
                    # arguments and return None (rather than raising) when a session
                    # is missing. We must only create a session when one genuinely
                    # does not exist: with persistent backends (Redis/Postgres),
                    # create_session overwrites the stored session with a fresh empty
                    # one, which would wipe the chat history on every request.
                    existing_session = await session_service.get_session(
                        app_name=APP_NAME,
                        user_id=user_id,
                        session_id=session_id,
                    )
                    if existing_session is None:
                        await session_service.create_session(
                            session_id=session_id,
                            user_id=user_id,
                            app_name=APP_NAME
                        )
            except Exception:
                pass
                
        return await call_next(request)
