# orchestrator/agents/ — sub-agent definitions

This package defines every sub-agent that the Nexus root orchestrator can delegate to. Agents are not instantiated here directly; each is wrapped in a factory function registered with `AgentRegistry` (see `../registry/agent_registry.py`). At startup, `orchestrator/app.py` calls `AgentRegistry.load_agents_from_module("orchestrator.agents.core_agents")` and then `register_dynamic_agents()`, collects all factories, instantiates them, and passes the resulting agents as `sub_agents` of the root agent. The root agent's routing prompt is auto-generated from each agent's `description` field, so descriptions are load-bearing: they are what the LLM uses to pick an agent.

Loading gotcha: `load_agents_from_module` walks and imports/reloads every module in this package, so any new `.py` file added here will be auto-imported at startup — module-level side effects run whether you want them or not.

## Files

- `core_agents.py` — Six always-on agents, each a `@AgentRegistry.register("<name>")`-decorated factory returning an ADK `LlmAgent`:
  - `sensor_agent` — IoT sensor analysis. Has NO tools (the mock `get_sensor_reading` tool exists in `../tools.py` but is not attached — the agent answers from the prompt alone).
  - `metric_agent` — DevOps metrics; tool `query_prometheus_metric` (real Prometheus query with mock fallback).
  - `api_agent` — YNAB budget lookups; tool `fetch_ynab_budget` (mock data, always $150.00).
  - `parsing_agent` — entity extraction; tool `extract_entities_with_grounding` (mock).
  - `system_agent` — server health; tool `execute_safe_bash_command` (allow-list: uptime, df -h, free -m).
  - `reviewer_agent` — QA critic. The name `reviewer_agent` is matched literally in `orchestrator/app.py` (to exclude it from the routing list and to enable `ReviewerEnforcementRunner`) and in `orchestrator/reviewer.py`. Renaming it silently disables reviewer enforcement.
  Registered names must stay in sync with `expected_agent` values in `orchestrator/eval_cases.py`.
- `dynamic_agents.py` — `register_dynamic_agents()` registers remote agents from config at startup:
  - One MCP agent per URL in `MCP_SERVER_URLS` (from `orchestrator/config.py`). Named `mcp_agent` when there is exactly one URL, else `mcp_agent_0`, `mcp_agent_1`, ... Uses ADK `McpToolset` over SSE with `require_confirmation=False` (tools run without human approval — set True for destructive tools). Talks to the nexus-mcp HR directory server.
  - One A2A agent per URL in `A2A_AGENT_URLS`. Named `weather_a2a_agent` for a single URL, else `a2a_agent_0`, ... Uses ADK `RemoteA2aAgent` pointed at the agent-card URL (nexus-a2a weather server, default `http://a2a-agent:8001/.well-known/agent-card.json`).
  - `get_propagated_headers(user_id, session_id)` builds outgoing headers for both: `Authorization: Bearer <user_id>` (mock-JWT identity propagation) plus OpenTelemetry `traceparent` via `inject()`. KNOWN BUG: its fallback does `from orchestrator.app import TRACE_STORE`, but `TRACE_STORE` actually lives in `orchestrator/middleware.py`; the ImportError is swallowed by the surrounding `except ImportError`, so the session-mapped trace fallback never fires. If you fix the import, import from `orchestrator.middleware`.
  - The factory closures capture `url`/`name` via default arguments — keep that pattern or every agent will bind to the last loop value.
- `__init__.py` — Empty.

## How to test

```bash
cd /Users/jyates/Repositories/nexus/nexus-orchestrator
./venv/bin/python -m pytest tests/test_initialization.py tests/test_orchestrator.py
```

`tests/test_initialization.py` specifically asserts the multi-URL naming scheme (`mcp_agent_0`, `a2a_agent_1`, ...). LLM routing quality is measured separately with `./venv/bin/python main.py evals` (needs a real API key).

## Caution

- Do not rename registered agent names without updating `orchestrator/eval_cases.py`, `orchestrator/app.py` (reviewer exclusion), and tests.
- Agent `description` strings drive LLM routing — edit them deliberately; vague or overlapping descriptions cause misrouting.
- Do not flip `require_confirmation` or remove the `Authorization` header without understanding that nexus-mcp/nexus-a2a expect the propagated identity token.
