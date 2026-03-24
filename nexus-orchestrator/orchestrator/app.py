import asyncio
import logging
import os
import warnings
from typing import List, Optional, TypeVar, Generic, Any, Dict
from contextlib import asynccontextmanager

import click
import httpx
import uvicorn

# ADK and GenAI Imports
from google.adk.agents.llm_agent import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.genai import types

# ADK Server Imports
from google.adk.cli.adk_web_server import AdkWebServer
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.evaluation.in_memory_eval_sets_manager import InMemoryEvalSetsManager
from google.adk.evaluation.local_eval_set_results_manager import (
    LocalEvalSetResultsManager,
)
from google.adk.cli.utils.base_agent_loader import BaseAgentLoader
from google.adk.errors.not_found_error import NotFoundError

# Local Imports
from .config import (
    AGENT_MODEL,
    APP_NAME,
    DEFAULT_USER_ID,
    DEFAULT_SESSION_ID,
    MCP_SERVER_URLS,
    A2A_AGENT_URLS,
    validate_config,
)
from .tools import (
    get_sensor_reading,
    query_prometheus_metric,
    fetch_ynab_budget,
    extract_entities_with_grounding,
    execute_safe_bash_command,
)

# Register foundation model adapters

# Suppress experimental and informational warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Setup logging
logging.basicConfig(level=logging.WARNING)
for logger_name in ["httpx", "google_adk", "google_genai", "a2a"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# ==========================================
# 1. Advanced Python: Generics & Protocols
# ==========================================

T = TypeVar("T", bound=Agent)


class AgentFactory(Generic[T]):
    """
    Demonstrates Python Generics.
    A factory for creating agents with consistent configuration.
    """

    def __init__(self, model: str):
        self.model = model

    def create_agent(
        self,
        name: str,
        instruction: str,
        description: Optional[str] = None,
        tools: Optional[List[Any]] = None,
    ) -> T:
        return Agent(  # type: ignore
            model=self.model,
            name=name,
            instruction=instruction,
            description=description or "",
            tools=tools or [],
        )


# ==========================================
# 2. Specialized Agents & Root Orchestrator
# ==========================================


def initialize_agents() -> Agent:
    """Initializes the agent hierarchy using the factory pattern."""
    factory = AgentFactory[Agent](model=AGENT_MODEL)

    # Core Internal Agents
    from google.adk.agents.base_agent import BaseAgent

    sub_agents: List[BaseAgent] = [
        factory.create_agent(
            name="sensor_agent",
            instruction="You are an IoT expert. Use tools to query physical sensors.",
            description="Expert in IoT and physical sensor data (temperature, humidity).",
            tools=[get_sensor_reading],
        ),
        factory.create_agent(
            name="metric_agent",
            instruction="You are a DevOps assistant. Query system metrics.",
            description="DevOps assistant for system-wide CPU and memory metrics via Prometheus.",
            tools=[query_prometheus_metric],
        ),
        factory.create_agent(
            name="api_agent",
            instruction="You are a financial assistant. Use external APIs for budget data.",
            description="Financial assistant for retrieving budget balances from YNAB.",
            tools=[fetch_ynab_budget],
        ),
        factory.create_agent(
            name="parsing_agent",
            instruction="You are an extraction expert. Extract entities from text.",
            description="Specialist in extracting specific entities from unstructured text.",
            tools=[extract_entities_with_grounding],
        ),
    ]

    # Dynamic MCP Integration
    for i, mcp_url in enumerate(MCP_SERVER_URLS):
        name = "mcp_agent" if len(MCP_SERVER_URLS) == 1 else f"mcp_agent_{i}"
        mcp_toolset = McpToolset(connection_params=SseConnectionParams(url=mcp_url))
        mcp_agent = factory.create_agent(
            name=name,
            instruction=f"You are an HR assistant connecting to MCP server at {mcp_url}. Use its tools to query database.",
            description=f"HR assistant specialized in employee database queries via MCP server at {mcp_url}.",
            tools=[mcp_toolset],
        )
        sub_agents.append(mcp_agent)

    # Dynamic A2A Integration
    for i, a2a_url in enumerate(A2A_AGENT_URLS):
        name = "weather_a2a_agent" if len(A2A_AGENT_URLS) == 1 else f"a2a_agent_{i}"
        a2a_agent = RemoteA2aAgent(
            name=name,
            agent_card=a2a_url,
            description=f"A remote sub-agent connecting to A2A card at {a2a_url}. Specialized in weather forecasts.",
        )
        sub_agents.append(a2a_agent)

    # System agent as a fallback
    sub_agents.append(
        factory.create_agent(
            name="system_agent",
            instruction="You are a system administrator. Check system status using bash tools only for uptime and disk space.",
            description="System administrator for basic server health (uptime, disk) as a fallback.",
            tools=[execute_safe_bash_command],
        )
    )

    # Build generic root_agent instruction from registered sub-agents
    agent_capabilities = "\n".join([f"- {a.name}: {a.description}" for a in sub_agents])
    root_instruction = (
        "You are the Root Orchestrator. Your primary job is to route user requests to the correct specialized sub-agent "
        "based on their capabilities and current context. Identify the best sub-agent and delegate immediately.\n"
        "Available Sub-Agents:\n" + agent_capabilities
    )

    # Root Orchestrator
    root_agent = Agent(
        model=AGENT_MODEL,
        name="root_agent",
        description="Main orchestrator that delegates tasks to specialized sub-agents.",
        instruction=root_instruction,
        sub_agents=sub_agents,
    )
    return root_agent


# ==========================================
# 3. Advanced Python: Context Managers
# ==========================================


@asynccontextmanager
async def get_runner(agent: Agent) -> Any:
    """
    Demonstrates Asynchronous Context Managers.
    Ensures the runner is properly initialized and session is created.
    """
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    # Ensure session exists
    if not await runner.session_service.get_session(
        app_name=APP_NAME, user_id=DEFAULT_USER_ID, session_id=DEFAULT_SESSION_ID
    ):
        await runner.session_service.create_session(
            app_name=APP_NAME, user_id=DEFAULT_USER_ID, session_id=DEFAULT_SESSION_ID
        )
    try:
        yield runner
    finally:
        # Cleanup logic would go here (e.g., closing MCP connections if applicable)
        pass


# ==========================================
# 4. Chat Logic
# ==========================================


async def process_prompt(runner: InMemoryRunner, prompt_text: str) -> None:
    """Handles a single user prompt and prints the streamed agent responses."""
    async for event in runner.run_async(
        user_id=DEFAULT_USER_ID,
        session_id=DEFAULT_SESSION_ID,
        new_message=types.Content(role="user", parts=[types.Part(text=prompt_text)]),
    ):
        if (
            event.author != "user"
            and not event.partial
            and event.content
            and event.content.parts
        ):
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(f"\n[{event.author}] > {part.text}")


async def run_chat_loop(initial_prompt: Optional[str] = None) -> None:
    """Starts an interactive chat loop or processes a single prompt."""
    async with get_runner(root_agent) as runner:
        if initial_prompt:
            await process_prompt(runner, initial_prompt)
            return

        print("\n--- Enhanced Multi-Agent Orchestrator ---")
        print("Type 'exit' or 'quit' to end.")
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("\nUser > ").strip()
                )
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit"]:
                    break
                await process_prompt(runner, user_input)
            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                print(f"Error: {e}")


