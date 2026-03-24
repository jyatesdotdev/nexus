# Changelog - Nexus Core

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

## [Project Structure] - 2026-03-21
- **Architecture:** Migrated to the modern Python **`src` layout** for better code/test isolation.
- **Structure:** Moved source code to `src/agent_app/` and tests to `tests/`.
- **Packaging:** Added `pyproject.toml` to define build system, dependencies, and test configurations.
- **Refinement:** Updated internal and test imports to support the new package structure.

## [Educational Enhancements] - 2026-03-21
- **Documentation:** Created a comprehensive `README.md` that explains the "Why" and "How" of the system's architecture.
- **Best Practices:** Added `src/agent_app/config.py` to demonstrate centralized configuration management.
- **Clarity:** Added Concept headers and pedagogical comments to all Python modules.
