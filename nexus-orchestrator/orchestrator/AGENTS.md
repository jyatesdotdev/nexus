# orchestrator/ — application package

This package is the entire application code of the Nexus orchestrator: a Google ADK "root agent" that routes user requests to specialized sub-agents (local tool agents, a remote MCP HR agent, a remote A2A weather agent) and exposes itself through a CLI and a FastAPI/SSE web server. The package is imported as `orchestrator` from the repo root (there is no src/ layout and no installable package; the repo root must be on sys.path).

IMPORTANT side-effect: importing `orchestrator.app` builds the root agent and the persistence services at module import time (`root_agent = initialize_agents()` and `session_service, memory_service = get_persistence_services()` run at the bottom of app.py). All environment variables (AGENT_MODEL, PERSISTENCE_BACKEND, MCP_SERVER_URLS, A2A_AGENT_URLS, ...) must be set BEFORE anything imports `orchestrator.app`. Tests that change env vars must `importlib.reload` config and app.

## Files at this level

- `app.py` — Core wiring. `initialize_agents()` clears the `AgentRegistry`, loads core agents from `orchestrator.agents.core_agents`, registers dynamic MCP/A2A agents, then builds `root_agent` whose routing instruction is generated from each sub-agent's `description` (the `reviewer_agent` is excluded from the routing list by the literal name check `a.name != "reviewer_agent"`). `get_persistence_services()` picks InMemory/Redis/Postgres from `PERSISTENCE_BACKEND`. `get_runner()` wraps an ADK `Runner` with `LoopDetectionRunner` (only prints a warning after >10 author changes; it does not stop the loop) and, if a sub-agent named exactly `reviewer_agent` exists, with `ReviewerEnforcementRunner`. NOTE: `get_runner()` is used only by the CLI chat loop and evals — the web server (AdkWebServer) builds its own runners, so reviewer enforcement does NOT apply to HTTP `/run_sse` traffic, only prompt-level review does. `run_chat_loop()` implements the CLI chat. Gotcha: the line `from . import adapters` is intended to register model adapters, but `adapters/__init__.py` is empty, so it registers nothing (see adapters/AGENTS.md).
- `asgi.py` — 4 lines. Builds the FastAPI app for Gunicorn (`orchestrator.asgi:app`, used by the Dockerfile CMD). Does not call `validate_config()`, so a missing API key only surfaces at first model call in server mode.
- `server.py` — `create_app_instance()` wraps the root agent in ADK's `AdkWebServer` (standard endpoints incl. `POST /run_sse` for streaming chat and session management), with a `SimpleAgentLoader` that answers to the names `root_agent`, `containerized_agents`, and `""` and 404s anything else. Adds CORS `allow_origins=["*"]` (lab environment), the identity/session middleware from `middleware.py`, `bootstrap_fastapi_service(service_name="orchestrator", ...)` from nexus-common (adds `/health` and OpenTelemetry/Prometheus telemetry), and a custom `GET /system-status` endpoint that probes Prometheus (`PROMETHEUS_URL`, default `http://prometheus:9090`), the first MCP server URL, and the first A2A agent card URL with 2-second timeouts.
- `cli.py` — Click CLI with three commands: `chat [PROMPT]` (interactive or one-shot), `serve --host 0.0.0.0 --port 8080`, and `evals` (runs every case in `eval_cases.py` against the real model and reports routing + keyword pass/fail). The CLI group calls `validate_config()`, so `GEMINI_API_KEY` or `GOOGLE_API_KEY` must be set for any CLI command.
- `config.py` — The ONLY place that reads environment variables for app configuration; keep it that way. Defines `AGENT_MODEL` (default `gemini-2.5-flash`), `PERSISTENCE_BACKEND` (`in_memory`/`redis`/`postgres`), `REDIS_URL`, `POSTGRES_URL` (must be an async SQLAlchemy URL, i.e. `postgresql+asyncpg://...`), `MCP_SERVER_URLS` and `A2A_AGENT_URLS` (comma-separated lists; legacy single-value fallbacks `MCP_SERVER_URL`/`A2A_AGENT_URL`), `APP_NAME = "containerized_agents"` (must remain a valid Python identifier — a test enforces this, and it is baked into persisted session keys), `DEFAULT_USER_ID`, `DEFAULT_SESSION_ID`, and `validate_config()`.
- `middleware.py` — FastAPI HTTP middleware applied only to `POST /run_sse`: replays the request body, verifies the mock JWT in the `user_id` field via `verify_token` from nexus-common (401 `INVALID_IDENTITY` on failure), stores the current OpenTelemetry trace headers in the module-level `TRACE_STORE` dict keyed by session_id, and auto-creates the session if it does not exist (so the UI works after a persistence flush). Gotchas: (1) `TRACE_STORE` is defined HERE, but `agents/dynamic_agents.py` tries to import it from `orchestrator.app` — that import fails silently, so the trace-header fallback is currently dead code; if you fix one side, fix the other. (2) The auto-create path calls `session_service.get_session(session_id)` positionally, but every session service takes keyword-only arguments, so that call always raises and `create_session` runs on every request; with the Redis backend `create_session` overwrites the stored session with a fresh empty one, which can wipe history. (3) All exceptions in the middleware body are swallowed with `except Exception: pass`.
- `reviewer.py` — `ReviewerEnforcementRunner`: a decorator/wrapper around an ADK Runner that buffers all non-reviewer response text from a run, then sends it to the `reviewer_agent` with a "reply APPROVED or REVISION" prompt using a second Runner, and streams the review events after the normal events. Delegates every other attribute to the wrapped runner via `__getattr__`. The agent name `reviewer_agent` is a load-bearing string shared with `agents/core_agents.py` and `app.py`.
- `tools.py` — Tool functions given to sub-agents plus their Pydantic result models. All tools return Pydantic models (SensorReading, MetricValue, BudgetBalance, ExtractedEntities, BashOutput). Docstrings are MANDATORY — the LLM reads them to decide how to call the tool. `query_prometheus_metric` is the only real one (async httpx call to `PROMETHEUS_URL`, falls back to a mock value `95.4` with status `"mock"` if unreachable); sensor/YNAB/entity tools return hardcoded mock data (evals depend on the mock values, e.g. `$150.00` and `95.4`). `execute_safe_bash_command` enforces a strict allow-list (`uptime`, `df -h`, `free -m`) — never widen it casually; it runs `subprocess.run` on the host/container.
- `eval_cases.py` — Declarative eval dataset (`EvalCase` Pydantic model + `EVAL_CASES` list) used by `main.py evals`. Each case's `expected_agent` must exactly match a registered agent name (`weather_a2a_agent`, `mcp_agent`, `api_agent`, `system_agent`, `metric_agent`, `parsing_agent`, `sensor_agent`), and `expected_keywords` must match the mock tool outputs in `tools.py`. If you rename an agent or change mock data, update this file.
- `__init__.py` — Empty.

