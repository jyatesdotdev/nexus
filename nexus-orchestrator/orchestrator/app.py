import warnings
from typing import Optional, Any
from contextlib import asynccontextmanager

from google.adk.agents.llm_agent import LlmAgent as Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai.types import Content, Part

from orchestrator import config
from orchestrator.config import (
    AGENT_MODEL,
    APP_NAME,
    DEFAULT_SESSION_ID,
    DEFAULT_USER_ID,
    PERSISTENCE_BACKEND,
    REDIS_URL,
    POSTGRES_URL,
)
from orchestrator.persistence.redis_services import RedisSessionService, RedisMemoryService
from orchestrator.persistence.postgres_services import PostgresMemoryService
from orchestrator.persistence.database_services import DatabaseSessionService
from orchestrator.reviewer import LoopDetectionRunner, build_governed_runner  # noqa: F401  (LoopDetectionRunner re-exported for compatibility)
from orchestrator.registry.agent_registry import AgentRegistry

# Register foundation model adapters
from . import adapters # noqa: F401

# Suppress experimental and informational warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.adk")

# ==========================================
# 1. Agent Initialization (Hierarchical)
# ==========================================

def initialize_agents() -> Agent:
    """
    Initializes the root orchestrator and its specialized sub-agents using a registry pattern.
    This demonstrates the Google ADK's ability to create a hierarchical
    multi-agent system dynamically.
    """
    # Clear registry to ensure test isolation and prevent duplicate loading
    AgentRegistry.clear()

    # Load core agents defined in orchestrator/agents/core_agents.py
    AgentRegistry.load_agents_from_module("orchestrator.agents.core_agents")
    
    # Load dynamic agents based on configuration (MCP, A2A)
    from orchestrator.agents.dynamic_agents import register_dynamic_agents
    register_dynamic_agents()
    
    # Get all registered agents
    sub_agents = AgentRegistry.get_all_agents()

    # Build generic root_agent instruction from registered sub-agents
    agent_capabilities = "\n".join([f"- {a.name}: {a.description}" for a in sub_agents if a.name != "reviewer_agent"])
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
# 2. Persistence Layer
# ==========================================

def get_persistence_services() -> tuple[Any, Any]:
    """Initializes and returns the configured persistence services."""
    if PERSISTENCE_BACKEND == "redis":
        import redis.asyncio as redis
        redis_client = redis.from_url(REDIS_URL)
        return RedisSessionService(redis_client), RedisMemoryService(redis_client)
    elif PERSISTENCE_BACKEND == "postgres":
        return DatabaseSessionService(POSTGRES_URL), PostgresMemoryService(POSTGRES_URL)
    return InMemorySessionService(), InMemoryMemoryService() # type: ignore


# Initialize globally for shared access
session_service, memory_service = get_persistence_services()
root_agent = initialize_agents()


# ==========================================
# 3. Execution Runners
# ==========================================

@asynccontextmanager
async def get_runner(agent: Agent) -> Any:
    """
    Ensures the runner is properly initialized with reviewer enforcement and loop detection.
    """
    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=session_service,
        memory_service=memory_service,
        auto_create_session=True
    )

    # EDUCATIONAL NOTE: Programmatic Reviewer Enforcement
    # The governance pipeline (loop detection + reviewer enforcement) is built by
    # orchestrator.reviewer.build_governed_runner so the CLI/evals path here and
    # the HTTP path in server.py share identical behavior. REVIEWER_ENFORCEMENT
    # is read via the config module attribute (not a from-import) so tests and
    # demos can toggle it with a config reload / patch.
    runner = build_governed_runner(
        runner, agent, enforce_review=config.REVIEWER_ENFORCEMENT
    )

    try:
        yield runner
    finally:
        pass


# ==========================================
# 4. Chat Logic
# ==========================================

async def run_chat_loop(prompt: Optional[str] = None) -> None:
    """Runs the main chat loop (CLI)."""
    async with get_runner(root_agent) as runner:
        if prompt:
            print(f"User: {prompt}")
            async for event in runner.run_async(
                user_id=DEFAULT_USER_ID,
                session_id=DEFAULT_SESSION_ID,
                new_message=Content(parts=[Part(text=prompt)]),
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(part.text, end="", flush=True)
            print("\n")
            return

        print(f"--- Welcome to {APP_NAME} ---")
        print("Type 'exit' or 'quit' to stop.")
        while True:
            try:
                user_input = input("User: ")
                if user_input.lower() in ["exit", "quit"]:
                    break

                print("Nexus: ", end="", flush=True)
                async for event in runner.run_async(
                    user_id=DEFAULT_USER_ID,
                    session_id=DEFAULT_SESSION_ID,
                    new_message=Content(parts=[Part(text=user_input)]),
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                print(part.text, end="", flush=True)
                print("\n")
            except (KeyboardInterrupt, EOFError):
                break
