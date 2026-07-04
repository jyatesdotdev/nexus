# nexus-a2a — A2A Weather Sub-Agent

This repo is a standalone microservice in the Nexus multi-agent learning workspace. It implements a weather-forecasting sub-agent that speaks the Agent-to-Agent (A2A) protocol using the `a2a-sdk` Python package. The root orchestrator (sibling repo `nexus-orchestrator`, a Google ADK agent) discovers this service at runtime by fetching its agent card from `http://a2a-agent:8001/.well-known/agent-card.json` and wraps it as a remote sub-agent named `weather_sub_agent`. When asked about weather, the orchestrator delegates the query here over JSON-RPC; this service extracts a city name from the natural-language message, fetches live conditions from the public `wttr.in` API, and streams A2A task-status events back (a "thinking" update followed by a final result with structured weather metadata).

The whole service is one Python module (`server.py`) plus tests. It depends on the sibling repo `nexus-common` (installed editable via `-e ../nexus-common`) for the shared `/health` endpoint, OpenTelemetry setup, and mock identity propagation (`IdentityContext`). It is normally run as the `a2a-agent` container defined in `../nexus-stack/docker-compose.yml`. Historical note: this repo was previously named `nexus-weather` (see the CHANGELOG title); the empty `../nexus-weather/` directory in the workspace is a leftover of that rename, not a separate project.

## Files at this level

- `server.py` — the entire service. Contains:
  - `extract_city(user_message) -> Optional[str]`: heuristic city parser, hardened 2026-07-04 after a live incident (the orchestrator's delegated message contained "in the engineering department" from an earlier HR turn; the old parser latched onto it and wttr.in fuzzy-geocoded the nonsense into a confident forecast). Strips anything after a literal `"For context:"` marker, then looks for the word `in` and takes everything after it; otherwise, if the message contains none of the words what/how/weather/forecast, treats the whole message as the candidate. The candidate is then sanitized (trailing temporal words like "today"/"tonight" and leading articles stripped) and rejected — return `None`, NEVER a guess (the old `"London"` fallback is gone) — when empty or containing any `_NON_PLACE_WORDS` token (department/team/office/morning/...). `None` means "ask the user for a location". Tests in `tests/test_server.py` pin this behavior exactly.
  - `resolved_area_matches(candidate, data)`: second line of defense. wttr.in fuzzy-geocodes ANY path segment (nonsense never 404s), so after fetching, the j1 payload's `nearest_area` (areaName/region/country values) is checked for loose case-insensitive token overlap with the requested candidate. Missing/malformed `nearest_area` counts as a match (can't validate; also keeps older payloads and the mocked happy-path tests working). On mismatch the executor asks for clarification instead of reporting the fuzzy result.
  - `CLARIFICATION_TEXT`: the canned "which city or place would you like the weather for?" reply used when `extract_city` returns None.
  - `WeatherAgentExecutor`: implements the A2A SDK `AgentExecutor` interface. `execute()` reads the `Authorization` value from `context.metadata` into a `nexus_common.IdentityContext` (mock JWT — no real validation), enqueues a non-final `TaskStatusUpdateEvent` ("Fetching weather data for **{city}**...", or "Looking for a location in the request..." when no city was extracted), then either (a) asks for a specific location (no-location path — no HTTP call happens — or unrelated-resolution path; no `structured_data` rides on a clarification) or (b) calls `https://wttr.in/{city}?format=j1` via `httpx` (10 s timeout, helper `_fetch_weather_data`), validates the resolution with `resolved_area_matches`, and enqueues a final `TaskStatusUpdateEvent` whose message carries the answer text and a `metadata={"structured_data": {...}}` payload (type `weather_forecast`, city, temp_f, temp_c, description, humidity, wind_speed). Exactly two events per request ON EVERY PATH (helper `_enqueue_status`) — the tests assert this count. Clarification finals use `TaskState.completed`, not `input_required`, to preserve the simple two-event contract (EDUCATIONAL NOTE in the code explains the tradeoff). HTTP status errors ("Could not retrieve weather for {city}. The service returned status {code}."), network errors, malformed-payload parse errors (`KeyError`/`IndexError`/`TypeError` → "Could not parse weather data for {city}."), and everything else are caught and turned into a final message; the executor never raises to the caller. `cancel()` is a no-op.
  - `AgentCard`: name "Weather Sub-Agent", version 1.0.0, one skill with id `weather_forecast`, `capabilities=AgentCapabilities(streaming=True)`, `url` taken from `A2A_PUBLIC_URL`. This card is what the orchestrator routes on.
  - Server wiring: `A2AStarletteApplication(agent_card, DefaultRequestHandler(WeatherAgentExecutor(), InMemoryTaskStore())).build()` produces the ASGI `app`, then `bootstrap_starlette_service(service_name="a2a-agent", app=app)` (from nexus-common) adds `GET /health` and OpenTelemetry instrumentation. Env vars: `A2A_HOST` (default `0.0.0.0`), `A2A_PORT` (default `8001`), `A2A_PUBLIC_URL` (default `http://a2a-agent:{PORT}` — the Docker network name, not localhost). Running `python server.py` starts uvicorn with reload.
  - Endpoints served: agent card at `GET /.well-known/agent-card.json`, JSON-RPC at `POST /` (the SDK default — there is no `/rpc` route), health at `GET /health`.
