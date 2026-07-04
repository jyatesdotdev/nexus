# nexus-__SERVICE_NAME__ — __SERVICE_TITLE__ A2A Sub-Agent

This directory is a standalone microservice in the Nexus multi-agent learning workspace, scaffolded from `nexus-stack/templates/a2a-service` (which is modeled on the canonical `nexus-a2a` weather agent). It implements a sub-agent that speaks the Agent-to-Agent (A2A) protocol using the `a2a-sdk` Python package. The root orchestrator (`../nexus-orchestrator`, a Google ADK agent) discovers this service dynamically: every URL in its `A2A_AGENT_URLS` environment variable has its agent card fetched at startup, and one sub-agent is registered per card, **named from the card's `name` field** ("__SERVICE_TITLE__ Sub-Agent" → `__SERVICE_SNAKE___sub_agent`). When the orchestrator routes a request here, this service streams A2A task-status events back: a "thinking" update followed by a final result.

The whole service is one Python module (`server.py`) plus tests. It depends on the sibling `nexus-common` (a uv-workspace source locally; `-e ../nexus-common` in Docker) for the shared `/health` endpoint, OpenTelemetry setup, and mock identity propagation (`IdentityContext`). It is normally run as the `__SERVICE_NAME__-agent` container defined in `../nexus-stack/docker-compose.yml`.

## Files at this level

- `server.py` — the entire service. Contains:
  - `process_query(user_message)`: pure domain-logic function. The scaffold implementation strips the orchestrator's `"For context:"` suffix and echoes the request back; **the `TODO` marker inside it is where the real capability goes.**
  - `__SERVICE_TITLE__AgentExecutor`: implements the A2A SDK `AgentExecutor` interface. `execute()` reads `Authorization` from `context.metadata` into a `nexus_common.IdentityContext`, enqueues a non-final `TaskStatusUpdateEvent` (thinking), optionally fetches upstream data via `_fetch_external_data` (only when `EXTERNAL_API_URL` is set), then enqueues a final `TaskStatusUpdateEvent` whose message carries the answer text and `metadata={"structured_data": {...}}` (type `__SERVICE_SNAKE___result`). Exactly two events per request — the tests assert this count. All errors (HTTP status, network, unexpected) become final messages; the executor never raises. `cancel()` is a no-op.
  - `AgentCard`: name "__SERVICE_TITLE__ Sub-Agent" (drives the orchestrator-side agent name — see the comment in the code), skill id `__SERVICE_SNAKE___capability`, `capabilities=AgentCapabilities(streaming=True)`, `url` from `__SERVICE_UPPER___PUBLIC_URL`.
  - Server wiring: `A2AStarletteApplication(...).build()` plus `bootstrap_starlette_service(service_name="__SERVICE_NAME__-agent", app=app)` for `/health` + telemetry. Env vars: `__SERVICE_UPPER___HOST` (default `0.0.0.0`), `__SERVICE_UPPER___PORT` (default `__PORT__`), `__SERVICE_UPPER___PUBLIC_URL` (default `http://__SERVICE_NAME__-agent:__PORT__` — the Docker network name, not localhost), `EXTERNAL_API_URL` (optional upstream API).
  - Endpoints served: agent card at `GET /.well-known/agent-card.json`, JSON-RPC at `POST /` (the SDK default), health at `GET /health`.
- `requirements.txt` — manual mirror of the pyproject deps, kept ONLY for the Dockerfile and CI installs (local dev uses the uv workspace). Pins `a2a-sdk[http-server]==0.3.25`: the 1.x line removes `a2a.server.apps.jsonrpc.starlette_app` and breaks `server.py` imports. Update BOTH files together when deps change.
- `pyproject.toml` — `[project]` runtime deps + `[dependency-groups]` dev tooling for the workspace-root uv workspace (`nexus-common` is a `{ workspace = true }` source; `[tool.uv] package = false`). Ruff targets py314; mypy strict; pytest `pythonpath = ["."]`.
- `Dockerfile` — multi-stage build; the build context must be the workspace parent directory (it copies `nexus-common/`), which is how `../nexus-stack/docker-compose.yml` invokes it (`context: ..`). Non-root `appuser`, curl HEALTHCHECK against the agent card, gunicorn with 1 uvicorn worker on `0.0.0.0:__PORT__`.
- `README.md` — human-facing overview; keep in sync with this file.
- `CHANGELOG.md` — reverse-chronological history.

## Subdirectories

- `tests/` — pytest suite for `server.py` (see `tests/AGENTS.md`). All external I/O mocked (respx); no live network calls.

## How to run and test

```bash
cd /path/to/workspace && uv sync        # once (requires this project in the root pyproject.toml workspace members)
cd nexus-__SERVICE_NAME__
uv run pytest tests/
uv run ruff check .
uv run python server.py                 # serves http://localhost:__PORT__
curl http://localhost:__PORT__/.well-known/agent-card.json
```

## Caution / do not modify without checking consumers

- Port `__PORT__`, the agent-card path, and the container name `__SERVICE_NAME__-agent` are referenced by `../nexus-stack/docker-compose.yml`, the orchestrator's `A2A_AGENT_URLS`, this Dockerfile's HEALTHCHECK, and `../nexus-dev-infra/prometheus.yml`. Change one, change all.
- The `AgentCard` name drives the orchestrator-side agent name; renaming it renames the agent the LLM routes to.
- The two-event streaming contract (one non-final `working` update, one `final=True` `completed` update) is asserted by tests and consumed upstream. Do not add or reorder events casually.
- Tests must never hit real networks; all HTTP is mocked with `respx`.
- Project convention: explain non-obvious design choices with `# EDUCATIONAL NOTE:` comments (Semgrep-enforced once this directory is added to `nexus-stack/.semgrep.yaml`).
