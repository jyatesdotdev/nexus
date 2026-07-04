from pydantic import BaseModel
from typing import List

class EvalCase(BaseModel):
    name: str
    input: str
    expected_agent: str
    expected_keywords: List[str]
    description: str

# EDUCATIONAL NOTE: Multi-Agent Evaluation (Evals)
# Testing agentic systems is different from testing standard software. 
# Because LLMs are non-deterministic, we use "Evals" to run a large batch 
# of prompts and statistically measure accuracy, routing success, and 
# response quality against a known baseline.

EVAL_CASES = [
    # 1. Routing: Weather Agent
    # NOTE: A2A agents are now named from their discovered agent card
    # (see orchestrator/agents/dynamic_agents.py). nexus-a2a's card name is
    # "Weather Sub-Agent", which sanitizes to "weather_sub_agent".
    EvalCase(
        name="weather_paris",
        input="What is the weather like in Paris today?",
        expected_agent="weather_sub_agent",
        expected_keywords=["Paris", "weather", "temperature"],
        description="Verify routing to Weather Agent and city extraction."
    ),
    EvalCase(
        name="weather_london",
        input="Give me the forecast for London.",
        expected_agent="weather_sub_agent",
        expected_keywords=["London", "forecast"],
        description="Verify routing to Weather Agent."
    ),
    # 2. Routing: HR (MCP) Agent
    EvalCase(
        name="hr_search_engineering",
        input="Who works in the engineering department?",
        expected_agent="mcp_agent",
        expected_keywords=["engineering", "employees", "Dept"],
        description="Verify routing to HR Agent and department query."
    ),
    EvalCase(
        name="hr_search_alice",
        input="Search for Alice in the employee directory.",
        expected_agent="mcp_agent",
        expected_keywords=["Alice"],
        description="Verify routing to HR Agent and name search."
    ),
    # 3. Routing: API/YNAB Agent
    EvalCase(
        name="api_ynab_groceries",
        input="How much do I have left in my Groceries budget?",
        expected_agent="api_agent",
        expected_keywords=["Groceries", "balance", "$150.00"],
        description="Verify routing to API Agent and YNAB tool usage."
    ),
    # 4. Routing: System Agent
    EvalCase(
        name="system_uptime",
        input="How long has the server been running?",
        expected_agent="system_agent",
        expected_keywords=["uptime"],
        description="Verify routing to System Agent for uptime."
    ),
    EvalCase(
        name="system_disk",
        input="Check the available disk space.",
        expected_agent="system_agent",
        expected_keywords=["disk space", "df -h"],
        description="Verify routing to System Agent for disk space."
    ),
    # 5. Routing: Metric Agent
    EvalCase(
        name="metric_cpu",
        input="What is the current CPU usage of the cluster?",
        expected_agent="metric_agent",
        expected_keywords=["CPU", "usage", "95.4"],
        description="Verify routing to Metric Agent."
    ),
    # 6. Routing: Parsing Agent
    EvalCase(
        name="parsing_entities",
        input="Extract the name of the organization from this text: Google is based in Mountain View.",
        expected_agent="parsing_agent",
        expected_keywords=["Google", "organization", "extracted"],
        description="Verify routing to Parsing Agent."
    ),
    # 7. Routing: Sensor Agent
    EvalCase(
        name="sensor_data",
        input="Get the latest reading from sensor SENSOR_789.",
        expected_agent="sensor_agent",
        expected_keywords=["SENSOR_789", "temperature", "humidity"],
        description="Verify routing to Sensor Agent."
    ),
]
