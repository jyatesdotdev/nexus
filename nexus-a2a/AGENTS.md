# nexus-a2a — A2A Weather Sub-Agent

This repo is a standalone microservice in the Nexus multi-agent learning workspace. It implements a weather-forecasting sub-agent that speaks the Agent-to-Agent (A2A) protocol using the `a2a-sdk` Python package. The root orchestrator (sibling repo `nexus-orchestrator`, a Google ADK agent) discovers this service at runtime by fetching its agent card from `http://a2a-agent:8001/.well-known/agent-card.json` and wraps it as a remote sub-agent named `weather_a2a_agent`. When asked about weather, the orchestrator delegates the query here over JSON-RPC; this service extracts a city name from the natural-language message, fetches live conditions from the public `wttr.in` API, and streams A2A task-status events back (a "thinking" update followed by a final result with structured weather metadata).

The whole service is one Python module (`server.py`) plus tests. It depends on the sibling repo `nexus-common` (installed editable via `-e ../nexus-common`) for the shared `/health` endpoint, OpenTelemetry setup, and mock identity propagation (`IdentityContext`). It is normally run as the `a2a-agent` container defined in `../nexus-stack/docker-compose.yml`. Historical note: this repo was previously named `nexus-weather` (see the CHANGELOG title); the empty `../nexus-weather/` directory in the workspace is a leftover of that rename, not a separate project.

## Files at this level

- `server.py` — the entire service. Contains:
  - `extract_city(user_message)`: heuristic city parser. Strips anything after a literal `"For context:"` marker, then looks for the word `in` and takes everything after it; otherwise, if the message contains none of the words what/how/weather/forecast, treats the whole message as the city. Falls back to `"London"`. Tests in `tests/test_server.py` pin this behavior exactly.
  - `WeatherAgentExecutor`: implements the A2A SDK `AgentExecutor` interface. `execute()` reads the `Authorization` value from `context.metadata` into a `nexus_common.IdentityContext` (mock JWT — no real validation), enqueues a non-final `TaskStatusUpdateEvent` ("Fetching weather data for **{city}**..."), calls `https://wttr.in/{city}?format=j1` via `httpx` (10 s timeout), then enqueues a final `TaskStatusUpdateEvent` whose message carries the answer text and a `metadata={"structured_data": {...}}` payload (type `weather_forecast`, city, temp_f, temp_c, description, humidity, wind_speed). Exactly two events per request — the tests assert this count. HTTP status errors ("Could not retrieve weather for {city}. The service returned status {code}."), network errors, malformed-payload parse errors (`KeyError`/`IndexError`/`TypeError` → "Could not parse weather data for {city}."), and everything else are caught and turned into a final message; the executor never raises to the caller. `cancel()` is a no-op.
  - `AgentCard`: name "Weather Sub-Agent", version 1.0.0, one skill with id `weather_forecast`, `capabilities=AgentCapabilities(streaming=True)`, `url` taken from `A2A_PUBLIC_URL`. This card is what the orchestrator routes on.
  - Server wiring: `A2AStarletteApplication(agent_card, DefaultRequestHandler(WeatherAgentExecutor(), InMemoryTaskStore())).build()` produces the ASGI `app`, then `bootstrap_starlette_service(service_name="a2a-agent", app=app)` (from nexus-common) adds `GET /health` and OpenTelemetry instrumentation. Env vars: `A2A_HOST` (default `0.0.0.0`), `A2A_PORT` (default `8001`), `A2A_PUBLIC_URL` (default `http://a2a-agent:{PORT}` — the Docker network name, not localhost). Running `python server.py` starts uvicorn with reload.
  - Endpoints served: agent card at `GET /.well-known/agent-card.json`, JSON-RPC at `POST /` (the SDK default — there is no `/rpc` route), health at `GET /health`.
