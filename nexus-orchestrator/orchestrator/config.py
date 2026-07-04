# OS: The standard library module for operating system interactions.
import os

# CONSTANTS: In Python, variables in ALL_CAPS are treated as constants by convention.
# EDUCATIONAL NOTE: [Why] They are values that are set once and not changed during program execution.
# Using uppercase makes them easily identifiable throughout the project.

# OS.GETENV: Reads an environment variable.
# EDUCATIONAL NOTE: [How] os.getenv("VARIABLE_NAME", "default_value").
# EDUCATIONAL NOTE: [Why] This allows configuration to be external to the code. If the variable
# isn't set in the environment, it safely falls back to the provided default.
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
PERSISTENCE_BACKEND = os.getenv("PERSISTENCE_BACKEND", "in_memory")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+asyncpg://nexus:password@localhost:5432/nexus_dev")


# PARSE LISTS: Helper to get multiple URLs from comma-separated env vars.
def get_env_list(var_name: str, default: str) -> list[str]:
    raw_val = os.getenv(var_name, default)
    # Split by comma and strip whitespace, filter out empty strings
    return [url.strip() for url in raw_val.split(",") if url.strip()]


# DYNAMIC AGENT CONFIGS: Multiple endpoints for MCP and A2A.
# If MCP_SERVER_URLS isn't set, it falls back to the legacy single variable or a default.
MCP_SERVER_URLS = get_env_list(
    "MCP_SERVER_URLS", os.getenv("MCP_SERVER_URL", "http://mcp-server:8000/sse")
)
A2A_AGENT_URLS = get_env_list(
    "A2A_AGENT_URLS",
    os.getenv("A2A_AGENT_URL", "http://a2a-agent:8001/.well-known/agent-card.json"),
)

APP_NAME = "containerized_agents"
DEFAULT_USER_ID = "default_user"
DEFAULT_SESSION_ID = "chat_session_001"


def validate_config() -> None:
    """
    Checks the environment to ensure essential API keys are present.
    """
    # BOOLEAN LOGIC: 'not A and not B' checks if neither key is available.
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        # EXCEPTIONS: RAISING an error stops the program from running with
        # invalid configuration.
        # EDUCATIONAL NOTE: [Why] Better to crash immediately with a clear 'ValueError' than to
        # fail later with a cryptic error from a network library.
        raise ValueError(
            "Missing API Key. Please set GEMINI_API_KEY in your .env file."
        )
