# Changelog - Nexus Directory (MCP)

## [Fixes & Hardening] - 2026-07-03
- **Migrations:** Rewrote the initial Alembic revision (`668e2bd0edd6`) as a true baseline that creates the `users` table, so `alembic upgrade head` now works on a fresh database; enabled `render_as_batch=True` in `alembic/env.py` for SQLite compatibility. Existing databases created by the server's `create_all()` should be marked current with `alembic stamp head`.
- **Typing:** `search_directory` optional parameters are now `str | None`; added return annotations and `sqlmodel.col()` usage; the repo now passes `mypy --strict` (mypy added to `requirements-dev.txt`).
- **Tests:** Added coverage for `delete_user` (admin allowed, non-admin denied, missing auth header, not-found) using a mocked MCP context; suite is now 11 tests.
- **Documentation:** README now documents the `delete_user` tool and the `../nexus-common` dependency, and its Docker build instructions use the required workspace-parent build context; replaced references to the removed `GEMINI.md` with the per-directory `AGENTS.md` files.

## [Advanced Features] - 2026-03-27
- **Tools:** Added `delete_user` tool to demonstrate sensitive operations.
- **Orchestration:** Integrated with the Orchestrator's Human-in-the-Loop (HITL) pattern via `require_confirmation`.
- **Security:** Supported identity propagation for scoped operations.

## [Nexus Branding Update] - 2026-03-24
- **Documentation:** Extensively updated **README.md** with project branding, architectural details, and key technologies.
- **Project Structure:** Standardized project name as **Nexus HR Directory (MCP)**.
- **Migrations:** Explicitly added guidance for using **Alembic** migrations.
- **Quality:** Integrated development and quality instructions for **Ruff**, **Mypy**, and **Pytest**.

## [MCP Integration] - 2026-03-21
- **Protocol:** Integrated **Model Context Protocol (MCP)** support.
- **Server:** Created initial MCP server using `FastMCP` to provide a "Quote of the Day" tool (later evolved to HR Directory).
- **Discovery:** Configured for automatic discovery by the root orchestrator.
- **Connection:** Used `StdioConnectionParams` with custom `env` and `cwd` to ensure reliable communication.
