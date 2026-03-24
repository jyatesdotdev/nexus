# GEMINI.md - MCP HR Directory Server

This document provides foundational context and instructional guidance for the MCP HR Directory Server project.

## 🚀 Project Overview

The **MCP HR Directory Server** is a specialized capability provider within an agentic architecture. It implements the **Model Context Protocol (MCP)** to expose a secure interface to a corporate HR database (SQLite) for LLM-based orchestrators.

### Key Technologies
- **Framework:** [FastMCP](https://modelcontextprotocol.io/) (Python SDK).
- **Runtime:** Python 3.14.
- **Database:** SQLite (local `hr.db`).
- **Transport:** SSE (Server-Sent Events) via Starlette/Uvicorn.
- **Containerization:** Docker (running as a non-root `appuser`).

## 🏗️ Architecture & Components

The server acts as a **Capability Provider**, offering specific "skills" (tools) and "knowledge" (resources) to an agent or orchestrator.

### Tools
- **`search_directory(department: str = None, name: str = None)`**: 
  - **Purpose:** Queries the HR database for employee records.
  - **Logic:** Supports filtering by department or partial name match.
  - **Security:** Uses parameterized queries to prevent SQL injection.

### Resources
- **`system://status`**: 
  - **Purpose:** A static resource providing the server's operational health and database connection status.

## 🛠️ Building and Running

### Using Docker (Recommended)
1. **Build the image:**
   ```bash
   docker build -t mcp-hr-server .
   ```
2. **Run the container:**
   ```bash
   docker run -p 8000:8000 mcp-hr-server
   ```
   The server listens on `http://0.0.0.0:8000`.

### Manual Execution
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Start the server:**
   ```bash
   python server.py
   ```

## 📏 Development Conventions

### MCP Implementation
- **Tool Definitions:** Use the `@mcp.tool()` decorator. Ensure docstrings are descriptive and include type hints, as they are used by LLMs to understand the tool's purpose and arguments.
- **Resource Definitions:** Use the `@mcp.resource(uri)` decorator for static or semi-static data.
- **Transport:** Defaults to `sse` for web-compatible asynchronous communication.

### Database Patterns
- **Connection Management:** Use the `get_db()` context manager (defined in `server.py`) to ensure connections are properly closed.
- **Initialization:** The `init_db()` function handles schema creation and mock data population on startup if `hr.db` does not exist.
- **Security:** Always use parameterized queries (`?` placeholders) for SQL execution.

### Docker Standards
- **Security:** The `Dockerfile` creates a non-root `appuser` and changes ownership of the `/app` directory before execution.
- **Base Image:** Uses `python:3.14-slim` for a minimal footprint.

## 📁 Key Files
- `server.py`: The main entry point containing MCP tool/resource definitions and database logic.
- `hr.db`: The SQLite database file (created dynamically if missing).
- `requirements.txt`: Project dependencies (`mcp[sse]`, `uvicorn`, `starlette`).
- `Dockerfile`: Containerization configuration.
