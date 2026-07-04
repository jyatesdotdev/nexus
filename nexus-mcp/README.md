# Nexus HR Directory (MCP)

The **Nexus HR Directory** is a specialized capability provider within an agentic architecture. It implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to expose a secure interface to a corporate HR database for LLM-based orchestrators.

## 🚀 Overview

This server allows LLMs (Large Language Models) to query employee information stored in a local or external database through well-defined tools and resources. It is built with a focus on security, type safety, and educational clarity.

- **Tools:**
  - `search_directory(department, name)`: Query the HR database for employee records including name, department, and email. Supports partial name matching.
- **Resources:**
  - `system://status`: A static resource that confirms the server's operational status and database connectivity.

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

1.  **Build the image:**
    ```bash
    docker build -t nexus-hr-directory .
    ```
2.  **Run the container:**
    ```bash
    docker run -e DATABASE_URL="sqlite:///hr.db" -p 8000:8000 nexus-hr-directory
    ```

### Manual Execution

1.  **Set up environment:**
    ```bash
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Apply migrations:**
    ```bash
    alembic upgrade head
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
- `Dockerfile`: Optimized multi-stage container configuration.
- `GEMINI.md`: Foundational context and engineering standards.


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
- **Living Reference:** `GEMINI.md` and `README.md` must be kept in sync with the project's actual state.
- **Architectural Diagrams:** Use Mermaid.js or clear text-based diagrams to visualize service interactions.
