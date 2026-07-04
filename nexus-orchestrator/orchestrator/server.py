import os
import httpx
from typing import Any, Dict, List, Optional
from fastapi import Request, Response
from google.adk.cli.adk_web_server import AdkWebServer
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import InMemoryCredentialService
from google.adk.evaluation.in_memory_eval_sets_manager import InMemoryEvalSetsManager
from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager
from google.adk.agents.llm_agent import LlmAgent as Agent
from google.adk.errors.not_found_error import NotFoundError

from nexus_common import bootstrap_fastapi_service # type: ignore

from orchestrator.config import (
    APP_NAME,
    MCP_SERVER_URLS,
    A2A_AGENT_URLS,
    PERSISTENCE_BACKEND,
)
from orchestrator.middleware import setup_middleware

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

def create_app_instance(agent: Agent, session_service: Any, memory_service: Any) -> Any:
    """Creates the FastAPI app instance."""
    web_server = AdkWebServer(
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
