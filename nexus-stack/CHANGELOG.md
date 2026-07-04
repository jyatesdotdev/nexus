# Changelog

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
