# Changelog - Nexus Directory (MCP)

## [MCP Integration] - 2026-03-21
- **Protocol:** Integrated **Model Context Protocol (MCP)** support.
- **Server:** Created initial MCP server using `FastMCP` to provide a "Quote of the Day" tool (later evolved to HR Directory).
- **Discovery:** Configured for automatic discovery by the root orchestrator.
- **Connection:** Used `StdioConnectionParams` with custom `env` and `cwd` to ensure reliable communication.