- `requirements.txt` — runtime + dev deps in one file, including `-e ../nexus-common` (a relative path: `pip install -r requirements.txt` must be run from this repo's root with the sibling checkout present). Pins `a2a-sdk[http-server]==0.3.25`: the code only works with the 0.3.x line — a2a-sdk 1.x removes `a2a.server.apps.jsonrpc.starlette_app` and `server.py` fails at import. Do not loosen the pin without migrating the imports.
- `pyproject.toml` — tool config only (no `[project]` section; this is not a package). Ruff targets py314 with line length 88; mypy is `strict = true` (server.py carries a few `# type: ignore[list-item]` comments to satisfy it).
- `Dockerfile` — multi-stage build. The build context must be the workspace parent directory (it copies `nexus-a2a/requirements.txt` and `nexus-common/`), which is how `../nexus-stack/docker-compose.yml` invokes it (`context: ..`). Final image: `python:3.14-slim`, non-root `appuser`, curl-based HEALTHCHECK against `/.well-known/agent-card.json`, `PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc` (wiped on start), CMD runs gunicorn with 1 uvicorn worker bound to `0.0.0.0:8001`.
- `.dockerignore` — keeps `venv/`, caches, `.env`, and `.git` out of the image build context.
- `README.md` — human-facing architecture explanation; documents the JSON-RPC endpoint as `POST /` and refers readers here for agent-facing detail.
- `CHANGELOG.md` — brief history; titled "Nexus Weather (A2A)" (the repo's former name). Mentions a "client template" that no longer exists in this repo.
- `.gitignore` — venv, caches, `.env`.
- `venv/` (untracked, gitignored) — local virtualenv created with `python3 -m venv venv` and populated from `requirements.txt` (which pulls in `a2a-sdk 0.3.25`, test deps, and the editable `nexus-common`). If its shebangs ever go stale (e.g. after moving the repo), just delete and recreate it.
- `.mypy_cache/`, `.ruff_cache/`, `tests/__pycache__/` — tool caches, ignore.

## Subdirectories

- `tests/` — pytest suite for `server.py`. See `tests/AGENTS.md`. All 5 tests pass.

## How to run and test

Docker (the normal path — the whole stack lives in `../nexus-stack`):

```bash
cd ../nexus-stack
make up          # builds and starts all services including a2a-agent on :8001
make logs        # tail logs
```

Local, without Docker (requires the `nexus-common` sibling checkout):

```bash
cd /Users/jyates/Repositories/nexus/nexus-a2a
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # includes the a2a-sdk[http-server]==0.3.25 pin
python server.py                  # serves http://localhost:8001
curl http://localhost:8001/.well-known/agent-card.json   # discovery card
```

Tests, lint, types (from this repo's root — tests import `server` as a top-level module):

```bash
PYTHONPATH=. venv/bin/python -m pytest tests/   # this is how ../nexus-stack/Makefile runs it
venv/bin/python -m ruff check .
venv/bin/python -m ruff format .
venv/bin/python -m mypy server.py
```

## Caution / do not modify without checking consumers

- Port `8001`, the agent-card path `/.well-known/agent-card.json`, and the container name `a2a-agent` are hardcoded in: `../nexus-orchestrator/orchestrator/config.py` (default `A2A_AGENT_URL`), `../nexus-stack/docker-compose.yml` (env, ports, healthcheck), this repo's `Dockerfile` HEALTHCHECK, and `../nexus-dev-infra/prometheus.yml` (scrape target). Change one, change all.
- The `AgentCard` contents (name, skill id `weather_forecast`, description, `streaming=True`) are what the orchestrator's `weather_a2a_agent` uses for routing/delegation. Keep the card truthful and keep `A2A_PUBLIC_URL` reachable from the orchestrator's network namespace (in Docker that is `http://a2a-agent:8001`, never `localhost`).
- The two-event streaming contract (one non-final `working` update, one `final=True` `completed` update) and the `metadata["structured_data"]` shape are asserted by tests and consumed upstream. Do not add or reorder events casually.
- `GET /health` comes from `nexus_common.bootstrap_starlette_service`; do not remove that call — Docker healthchecks and the orchestrator's system-status rely on the conventions it installs.
- Tests must never hit real networks; all HTTP is mocked with `respx`. Keep it that way.
- Do not bump `a2a-sdk` to 1.x without migrating imports (`a2a.server.apps.jsonrpc.starlette_app` does not exist there).
- Project convention: explain non-obvious design choices with `# EDUCATIONAL NOTE:` comments; this is a learning codebase and clarity beats cleverness.