## Subdirectories

- `agents/` — Sub-agent factory definitions (core + dynamic MCP/A2A). See `agents/AGENTS.md`.
- `adapters/` — Custom `BaseLlm` adapters (Ollama, skeletal Bedrock). See `adapters/AGENTS.md`.
- `persistence/` — Redis and Postgres implementations of ADK session/memory services. See `persistence/AGENTS.md`.
- `registry/` — The `AgentRegistry` decorator/registry pattern. See `registry/AGENTS.md`.

## How to run/test

From the repo root (`/Users/jyates/Repositories/nexus/nexus-orchestrator`):

```bash
./venv/bin/python main.py serve            # HTTP server on :8080
./venv/bin/python main.py chat "hello"     # CLI
./venv/bin/python -m pytest tests/         # unit tests (mocked, no key needed)
./venv/bin/mypy orchestrator               # strict typing is enforced project-wide
```

## Caution / do not modify

- Do not rename `reviewer_agent`, `root_agent`, or `APP_NAME` without tracing every literal usage (app.py, reviewer.py, server.py SimpleAgentLoader, agents/core_agents.py, tests, persisted session keys).
- Do not add `os.getenv` calls outside `config.py` (existing exceptions: `PROMETHEUS_URL` in server.py/tools.py, `OLLAMA_BASE_URL` in the adapter, API keys in persistence).
- Do not make `app.py` do domain work — it must stay a thin router; put domain logic in sub-agents/tools.
- Do not extend the bash allow-list in `tools.py` without a security reason.
