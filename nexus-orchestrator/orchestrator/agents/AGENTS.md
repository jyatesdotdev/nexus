# orchestrator/agents/ — sub-agent definitions

This package defines every sub-agent that the Nexus root orchestrator can delegate to. Agents are not instantiated here directly; each is wrapped in a factory function registered with `AgentRegistry` (see `../registry/agent_registry.py`). At startup, `orchestrator/app.py` calls `AgentRegistry.load_agents_from_module("orchestrator.agents.core_agents")` and then `register_dynamic_agents()`, collects all factories, instantiates them, and passes the resulting agents as `sub_agents` of the root agent. The root agent's routing prompt is auto-generated from each agent's `description` field, so descriptions are load-bearing: they are what the LLM uses to pick an agent.

Loading gotcha: `load_agents_from_module` walks and imports/reloads every module in this package, so any new `.py` file added here will be auto-imported at startup — module-level side effects run whether you want them or not.

## Files

- `core_agents.py` — Six always-on agents, each a `@AgentRegistry.register("<name>")`-decorated factory returning an ADK `LlmAgent`:
  - `sensor_agent` — IoT sensor analysis; tool `get_sensor_reading` (mock data: temperature 22.5, humidity 45.0).
  - `metric_agent` — DevOps metrics; tool `query_prometheus_metric` (real Prometheus query with mock fallback).
  - `api_agent` — YNAB budget lookups; tool `fetch_ynab_budget` (mock data, always $150.00).
  - `parsing_agent` — entity extraction; tool `extract_entities_with_grounding` (mock).
  - `system_agent` — server health; tool `execute_safe_bash_command` (allow-list: uptime, df -h, free -m).
  - `reviewer_agent` — QA critic. The name `reviewer_agent` is matched literally in `orchestrator/app.py` (to exclude it from the routing list and to enable `ReviewerEnforcementRunner`) and in `orchestrator/reviewer.py`. Renaming it silently disables reviewer enforcement.
  Registered names must stay in sync with `expected_agent` values in `orchestrator/eval_cases.py`.
- `dynamic_agents.py` — `register_dynamic_agents()` registers remote agents from config at startup:
  - One MCP agent per URL in `MCP_SERVER_URLS` (from `orchestrator/config.py`). Named `mcp_agent` when there is exactly one URL, else `mcp_agent_0`, `mcp_agent_1`, ... Uses ADK `McpToolset` over SSE with `require_confirmation=False` (tools run without human approval — set True for destructive tools). Talks to the nexus-mcp HR directory server.
  - A2A agents are DISCOVERED, not hardwired: for each entry in `A2A_AGENT_URLS` (a base URL like `http://a2a-agent:8001` or a full card URL — `_agent_card_url` appends `/.well-known/agent-card.json` when missing), the card is fetched at registration time with `httpx.get` (3s timeout, `A2A_DISCOVERY_TIMEOUT_SECONDS`). The registered agent takes its NAME and DESCRIPTION from the card: `_sanitize_agent_name` lowercases and underscores the card name into a valid ADK identifier (nexus-a2a's "Weather Sub-Agent" → `weather_sub_agent`). Cards without a usable name fall back to the legacy scheme (`weather_a2a_agent` for a single URL, else `a2a_agent_{i}`); duplicate names get an `_{i}` suffix. Unreachable/invalid endpoints are logged (`_fetch_agent_card`) and skipped — startup never crashes on a dead A2A service. Adding a new A2A service to the stack = appending its URL to `A2A_AGENT_URLS`. Uses ADK `RemoteA2aAgent` pointed at the card URL. Because registration happens at `orchestrator.app` import time, unit tests must patch `httpx.get` (see tests/conftest.py).
  - `get_propagated_headers(user_id, session_id)` builds outgoing headers for both: `Authorization: Bearer <user_id>` (mock-JWT identity propagation) plus OpenTelemetry `traceparent` via `inject()`. When `inject()` finds an empty OTel context, it falls back to the session-mapped `TRACE_STORE` imported lazily from `orchestrator.middleware` (where it is defined and populated) — keep that import path in sync if `TRACE_STORE` ever moves.
  - The factory closures capture `url`/`name` via default arguments — keep that pattern or every agent will bind to the last loop value.
- `__init__.py` — Empty.

## How to test

```bash
cd /Users/jyates/Repositories/nexus/nexus-orchestrator
uv run pytest tests/test_initialization.py tests/test_orchestrator.py
```

`tests/test_initialization.py` asserts the multi-URL fallback naming scheme (`mcp_agent_0`, `a2a_agent_1`, ...); `tests/test_a2a_discovery.py` covers card-derived naming, URL normalization, and the unreachable-endpoint skip. LLM routing quality is measured separately with `uv run python main.py evals` (needs a real API key).

## Caution

- Do not rename registered agent names without updating `orchestrator/eval_cases.py`, `orchestrator/app.py` (reviewer exclusion), and tests. A2A agent names now come from each service's agent card — renaming a card (e.g. in nexus-a2a/server.py) renames the registered agent and must be reflected in `eval_cases.py`.
- Agent `description` strings drive LLM routing — edit them deliberately; vague or overlapping descriptions cause misrouting.
- Do not flip `require_confirmation` or remove the `Authorization` header without understanding that nexus-mcp/nexus-a2a expect the propagated identity token.
