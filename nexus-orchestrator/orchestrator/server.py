import os
import httpx
from typing import Any, Dict, List, Optional
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from google.adk.cli.adk_web_server import AdkWebServer
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.evaluation.in_memory_eval_sets_manager import InMemoryEvalSetsManager
from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager
from google.adk.agents.llm_agent import LlmAgent as Agent
from google.adk.errors.not_found_error import NotFoundError

from nexus_common import bootstrap_fastapi_service # type: ignore

from orchestrator import config
from orchestrator.config import (
    MCP_SERVER_URLS,
    A2A_AGENT_URLS,
    PERSISTENCE_BACKEND,
)
from orchestrator.middleware import setup_middleware, TRACE_ID_HEADER
from orchestrator.reviewer import build_governed_runner

class SimpleAgentLoader(BaseAgentLoader):
    """
    A simple agent loader that returns the pre-initialized root_agent.
    """
    def __init__(self, agent: Agent):
        self.agent = agent

    def load_agent(self, agent_name: str) -> Optional[Agent]:
        # EDUCATIONAL NOTE: Robust Agent Resolution
        # [Why] The frontend might refer to the agent by its specific name ('root_agent')
        # or by the general app name ('containerized_agents'). We handle both.
        if agent_name in ["root_agent", "containerized_agents", ""]:
            return self.agent
        
        raise NotFoundError(f"Agent {agent_name} not found")

    def list_agents(self) -> List[str]:
        return ["root_agent", "containerized_agents"]


class GovernedAdkWebServer(AdkWebServer):
    """
    AdkWebServer whose runners are wrapped in the governance pipeline
    Runner -> LoopDetectionRunner -> ReviewerEnforcementRunner.

    EDUCATIONAL NOTE: Reviewer Enforcement on the HTTP Path
    [Why] `app.get_runner()` only governs the CLI/evals path; AdkWebServer
    builds its own Runner per app inside `get_runner_async`, so UI traffic
    hitting POST /run_sse used to bypass the reviewer entirely. ADK (1.28.0)
    offers no runner-factory or injection hook on AdkWebServer, so the
    narrowest supported seam is overriding the protected `_create_runner`
    method — the single place where `get_runner_async` constructs a Runner
    before caching it in `runner_dict`.
    [Tradeoff] `_create_runner` is a private method, so an ADK upgrade could
    move it; the unit tests in tests/test_reviewer_wiring.py pin this seam
    and will fail loudly if it disappears. The wrappers duck-type as Runner
    (they forward every other attribute via __getattr__), which satisfies all
    call sites in adk_web_server.py (run_async, run_live, close,
    auto_create_session, app).
    """

    def _create_runner(self, agentic_app: Any) -> Any:
        runner = super()._create_runner(agentic_app)
        # REVIEWER_ENFORCEMENT is read via the config module attribute at
        # runner-creation time so tests/demos can toggle it without reloading
        # this module.
        return build_governed_runner(
            runner,
            self._get_root_agent(agentic_app),
            enforce_review=config.REVIEWER_ENFORCEMENT,
        )


def create_app_instance(agent: Agent, session_service: Any, memory_service: Any) -> Any:
    """Creates the FastAPI app instance."""
    web_server = GovernedAdkWebServer(
        agent_loader=SimpleAgentLoader(agent),
        session_service=session_service,
        memory_service=memory_service,
        artifact_service=InMemoryArtifactService(),
        credential_service=InMemoryCredentialService(),
        eval_sets_manager=InMemoryEvalSetsManager(),
        eval_set_results_manager=LocalEvalSetResultsManager(agents_dir="."),
        agents_dir=".",
    )

    # EDUCATIONAL NOTE: CORS Configuration
    # [Why] Allowing all origins ('*') ensures the UI can communicate with the backend
    # regardless of which hostname or port it's served from in this lab environment.
    app = web_server.get_fast_api_app(allow_origins=["*"])

    # EDUCATIONAL NOTE: Exposing Custom Headers Across Origins
    # [Why] Browsers hide non-safelisted response headers from cross-origin
    # JavaScript unless the server lists them in Access-Control-Expose-Headers.
    # The UI (localhost:5173) needs to read X-Trace-Id from /run_sse responses
    # (served from :8080), so we must expose it. AdkWebServer.get_fast_api_app
    # adds its own CORSMiddleware but has no expose_headers parameter, so we
    # amend the registered middleware's kwargs before the stack is built at
    # startup (Starlette builds the middleware stack lazily on first request).
    for registered_middleware in app.user_middleware:
        if registered_middleware.cls is CORSMiddleware:
            expose = list(registered_middleware.kwargs.get("expose_headers") or [])
            if TRACE_ID_HEADER not in expose:
                expose.append(TRACE_ID_HEADER)
            registered_middleware.kwargs["expose_headers"] = expose

    @app.exception_handler(NotFoundError) # type: ignore
    async def not_found_exception_handler(request: Request, exc: NotFoundError) -> Response:
        return Response(content=str(exc), status_code=404)

    # Setup the identity and session validation middleware
    setup_middleware(app, session_service)
    
    # EDUCATIONAL NOTE: Shared Infrastructure
    # We now use the nexus_common library to standardize telemetry and health
    # checks across all services, ensuring consistency.
    bootstrap_fastapi_service(service_name="orchestrator", app=app) # type: ignore

    @app.get("/system-status")  # type: ignore
    async def get_system_status() -> Dict[str, Any]:
        status: Dict[str, Any] = {
            "orchestrator": "Online",
            "mcp_server": "Offline",
            "mcp_db": "Offline",
            "a2a_agent": "Offline",
            "a2a_api": "Reachability",
            "prometheus": "Offline",
            "persistence": PERSISTENCE_BACKEND,
        }

        async with httpx.AsyncClient(timeout=2.0) as client:
            # Check Prometheus
            prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
            try:
                res = await client.get(f"{prometheus_url}/-/healthy")
                if res.status_code == 200:
                    status["prometheus"] = "Online"
            except Exception:
                pass

            # Check First MCP Server
            if MCP_SERVER_URLS:
                url = MCP_SERVER_URLS[0]
                try:
                    res = await client.head(url)
                    if res.status_code == 200:
                        status["mcp_server"] = "Online"
                        status["mcp_db"] = "Connected"
                except Exception:
                    pass

            # Check First A2A Agent
            if A2A_AGENT_URLS:
                url = A2A_AGENT_URLS[0]
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        status["a2a_agent"] = "Online"
                        status["a2a_api"] = "Reachable"
                except Exception:
                    pass

        return status

    return app
