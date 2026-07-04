# Nexus HR Directory (MCP)

The **Nexus HR Directory** is a specialized capability provider within an agentic architecture. It implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to expose a secure interface to a corporate HR database for LLM-based orchestrators.

## 🚀 Overview

This server allows LLMs (Large Language Models) to query employee information stored in a local or external database through well-defined tools and resources. It is built with a focus on security, type safety, and educational clarity.

- **Tools:**
  - `search_directory(department, name)`: Query the HR database for employee records including name, department, and email. Supports partial name matching.
  - `delete_user(email)`: Delete an employee record by email. This is a deliberately sensitive operation used to demonstrate identity propagation and authorization: the caller's identity is parsed from the `Authorization: Bearer` header (mock JWT via `nexus_common.IdentityContext`), and only the mock admin `mock_user_123` is permitted. The orchestrator's Human-in-the-Loop confirmation demo depends on this gate.
- **Resources:**
  - `system://status`: A static resource that confirms the server's operational status and database connectivity.

This server depends on the sibling repository [`../nexus-common`](../nexus-common) (installed editable via `requirements.txt`) for the `/health` endpoint, OpenTelemetry/Prometheus bootstrap, and mock identity parsing. A checkout of `nexus-common` next to this repo is required for installation and Docker builds.

## 🛠️ Key Technologies

- **Framework:** [FastMCP](https://modelcontextprotocol.io/) (Python SDK) - High-level framework for building MCP servers.
- **ORM:** [SQLModel](https://sqlmodel.tiangolo.com/) - Pydantic + SQLAlchemy for type-safe database interactions.
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/) - Robust database schema management.
- **Database:** SQLite (local `hr.db`) or External (via `DATABASE_URL`).
- **Code Quality:** [Ruff](https://beta.ruff.rs/docs/) (Linter & Formatter), [Mypy](https://mypy.readthedocs.io/) (Type Checking).
- **Testing:** [Pytest](https://docs.pytest.org/).
- **Containerization:** Optimized Multi-stage Docker.

## ⚙️ How It Works

1.  **Transport:** Uses **SSE (Server-Sent Events)** for asynchronous communication.
2.  **Database:** Upon startup, the server initializes the database. While `create_all` is used for rapid prototyping, production environments should rely on **Alembic** migrations.
3.  **Security:** 
    - ORM abstractions eliminate SQL injection risks.
    - Database credentials are externalized via environment variables.
    - Docker container runs as a non-root user.

## 🏃 Getting Started

### Using Docker (Recommended)

The normal way to build and run this service is through the full stack in
[`../nexus-stack/docker-compose.yml`](../nexus-stack) (service name `mcp-server`).

To build the image standalone, the build context must be the **workspace parent
directory** (not this repo), because the Dockerfile copies both `nexus-mcp/` and
the sibling `nexus-common/`:

1.  **Build the image (from the workspace parent):**
    ```bash
    cd .. && docker build -f nexus-mcp/Dockerfile -t nexus-hr-directory .
    ```
    (Running `docker build .` from inside this repo does not work.)
2.  **Run the container:**
    ```bash
    docker run -e DATABASE_URL="sqlite:///hr.db" -p 8000:8000 nexus-hr-directory
    ```

### Manual Execution

1.  **Set up environment** (requires the sibling `../nexus-common` checkout):
    ```bash
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt -r requirements-dev.txt
    ```
2.  **Apply migrations** (optional):
    ```bash
    alembic upgrade head
    ```
    The server also runs `SQLModel.metadata.create_all()` on startup, so a fresh
    database works without this step. If you have an existing database whose
    schema was created by the server rather than by Alembic, mark it as current
    instead of re-running the migration:
    ```bash
    alembic stamp head
    ```
3.  **Start the server:**
    ```bash
    python server.py
    ```

## 🧪 Development & Quality

### Linting & Formatting
We use **Ruff** for fast linting and formatting:
```bash
ruff format .
ruff check --fix .
```

### Type Checking
Ensure type safety with **Mypy**:
```bash
mypy .
```

### Running Tests
Execute the test suite using **Pytest**:
```bash
pytest
```

## 📂 Project Structure

- `server.py`: MCP tool/resource definitions and server entry point.
- `database.py`: SQLModel models and database configuration.
- `alembic/`: Database migration scripts.
- `tests/`: Automated test suite.
- `Dockerfile`: Optimized multi-stage container configuration (build context is the workspace parent).
- `AGENTS.md` (per directory): Foundational context and engineering standards for contributors and agents.


## 📏 Nexus Engineering Standards

This project adheres to the **Nexus Engineering Standards**, prioritizing educational clarity, production-grade quality, and architectural consistency. All contributors and sub-agents must follow these mandates:

### 1. Educational Integrity
- **Prefix:** Standardize all architectural and 'Why' commentary using the `# EDUCATIONAL NOTE:` (or language-appropriate) prefix.
- **Clarity:** Every non-trivial architectural choice must be accompanied by a note explaining the trade-offs and rationale.

### 2. Code Quality & Type Safety
- **Python:** Strict linting via `ruff` and static type checking via `mypy`.
- **UI/TypeScript:** Enforce `strict: true` in `tsconfig.json` and use ESLint for React/TypeScript best practices.
- **Automation:** Quality checks should be integrated into the `Makefile` or CI/CD pipelines.

### 3. Testing Isolation
- **No Side Effects:** Tests must be completely isolated. They must never hit external APIs (Gemini, Open-Meteo, etc.) or production resources.
- **Mocking:** Use robust mocking (e.g., `unittest.mock`, `pytest-mock`, `MSW`) to simulate all external dependencies and network boundaries.

### 4. Containerization & Production Readiness
- **Multi-stage Builds:** Dockerfiles must use multi-stage builds to keep production images lean.
- **Security:** Always run containers as a non-root user (`USER appuser`).
- **Healthchecks:** Every service must define a native `HEALTHCHECK` in its Dockerfile and/or `docker-compose.yml`.

### 5. Documentation
- **Living Reference:** the `AGENTS.md` files and `README.md` must be kept in sync with the project's actual state.
- **Architectural Diagrams:** Use Mermaid.js or clear text-based diagrams to visualize service interactions.