- `requirements.txt` — manual mirror of the pyproject deps (runtime + dev tooling), kept ONLY for the Dockerfile and CI installs, including `-e ../nexus-common` (a relative path: `pip install -r requirements.txt` must be run from this directory with the sibling checkout present). Local dev uses the uv workspace instead (see below). Pins `a2a-sdk[http-server]==0.3.25`: the code only works with the 0.3.x line — a2a-sdk 1.x removes `a2a.server.apps.jsonrpc.starlette_app` and `server.py` fails at import. Do not loosen the pin (here or in pyproject.toml) without migrating the imports; update BOTH files together when deps change.
- `pyproject.toml` — `[project]` deps (runtime) + `[dependency-groups]` dev (tooling) for the workspace-root uv workspace (`nexus-common` is a `{ workspace = true }` source; `[tool.uv] package = false` because this is an app, not an importable package), plus tool config. Ruff targets py314 with line length 88; mypy is `strict = true` (server.py carries a few `# type: ignore[list-item]` comments to satisfy it); pytest config sets `pythonpath = ["."]` so tests can `import server` from any invocation directory.
- `Dockerfile` — multi-stage build. The build context must be the workspace parent directory (it copies `nexus-a2a/requirements.txt` and `nexus-common/`), which is how `../nexus-stack/docker-compose.yml` invokes it (`context: ..`). Final image: `python:3.14-slim`, non-root `appuser`, curl-based HEALTHCHECK against `/.well-known/agent-card.json`, `PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc` (wiped on start), CMD runs gunicorn with 1 uvicorn worker bound to `0.0.0.0:8001`.
- `.dockerignore` — keeps `venv/`, caches, `.env`, and `.git` out of the image build context.
- `README.md` — human-facing architecture explanation; documents the JSON-RPC endpoint as `POST /` and refers readers here for agent-facing detail.
- `CHANGELOG.md` — brief history; titled "Nexus Weather (A2A)" (the repo's former name). Mentions a "client template" that no longer exists in this repo.
- `.gitignore` — venv, caches, `.env`.
- `.mypy_cache/`, `.ruff_cache/`, `tests/__pycache__/` — tool caches, ignore.

There is no per-service `venv/` anymore (removed 2026-07-04): the local environment is the shared `.venv/` at the workspace root, managed by `uv sync` against the root `pyproject.toml`/`uv.lock`.

## Subdirectories

- `tests/` — pytest suite for `server.py`. See `tests/AGENTS.md`. All 8 tests pass.

## How to run and test

Docker (the normal path — the whole stack lives in `../nexus-stack`):

```bash
cd ../nexus-stack
make up          # builds and starts all services including a2a-agent on :8001
make logs        # tail logs
```

Local, without Docker (uses the uv workspace at the repo root — one `uv sync` there serves all four Python projects):

```bash
cd /Users/jyates/Repositories/nexus && uv sync   # once; creates the shared root .venv
cd nexus-a2a
uv run python server.py           # serves http://localhost:8001
curl http://localhost:8001/.well-known/agent-card.json   # discovery card
```

Tests, lint, types (from this directory; `uv run` resolves the workspace env automatically — add `--no-sync` to skip the resolution check, which is how `../nexus-stack/Makefile` runs it):

```bash
uv run pytest tests/
uv run ruff check .
uv run ruff format .
uv run mypy server.py
```

## Caution / do not modify without checking consumers

- Port `8001`, the agent-card path `/.well-known/agent-card.json`, and the container name `a2a-agent` are hardcoded in: `../nexus-orchestrator/orchestrator/config.py` (default `A2A_AGENT_URL`), `../nexus-stack/docker-compose.yml` (env, ports, healthcheck), this repo's `Dockerfile` HEALTHCHECK, and `../nexus-dev-infra/prometheus.yml` (scrape target). Change one, change all.
- The `AgentCard` contents (name, skill id `weather_forecast`, description, `streaming=True`) are what the orchestrator's `weather_sub_agent` uses for routing/delegation. Keep the card truthful and keep `A2A_PUBLIC_URL` reachable from the orchestrator's network namespace (in Docker that is `http://a2a-agent:8001`, never `localhost`).
- The two-event streaming contract (one non-final `working` update, one `final=True` `completed` update) and the `metadata["structured_data"]` shape are asserted by tests and consumed upstream. Do not add or reorder events casually.
- `GET /health` comes from `nexus_common.bootstrap_starlette_service`; do not remove that call — Docker healthchecks and the orchestrator's system-status rely on the conventions it installs.
- Tests must never hit real networks; all HTTP is mocked with `respx`. Keep it that way.
- Do not bump `a2a-sdk` to 1.x without migrating imports (`a2a.server.apps.jsonrpc.starlette_app` does not exist there).
- Project convention: explain non-obvious design choices with `# EDUCATIONAL NOTE:` comments; this is a learning codebase and clarity beats cleverness.
