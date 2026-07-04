from google.adk.agents.llm_agent import LlmAgent as Agent
from orchestrator.registry.agent_registry import AgentRegistry
from orchestrator.tools import (
    execute_safe_bash_command,
    fetch_ynab_budget,
    extract_entities_with_grounding,
    get_sensor_reading,
    query_prometheus_metric,
)

# EDUCATIONAL NOTE: Every tool-backed agent must actually be given its tool.
# The sensor eval case ("Get the latest reading from sensor SENSOR_789",
# expecting temperature/humidity keywords) relies on get_sensor_reading's
# mock output — without the tool the agent could only hallucinate readings.
@AgentRegistry.register("sensor_agent")
def create_sensor_agent() -> Agent:
    return Agent(
        name="sensor_agent",
        instruction="You are a data analyst for IoT sensors. Analyze readings and report anomalies.",
        description="Expert in analyzing raw IoT sensor data and identifying trends.",
        tools=[get_sensor_reading],
    )

@AgentRegistry.register("metric_agent")
def create_metric_agent() -> Agent:
    return Agent(
        name="metric_agent",
        instruction="You are a DevOps engineer. Monitor system metrics and suggest optimizations.",
        description="Specialized in cloud infrastructure metrics and performance tuning.",
        tools=[query_prometheus_metric],
    )

@AgentRegistry.register("api_agent")
def create_api_agent() -> Agent:
    return Agent(
        name="api_agent",
        instruction="You are a financial assistant. Check budget balances from YNAB.",
        description="Financial assistant for retrieving budget balances from YNAB.",
        tools=[fetch_ynab_budget],
    )

@AgentRegistry.register("parsing_agent")
def create_parsing_agent() -> Agent:
    return Agent(
        name="parsing_agent",
        instruction="You are an extraction expert. Extract entities from text.",
        description="Specialist in extracting specific entities from unstructured text.",
        tools=[extract_entities_with_grounding],
    )

@AgentRegistry.register("system_agent")
def create_system_agent() -> Agent:
    return Agent(
        name="system_agent",
        instruction="You are a system administrator. Check system status using bash tools only for uptime and disk space.",
        description="System administrator for basic server health (uptime, disk) as a fallback.",
        tools=[execute_safe_bash_command],
    )

@AgentRegistry.register("reviewer_agent")
def create_reviewer_agent() -> Agent:
    return Agent(
        name="reviewer_agent",
        instruction=(
            "You are a strict QA Reviewer. Your job is to review the drafted responses or tool outputs of other agents. "
            "Ensure the information is accurate, safe, and formatted correctly. "
            "Do not provide the final answer yourself, but critique and tell the orchestrator if it is 'APPROVED' or if it needs 'REVISION' with specific feedback."
        ),
        description="Quality Assurance reviewer. Must be used to critique and approve all outgoing responses before they are presented to the user.",
    )