# Changelog - Nexus Core

## [Refinement] - 2026-07-07
- **Dead code + doc accuracy:** removed two never-called private helpers (`_get_app_state_key`, `_get_user_state_key`) from `RedisSessionService`. Corrected AGENTS.md files: the SQLAlchemy dependency is explicitly pinned (not transitive via google-adk); the middleware session-wipe and positional-arg claims are fixed (both already resolved in code); the `load_agents_from_module` "auto-discovers new files" claim is false (the sole caller passes a module, not a package, so `walk_packages` never runs — new agents must be registered in `core_agents.py` or explicitly imported). Server docstring ADK version 1.28.0 → 2.3.0.

## [Bugfix] - 2026-07-04 (later)
- **Reviewer (revision-session isolation):** The REVISION path no longer re-runs the wrapped runner in the USER session — that persisted the synthetic "For context: this is an automated QA retry..." message as a user event in Redis/Postgres history, where later turns and history replays could see pipeline scaffolding (found via live Redis session forensics). The revision now runs through a fresh ADK `Runner` against a throwaway `InMemorySessionService` seeded from the user session via the `BaseSessionService` API (`create_session` + `append_event` on copied events — backend-agnostic), its events still stream to the client, and the ONLY write-back to the user session is one clean model event carrying the revised answer (`session_service.append_event`). Verified against installed google-adk 2.3.0.
- **Docs (active-agent handoff semantics):** New notes in `AGENTS.md` and `orchestrator/agents/AGENTS.md`: after a transfer, the transferred-to agent (not root) handles subsequent turns and may transfer directly to peers — ADK's `AutoFlow` default, gated by the `LlmAgent` fields `disallow_transfer_to_peers`/`disallow_transfer_to_parent` (both default `False`); strict hub-and-spoke = set `disallow_transfer_to_peers=True` per sub-agent. Routing config unchanged.
- **Testing:** Suite grows 44 → 45: `test_revision_scaffolding_never_persists_in_user_session` (user session gains no user-authored scaffolding event and gains exactly the revised answer); the REVISION test now asserts the revision runs through a separate Runner on an isolated in-memory session service.

## [Bugfix] - 2026-07-04
- **Reviewer (streaming-safe review-then-revise):** `ReviewerEnforcementRunner` no longer streams the reviewer's raw verdict as trailing content events — SSE clients (demo script, nexus-ui) treat the last non-partial content event as the authoritative answer, so every reply showed up as "REVISION: ..." instead of the real answer. The verdict now travels in a single content-less event's `custom_metadata` (`reviewer.REVIEW_METADATA_KEY`), and a REVISION verdict triggers exactly one revision cycle through the wrapped runner so the stream always ends with a real answer. The CLI (`app._print_chat_event`) prints the notice as a labeled `[reviewer ...]` line.
- **Reviewer (draft double-counting):** The draft buffered for review now sums only non-partial (authoritative) events. In SSE streaming mode ADK emits both partial deltas and a final aggregate event; summing all of them handed the reviewer the answer twice, so it rejected nearly every response as "repetitive".
- **Reviewer (session pollution):** The review step now runs in an isolated in-memory session (`review_{session_id}`, fresh `InMemorySessionService`/`InMemoryMemoryService`) instead of the user's persistent session. Previously each turn appended the `REVIEW REQUEST`/verdict exchange to Redis-backed history, contaminating later turns' reviews with earlier topics.
- **Reviewer (revision prompt shape):** The revision message leads with the original user request and puts the critique after the `"For context:"` marker that naive downstream parsers (nexus-a2a `extract_city`) are documented to strip, so re-delegated revisions don't feed prompt scaffolding to remote agents.
- **Testing:** Suite grows 41 → 44: `tests/test_reviewer_enforcement.py` rewritten for the new semantics (approved/revision paths, partial-event buffering, isolated review session, empty-verdict fail-open, single-revision-cycle guarantee).

## [Tooling] - 2026-07-04
- **uv workspace:** Runtime deps moved into `pyproject.toml` `[project]` (pins preserved) with dev tooling in `[dependency-groups]`; `nexus-common` is now a `{ workspace = true }` source. The per-service `venv/` is gone — `uv sync` at the workspace root creates the shared `.venv`, and `uv run pytest|ruff|mypy|python main.py …` replaces the venv-bin invocations. `requirements.txt` stays as a hand-kept mirror for the Dockerfile and CI (header comment documents the sync rule).
- **Lint:** Ruff `target-version` raised py310 → py314 (matching the 3.14 runtime everywhere); `requires-python = ">=3.14"` declared. No new findings.

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
