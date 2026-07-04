# Changelog - Nexus Directory (MCP)

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
