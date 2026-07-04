# tests/ — unit test suite

Pytest suite for the Nexus orchestrator (the ADK root agent in `../orchestrator/`). Hard rule for this suite: 100% isolation — no test may hit a real LLM API, Ollama, Redis, Postgres, Prometheus, or any network endpoint. Everything external is mocked with `unittest.mock` (`patch`, `AsyncMock`, `MagicMock`). LLM behavior quality is NOT tested here; that is done separately by the evals command (`./venv/bin/python main.py evals`, which does hit the real model).

Configuration comes from `../pytest.ini`: `asyncio_mode = strict`, so every async test function must be decorated with `@pytest.mark.asyncio` or it will be skipped/error. Several files prepend the repo root to `sys.path` manually (`sys.path.append(os.path.join(os.path.dirname(__file__), ".."))`) because the project is not installed as a package — run pytest from the repo root so imports resolve.

Import-time gotcha: `orchestrator/app.py` builds the root agent and persistence services at import time from environment variables, and A2A discovery fetches each agent card over HTTP during that build. `conftest.py` therefore performs the suite's FIRST `import orchestrator.app` with `httpx.get` patched to return the production weather card (helper `make_card_response` is importable from conftest). Tests that need different env (e.g. multiple MCP/A2A URLs) must `patch.dict(os.environ, ...)`, patch `httpx.get`, and then `importlib.reload` `orchestrator.config`, `orchestrator.agents.dynamic_agents`, and `orchestrator.app` — see `test_initialization.py` for the pattern (including reloading back to defaults in a `finally`). `AgentRegistry` is process-global; `initialize_agents()` calls `AgentRegistry.clear()` to keep runs isolated.

## Files

- `conftest.py` — sys.path setup, the mocked-card first import of `orchestrator.app` described above, and the shared `make_card_response(card)` helper.
- `test_orchestrator.py` — Imports the real `root_agent` and runs it through ADK's `InMemoryRunner` with the model's `generate_content_async` mocked, verifying delegation/response plumbing end to end without network.
- `test_initialization.py` — Asserts dynamic agent registration fallback naming: with multiple `MCP_SERVER_URLS`/`A2A_AGENT_URLS` set and mocked agent cards that carry NO name, agents are named `mcp_agent_0`, `mcp_agent_1`, `a2a_agent_0`, ... Uses the env-patch + httpx-patch + reload pattern described above.
- `test_a2a_discovery.py` — Config-driven A2A discovery: card-derived agent names/descriptions (`Weather Sub-Agent` → `weather_sub_agent`), base-URL vs full-card-URL normalization to `/.well-known/agent-card.json`, unreachable endpoints logged + skipped without crashing, single-URL legacy fallback name, and default-config backward compatibility. All `httpx.get` calls mocked.
- `test_reviewer_wiring.py` — Proves the governance pipeline is wired into BOTH execution paths: `reviewer.build_governed_runner` composition, `server.GovernedAdkWebServer._create_runner` wrapping (with the ADK superclass method patched), the `REVIEWER_ENFORCEMENT` toggle (via `patch.object(config, ...)`), and a seam-pin test asserting `AdkWebServer._create_runner`/`_get_root_agent` still exist in the installed ADK.
- `test_server.py` — Builds the FastAPI app via `create_app_instance` and uses `fastapi.testclient.TestClient` (with `raise_server_exceptions=False`). Covers `/health`, `/system-status` (with `httpx` get/head patched), the 404 path for unknown agent names, asserts `APP_NAME` is a valid Python identifier (ADK requirement), and the `X-Trace-Id` contract: header present and 32-hex on `/run_sse` responses (404 and 401 paths), CORS-exposed via `Access-Control-Expose-Headers`, and `get_current_trace_id()` unit tests with a mocked OTel span (valid id passthrough + random fallback when the span is INVALID).
- `test_tools.py` — Direct unit tests of `orchestrator/tools.py`: mock sensor/YNAB/entity outputs, `query_prometheus_metric` with patched httpx, and `execute_safe_bash_command` allow-list enforcement (allowed commands run via patched `subprocess.run`; anything else returns `status="error"` without executing).
- `test_reviewer_enforcement.py` — Tests `ReviewerEnforcementRunner` (approved and revision paths). The wrapped runner's `run_async` is a `MagicMock` whose side_effect returns a real async generator (it is iterated, not awaited), and `orchestrator.reviewer.Runner` is patched because the production code builds a fresh ADK Runner for the review step — letting a real Runner run against MagicMock services raises `TypeError: 'MagicMock' object can't be awaited` (the pre-2026-07-03 failure mode).
- `test_ollama_adapter.py` — Tests `OllamaAdapter` non-streaming and streaming paths with `httpx.AsyncClient` mocked (streaming mocks `aiter_lines` yielding line-delimited JSON). In production the adapter is registered with ADK's `LLMRegistry` via `orchestrator/adapters/__init__.py` (see `../orchestrator/adapters/AGENTS.md`).
- `test_redis_services.py` — Tests `RedisSessionService`/`RedisMemoryService` against an `AsyncMock` Redis client: key formats, session round-trip, memory add/search word matching.
- `test_postgres_services.py` — Tests `PostgresMemoryService` with mocked SQLAlchemy engine/session factory and a mocked GenAI embeddings client (autouse fixture returns 768-dim dummy vectors, matching the `Vector(768)` column).
- `test_database_session_service.py` — Tests `DatabaseSessionService` (create/get/append_event) with mocked engine and session factory; verifies events persist as JSON and partial events are skipped.

## How to run

```bash
cd /Users/jyates/Repositories/nexus/nexus-orchestrator
./venv/bin/python -m pytest tests/                       # whole suite
./venv/bin/python -m pytest tests/test_tools.py -v       # one file
./venv/bin/python -m pytest tests/ -k "redis"            # by keyword
```

No `.env`, API key, or running services are required. Expected state as of 2026-07-04: all 41 tests pass.

## Caution

- Never add a test that performs real network or subprocess side effects; patch `httpx`, `subprocess.run`, Redis, and SQLAlchemy as the existing tests do.
- Keep mocked data consistent with the real mock tool outputs in `orchestrator/tools.py` and the naming scheme in `orchestrator/agents/dynamic_agents.py` — several assertions are string-exact.
