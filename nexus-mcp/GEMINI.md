# GEMINI.md - MCP HR Directory Server

This document provides foundational context and instructional guidance for the MCP HR Directory Server project.

## 🚀 Project Overview

The **MCP HR Directory Server** is a specialized capability provider within an agentic architecture. It implements the **Model Context Protocol (MCP)** to expose a secure interface to a corporate HR database for LLM-based orchestrators.

### Key Technologies
- **Framework:** [FastMCP](https://modelcontextprotocol.io/) (Python SDK).
- **Runtime:** Python 3.14.
- **ORM:** [SQLModel](https://sqlmodel.tiangolo.com/) (Pydantic + SQLAlchemy).
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/).
- **Database:** SQLite (local `hr.db`) or External (via `DATABASE_URL`).
- **Code Quality:** Ruff (Linter & Formatter), Mypy (Type Checking).
- **Testing:** Pytest.
- **Containerization:** Optimized Multi-stage Docker.

## 📏 Engineering Standards & Guidelines

These guidelines are strictly followed for all changes made to this project to ensure educational clarity, security, and production readiness.

### 1. Educational Integrity
- **Explanatory Comments:** Every architectural decision (e.g., why SQLModel, why Alembic) must be documented with inline "EDUCATIONAL NOTE" comments.
- **Clarity over Cleverness:** Code should be idiomatic and clean, prioritizing readability for someone learning the stack.

### 2. Database & Persistence
- **ORM-First:** Use **SQLModel** for all database interactions. Raw SQL should be avoided to ensure type safety and Pydantic integration.
- **Migrations:** Never use `create_all` for production schema changes. Always generate and apply **Alembic** migrations.
- **Externalization:** Support external databases by using the `DATABASE_URL` environment variable.
- **Security:** Use ORM abstractions or parameterized queries to prevent SQL Injection.

### 3. Code Quality & Formatting
- **Ruff:** Use `ruff format .` and `ruff check --fix .` for consistent styling and linting.
- **Typing:** Use Python 3.14 type hints comprehensively.
- **Environment:** Always use a virtual environment (`venv`) for local development to isolate dependencies.

### 4. Testing Strategy
- **Isolation:** Tests must NEVER touch the local `hr.db` or external production databases.
- **Mocking:** Use `unittest.mock` or environment injection to redirect database engines to an in-memory or temporary SQLite database during test runs.
- **Validation:** Every new feature or bug fix must be accompanied by relevant Pytest cases in the `tests/` directory.

### 5. Docker & Deployment
- **Multi-Stage Builds:** Use a `builder` stage for dependencies and a `final` stage for execution to minimize image size.
- **Security:** Always run as a non-root `appuser`.
- **Optimization:** Use `.dockerignore` to keep the build context small and prevent secrets/caches from leaking into images.
- **Healthchecks:** Include a native healthcheck (e.g., Python socket check) to monitor server availability.

## 🏗️ Architecture & Components

### Tools
- **`search_directory(department: str = None, name: str = None)`**: 
  - **Purpose:** Queries the HR database using SQLModel for employee records.
  - **Logic:** Supports dynamic filtering and partial name matching via `.contains()`.

### Resources
- **`system://status`**: 
  - **Purpose:** A static resource providing the server's operational health.

## 🛠️ Building and Running

### Using Docker (Recommended)
1. **Build the image:**
   ```bash
   docker build -t mcp-hr-server .
   ```
2. **Run the container:**
   ```bash
   docker run -e DATABASE_URL="sqlite:///hr.db" -p 8000:8000 mcp-hr-server
   ```

### Manual Execution
1. **Set up environment:**
   ```bash
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Apply migrations:**
   ```bash
   alembic upgrade head
   ```
3. **Start the server:**
   ```bash
   python server.py
   ```

## 📁 Key Files
- `server.py`: MCP tool/resource definitions and server entry point.
- `database.py`: SQLModel models, engine configuration, and initialization logic.
- `alembic/`: Database migration scripts.
- `tests/`: Automated test suite.
- `Dockerfile`: Optimized multi-stage container configuration.
- `requirements.txt`: Project dependencies.
