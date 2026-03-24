# GEMINI.md - A2A Weather Sub-Agent

This document provides instructional context and development standards for the **A2A Weather Sub-Agent**, a specialized microservice within the Multi-Agent & MCP Learning Lab.

## 🚀 Project Overview

The **A2A Weather Sub-Agent** is a standalone AI agent that complies with the **Agent-to-Agent (A2A) Protocol**. It provides real-time weather forecasting capabilities by extracting city names from natural language queries and fetching data from the [wttr.in](https://wttr.in) public API.

### Key Technologies
- **Language:** Python 3.14 (with `asyncio` and `httpx`).
- **Protocol:** A2A SDK (v0.3.25+), supporting dynamic capability discovery via `AgentCard`.
- **Server:** Starlette (via `A2AStarletteApplication`) and Uvicorn/Gunicorn.
- **Code Quality:** Ruff (Linter & Formatter), Mypy (Type Checking).
- **Testing:** Pytest and Respx.
- **Containerization:** Optimized Multi-stage Docker.
- **Integration:** Designed for discovery by a root orchestrator via JSON-RPC.

## 📏 Engineering Standards & Guidelines

These guidelines are strictly followed for all changes made to this project to ensure educational clarity, security, and production readiness.

### 1. Educational Integrity
- **Explanatory Comments:** Every architectural decision (e.g., why async, why a context manager) must be documented with inline "EDUCATIONAL NOTE" comments.
- **Clarity over Cleverness:** Code should be idiomatic and clean, prioritizing readability for someone learning the stack.

### 2. Code Quality & Formatting
- **Ruff:** Use `ruff format .` and `ruff check --fix .` for consistent styling and linting.
- **Typing:** Use Python 3.14 type hints comprehensively.
- **Environment:** Always use a virtual environment (`venv`) for local development to isolate dependencies.

### 3. Testing Strategy
- **Isolation:** Tests must NEVER touch external production APIs.
- **Mocking:** Use `respx` to mock external API requests (e.g., to `wttr.in`) during test runs.
- **Validation:** Every new feature or bug fix must be accompanied by relevant Pytest cases in the `tests/` directory.

### 4. Docker & Deployment
- **Multi-Stage Builds:** Use a `builder` stage for dependencies and a `final` stage for execution to minimize image size.
- **Security:** Always run as a non-root `appuser`.
- **Optimization:** Use `.dockerignore` to keep the build context small and prevent secrets/caches from leaking into images.
- **Healthchecks:** Include a native healthcheck (e.g., `curl` to the discovery card) to monitor server availability.

## 🏗️ Architecture

The agent is built around three core components:
1.  **`WeatherAgentExecutor`**: Contains the logic for parsing input, fetching weather data, and streaming A2A-compliant events (thinking messages and final results).
2.  **`AgentCard`**: Defines the agent's metadata (name, version, skills) for discovery.
3.  **`A2AStarletteApplication`**: Wraps the executor and card into an ASGI-compliant web server that handles A2A handshakes and RPC methods.

## 🛠️ Building and Running

### Docker (Recommended)
This agent is typically managed as part of the root project's `docker-compose.yml`.
```bash
# From the project root directory
make up          # Starts all services, including a2a-agent
make logs        # Tails logs from the container
```

### Manual Setup
To run the agent locally without Docker:
1.  **Install Dependencies**:
    ```bash
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Start the Server**:
    ```bash
    python server.py
    ```
    The agent will listen on `http://localhost:8001` by default.

### Environment Variables
| Variable | Description | Default |
| :--- | :--- | :--- |
| `A2A_HOST` | Interface to bind to. | `0.0.0.0` |
| `A2A_PORT` | Port to listen on. | `8001` |
| `A2A_PUBLIC_URL`| Discovery URL for the orchestrator. | `http://a2a-agent:8001` |

## 📁 Key Files
- `server.py`: The entry point containing the `WeatherAgentExecutor`, `AgentCard`, and Starlette app configuration.
- `requirements.txt`: Project dependencies.
- `Dockerfile`: Containerization configuration using `python:3.14-slim`.
