from google.adk.agents.llm_agent import LlmAgent as Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from orchestrator.registry.agent_registry import AgentRegistry
from orchestrator.config import MCP_SERVER_URLS, A2A_AGENT_URLS
from typing import Dict

# EDUCATIONAL NOTE: Distributed Trace Context Propagation
# [Why] To link traces across different microservices, we must explicitly extract
# the current OpenTelemetry trace context and inject it as HTTP headers
# (e.g., 'traceparent') into outgoing requests made by the ADK tools.
# ADK sometimes loses the native OTel context in background threads, so we
# fallback to a session-mapped TRACE_STORE defined in orchestrator.middleware.
def get_propagated_headers(user_id: str, session_id: str = None) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {user_id}"}
    try:
        from opentelemetry.propagate import inject
        inject(headers)

        # Fallback to cached headers if inject found an empty OTel context
        if "traceparent" not in headers and session_id:
            from orchestrator.middleware import TRACE_STORE
            if session_id in TRACE_STORE:
                headers.update(TRACE_STORE[session_id])
    except ImportError:
        pass
    return headers

# This approach allows for dynamic registration based on config,
# but it requires being called during app initialization.
def register_dynamic_agents() -> None:
    for i, mcp_url in enumerate(MCP_SERVER_URLS):
        name = "mcp_agent" if len(MCP_SERVER_URLS) == 1 else f"mcp_agent_{i}"
        
        def create_mcp_agent(url: str = mcp_url, agent_name: str = name) -> Agent:
            # EDUCATIONAL NOTE: Tool Confirmation
            # [Why] require_confirmation=False allows the agent to execute tools 
            # without manual user approval. For sensitive operations like 'delete_user',
            # you would typically set this to True.
            mcp_toolset = McpToolset(
                connection_params=SseConnectionParams(url=url),
                require_confirmation=False,
                header_provider=lambda ctx: get_propagated_headers(ctx.user_id, getattr(ctx, "session_id", None))
            )
            return Agent(
                name=agent_name,
                instruction=f"You are an HR assistant connecting to MCP server at {url}. Use its tools to query or modify the database.",
                description=f"HR assistant specialized in employee database queries and modifications via MCP server at {url}.",
                tools=[mcp_toolset],
            )
            
        AgentRegistry.register(name)(create_mcp_agent)

    for i, a2a_url in enumerate(A2A_AGENT_URLS):
        name = "weather_a2a_agent" if len(A2A_AGENT_URLS) == 1 else f"a2a_agent_{i}"
        
        def create_a2a_agent(url: str = a2a_url, agent_name: str = name) -> RemoteA2aAgent:
            return RemoteA2aAgent(
                name=agent_name,
                agent_card=url,
                description=f"A remote sub-agent connecting to A2A card at {url}. Specialized in weather forecasts.",
                a2a_request_meta_provider=lambda ctx, msg: get_propagated_headers(ctx.user_id, getattr(ctx, "session_id", None))
            )
            
        AgentRegistry.register(name)(create_a2a_agent)
