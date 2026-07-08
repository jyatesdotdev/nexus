# Changelog

## [Refinement] - 2026-07-07
- **`make type-check` covers nexus-common:** the `lint` target ran ruff over all four Python projects but `type-check` ran mypy over only three, silently omitting nexus-common (which passes strict mypy and ships `py.typed`). Added it for symmetry.
- **Docs accuracy (AGENTS.md):** the `clean` description still claimed a machine-wide `docker system prune` (removed 2026-07-05); rewritten to the scoped reality. Documented the overridable `ORCHESTRATOR_HOST_PORT` / `FRONTEND_HOST_PORT` on the service entries and the "after make up" URLs.

## [Standards] - 2026-07-05
- **Semgrep educational-note rule actually enforces now:** the old zero-width `\A` + `pattern-not-regex` construction silently matched nothing on older engines and mis-fired on newer ones (only honoring notes on line 1). Rewritten as a version-stable whole-file DOTALL lookahead; co-located UI test files excluded to match the python `tests/` exemption; include patterns unanchored per Semgrepignore v2. The working rule surfaced 19 files that had never received a note — all now documented.

## [Housekeeping] - 2026-07-05
- **Scoped `make clean` + gated `make clean-all`:** `clean` no longer runs machine-wide `docker system prune` (which deleted other projects' stopped containers). It now removes only the Nexus compose-built images plus always-safe dangling-image/build-cache garbage, never volumes. New `clean-all` deletes the Nexus data volumes too but refuses to run without `FORCE=1`.

## [Scaffolding] - 2026-07-04
- **Generator:** Added `make new-agent NAME=<name> [PORT=<port>]` (`scripts/new-agent.sh`) — scaffolds a complete A2A sub-agent service at `../nexus-<name>` from the new `templates/a2a-service/` tree (modeled on nexus-a2a: AgentExecutor with two-phase streaming, AgentCard discovery, `/health` + telemetry via nexus-common, respx-mocked tests that pass out of the box, multi-stage non-root Dockerfile, AGENTS/README/CHANGELOG docs). PORT defaults to the first free port ≥ 8002; refuses to overwrite an existing directory.
- **Checklist over auto-wiring:** The generator prints the remaining integration steps (compose snippet with healthcheck on `nexus-net`, orchestrator `A2A_AGENT_URLS` entry — one dynamically discovered sub-agent per agent card, named from the card — Prometheus scrape target, uv workspace member) instead of editing shared files itself.
- **Standards:** Template `.py`/Dockerfile files comply with the Semgrep educational-note rule (they are scanned as part of `nexus-stack/**`); template `tests/` are covered by the existing `**/tests/**` exclusion.

## [Tooling] - 2026-07-04
- **Makefile:** `test`, `lint`, and `type-check` now run the Python services through the uv workspace at the repo root (one `uv sync`, then `uv run --no-sync` per service) instead of reusing `../nexus-orchestrator/venv`, which no longer exists. `lint` checks all four Python projects (nexus-common included) in one ruff invocation.
- **Preflight:** `make doctor` additionally checks that `uv` is installed (required by the targets above).

## [Onboarding & Demo Tooling] - 2026-07-04
- **Onboarding:** Added `.env.example` documenting every environment variable the stack consumes (placeholders only), including optional `A2A_AGENT_URLS` / `REVIEWER_ENFORCEMENT` overrides and a note on UI build-time `VITE_*` variables.
- **Preflight:** Added `make doctor` (`scripts/doctor.sh`) — checks Docker CLI/daemon, `.env` + non-placeholder `GEMINI_API_KEY` (presence only, value never printed), the external `nexus-net` network, and Node/npm; reports all problems with fixes and exits nonzero.
- **Demo:** Added `make demo` (`scripts/demo.sh`) — guided scripted conversation against `/run_sse` exercising MCP delegation (HR directory), A2A delegation (weather), and a local sensor tool; prints each response and its `X-Trace-Id` with a Grafana Tempo deep link. Requires a running stack (`make up`).
- **Persistence:** Documented that the orchestrator defaults to `PERSISTENCE_BACKEND=redis` in `docker-compose.yml` (`${PERSISTENCE_BACKEND:-redis}`), so session history survives orchestrator restarts out of the box.
- **Testing:** `make test` now runs the integration suite via directory discovery (`pytest /e2e_tests`) instead of an explicit file list, so new `nexus-integration/test_*.py` files are picked up automatically.
- **Docs:** README quickstart rewritten around `cp .env.example .env` → `make doctor` → `make up` → `make demo`.

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
- **Strategy:** Researched and implemented "LLM-as-a-judge" for testing agentic workflows.
- **Implementation:** Created `test_agent_judge.py` with automated `pytest` cases that use Gemini to evaluate agent quality.
- **Bugfix:** Updated all model references to `gemini-2.5-flash` to resolve 404 availability errors.
- **Validation:** Verified all agents (sensor, metric, api) pass high-quality evaluation rubrics.

## [Project Structure] - 2026-03-21
- **Architecture:** Migrated to the modern Python **`src` layout** for better code/test isolation.
- **Structure:** Moved source code to `src/agent_app/` and tests to `tests/`.
- **Packaging:** Added `pyproject.toml` to define build system, dependencies, and test configurations.
- **Refinement:** Updated internal and test imports to support the new package structure.

## [MCP Integration] - 2026-03-21
- **Protocol:** Integrated **Model Context Protocol (MCP)** support.
- **Server:** Created `src/agent_app/mcp_server.py` using `FastMCP` to provide a "Quote of the Day" tool.
- **Discovery:** Configured the agent to automatically discover and use tools from the MCP server using `McpToolset`.
- **Connection:** Used `StdioConnectionParams` with custom `env` and `cwd` to ensure reliable communication with the local MCP subprocess.

## [Educational Enhancements] - 2026-03-21
- **Documentation:** Created a comprehensive `README.md` that explains the "Why" and "How" of the system's architecture.
- **Best Practices:** Added `src/agent_app/config.py` to demonstrate centralized configuration management.
- **Clarity:** Added Concept headers and pedagogical comments to all Python modules.

## [A2A Capability] - 2026-03-21
- **Protocol:** Integrated **Agent-to-Agent (A2A)** capabilities.
- **Server:** Created `src/agent_app/a2a_server.py` using the `a2a-sdk` to expose a weather forecasting service.
- **Client Template:** Added `src/agent_app/a2a_client.py` to demonstrate how to build a pure A2A client that performs handshakes and message exchange directly.
- **Integration:** Added `RemoteA2aAgent` to the root orchestrator, enabling seamless cross-service delegation.
- **Testing:** Implemented `tests/test_a2a_integration.py` to verify the multi-agent handshake and message exchange.