# ==========================================
# 5. Server Logic
# ==========================================


class SimpleAgentLoader(BaseAgentLoader):
    def __init__(self, root_agent: Agent) -> None:
        self.root_agent = root_agent

    def load_agent(self, app_name: str) -> Agent:
        if app_name == APP_NAME:
            return self.root_agent
        raise NotFoundError(f"App {app_name} not found")  # type: ignore

    def list_agents(self) -> List[str]:
        return [APP_NAME]

    def list_agents_detailed(self) -> List[Dict[str, str]]:
        return [
            {
                "name": APP_NAME,
                "root_agent_name": "root_agent",
                "description": "Orchestrator",
                "language": "python",
            }
        ]


# Initialize a global root_agent for consistency across commands and tests
root_agent = initialize_agents()


def create_app_instance(agent: Agent) -> Any:
    """Creates the FastAPI app instance."""
    web_server = AdkWebServer(
        agent_loader=SimpleAgentLoader(agent),
        session_service=InMemorySessionService(),  # type: ignore
        memory_service=InMemoryMemoryService(),  # type: ignore
        artifact_service=InMemoryArtifactService(),
        credential_service=InMemoryCredentialService(),  # type: ignore
        eval_sets_manager=InMemoryEvalSetsManager(),  # type: ignore
        eval_set_results_manager=LocalEvalSetResultsManager(agents_dir="."),
        agents_dir=".",
        auto_create_session=True,
    )

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    app = web_server.get_fast_api_app(allow_origins=[frontend_url])

    @app.get("/health")  # type: ignore
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/system-status")  # type: ignore
    async def get_system_status() -> Dict[str, Any]:
        status: Dict[str, Any] = {
            "orchestrator": "Online",
            "mcp_servers": {},
            "a2a_agents": {},
        }

        async with httpx.AsyncClient(timeout=2.0) as client:
            # Check MCP Servers
            for i, url in enumerate(MCP_SERVER_URLS):
                try:
                    res = await client.head(url)
                    status["mcp_servers"][f"mcp_{i}"] = (
                        "Online" if res.status_code == 200 else "Offline"
                    )
                except Exception:
                    status["mcp_servers"][f"mcp_{i}"] = "Offline"

            # Check A2A Agents
            for i, url in enumerate(A2A_AGENT_URLS):
                try:
                    res = await client.get(url)
                    status["a2a_agents"][f"a2a_{i}"] = (
                        "Online" if res.status_code == 200 else "Offline"
                    )
                except Exception:
                    status["a2a_agents"][f"a2a_{i}"] = "Offline"

        return status

    return app


# Expose app for testing/external use
app = create_app_instance(root_agent)


@click.group()
def cli() -> None:
    """Multi-Agent Orchestrator CLI."""
    validate_config()


@cli.command()
@click.argument("prompt", required=False)
def chat(prompt: Optional[str]) -> None:
    """Start an interactive chat or run a single prompt."""
    asyncio.run(run_chat_loop(prompt))


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind.")
@click.option("--port", default=8080, help="Port to bind.")
def serve(host: str, port: int) -> None:
    """Start the FastAPI backend server."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    cli()
