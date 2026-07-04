# Changelog - Nexus Core

## [Feature] - 2026-07-04
- **Observability (X-Trace-Id):** Every `POST /run_sse` response (including 401/404 rejections) now carries an `X-Trace-Id` header with the current OpenTelemetry trace id (32-char hex), attached in `middleware.py` before the SSE body starts streaming; `server.py` amends the ADK CORS middleware with `Access-Control-Expose-Headers: X-Trace-Id` so the cross-origin UI can read it. Falls back to a random well-formed id when no OTel provider is configured.
- **Governance (Reviewer on HTTP path):** New `GovernedAdkWebServer` (`server.py`) overrides ADK's private `AdkWebServer._create_runner` seam so HTTP `/run_sse` runners get the same `Runner → LoopDetectionRunner → ReviewerEnforcementRunner` pipeline as the CLI/evals path (previously UI traffic bypassed the reviewer). The pipeline is centralized in `reviewer.build_governed_runner` (with `LoopDetectionRunner` moved from `app.py` to `reviewer.py`) and toggleable via the new `REVIEWER_ENFORCEMENT` env var (default `true`).
- **A2A (Config-driven discovery):** `dynamic_agents.py` now fetches `{url}/.well-known/agent-card.json` for every entry in `A2A_AGENT_URLS` (entries may be base URLs or full card URLs) and registers one sub-agent per card, taking name/description from the card; unreachable endpoints are logged and skipped at startup instead of crashing. The default weather agent is therefore now registered as `weather_sub_agent` (sanitized from its card name "Weather Sub-Agent"); `eval_cases.py` updated to match. Cards without a usable name keep the legacy `weather_a2a_agent`/`a2a_agent_{i}` naming.
- **Testing:** Suite grows 25 → 41 tests: new `tests/test_a2a_discovery.py` (card naming, base-vs-card URLs, unreachable skip, default compat), `tests/test_reviewer_wiring.py` (pipeline on both paths, toggle, ADK seam pin), trace-header tests in `tests/test_server.py`, and a `tests/conftest.py` that stubs `httpx.get` so import-time discovery never touches the network.

## [Refinement] - 2026-07-03
- **Bugfix (Sessions):** `middleware.py` now calls `session_service.get_session` with the ADK keyword-only arguments and only creates a session when one does not exist; previously the positional call always raised, so every `/run_sse` request re-created the session and wiped chat history on the Redis backend.
- **Bugfix (Adapters):** `orchestrator/adapters/__init__.py` now imports the adapter modules so `LLMRegistry` registration runs at startup; `AGENT_MODEL=ollama/...` works in production again.
- **Bugfix (Tracing):** Fixed `get_propagated_headers` to import `TRACE_STORE` from `orchestrator.middleware` (was a swallowed ImportError from `orchestrator.app`, leaving the trace-propagation fallback dead).
- **Bugfix (Agents):** Attached the `get_sensor_reading` tool to `sensor_agent`, matching its instruction and the sensor eval case.
- **Testing:** Repaired `tests/test_reviewer_enforcement.py` mocks (async-generator side effects, patched reviewer `Runner`) — full suite passes again.
- **Docs:** Converted `GEMINI.md` into per-directory `AGENTS.md` files; refreshed `README.md` (root agent lives in `orchestrator/app.py`, tracing via Grafana Tempo, default model `gemini-2.5-flash`); removed the stray zero-byte `core` file.

## [Initial State] - 2026-03-21
- Resolved `GEMINI_API_KEY` missing error by loading `.env` correctly.
- Added command-line prompt support to `agent.py`.
- Fixed `google-adk` internal warning by patching and then properly using a logging filter.
- Upgraded `google-adk` to version 1.27.2.
- Created `TODO.md` and `CHANGELOG.md` to track project tasks.

## [Refactor] - 2026-03-21
- **Organization:** Moved mock tools to `tools.py` for better separation of concerns.
- **Refactoring:** Cleaned up `agent.py` with better structure and imports.
- **Documentation:** Added detailed "HOW" and "WHY" comments to clarify the purpose and implementation of non-obvious code sections.
- **Modernization:** Switched models to `gemini-2.5-flash` for better performance and feature support.

## [Testing] - 2026-03-21
- **Bugfix:** Updated all model references to `gemini-2.5-flash` to resolve 404 availability errors.

## [Refinement] - 2026-03-27
- **Persistence:** Integrated Redis and PostgreSQL support for long-term memory and session state.
- **Observability:** Added OpenTelemetry instrumentation for distributed tracing via Jaeger.
- **Orchestration:** Implemented the Critic/Reviewer pattern with a dedicated `reviewer_agent`.
- **Security:** Implemented Identity Propagation via mock JWT tokens across service boundaries.
- **Standards:** Enhanced educational notes and type safety across the orchestrator logic.

## [Project Structure] - 2026-03-21
- **Architecture:** Migrated to the modern Python **`src` layout** for better code/test isolation.
- **Structure:** Moved source code to `src/agent_app/` and tests to `tests/`.
- **Packaging:** Added `pyproject.toml` to define build system, dependencies, and test configurations.
- **Refinement:** Updated internal and test imports to support the new package structure.

## [Educational Enhancements] - 2026-03-21
- **Documentation:** Created a comprehensive `README.md` that explains the "Why" and "How" of the system's architecture.
- **Best Practices:** Added `src/agent_app/config.py` to demonstrate centralized configuration management.
- **Clarity:** Added Concept headers and pedagogical comments to all Python modules.
