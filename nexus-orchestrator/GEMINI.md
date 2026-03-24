# GEMINI.md - Orchestrator (Root Agent)

This document provides foundational context and instructional guidance for the Orchestrator project, which serves as the central hub for a multi-agent system built with the Google Agent Development Kit (ADK).

## 🚀 Project Overview

The **Orchestrator** is a sophisticated agentic system designed to understand user intent and delegate tasks to specialized sub-agents, remote services, and local tools. It acts as a **Root Agent** in a hierarchical orchestration pattern.

### Key Technologies
- **Orchestration:** Google ADK, Python 3.10+.
- **Web Framework:** FastAPI, Uvicorn, Gunicorn.
- **Communication:** Server-Sent Events (SSE) for real-time streaming, Agent-to-Agent (A2A) Protocol, Model Context Protocol (MCP).
- **Models:** Gemini (default), Ollama (local models), skeletal support for Amazon Bedrock.
- **Data Validation:** Pydantic.

### Hierarchical Architecture
- **`root_agent` (`orchestrator/app.py`)**: The primary router that identifies the best-suited sub-agent for a given request.
- **Specialized Sub-Agents**:
    - `sensor_agent`: IoT/Physical sensor queries.
    - `metric_agent`: DevOps/Prometheus system metrics.
    - `api_agent`: Financial/YNAB budget data.
    - `parsing_agent`: Entity extraction from text.
    - `system_agent`: Safe bash command execution.
    - `mcp_agent`: Remote HR directory queries via MCP.
    - `weather_a2a_agent`: Dynamic weather forecasts via A2A.

## 🛠️ Building and Running

### Environment Setup
Ensure a `.env` file exists with your `GEMINI_API_KEY` or `GOOGLE_API_KEY`:
```env
GEMINI_API_KEY=your_key_here
# Optional: Set AGENT_MODEL to ollama/llama3 for local execution
AGENT_MODEL=gemini-2.5-flash
```

### Key Commands

| Task | Command | Description |
| :--- | :--- | :--- |
| **Install** | `python3 -m venv venv && ./venv/bin/pip install -r requirements.txt` | Creates a venv and installs all Python dependencies. |
| **CLI Mode** | `./venv/bin/python main.py chat "Your prompt"` | Runs a single prompt through the orchestrator. |
| **Interactive CLI** | `./venv/bin/python main.py chat` | Starts an interactive chat session in the terminal. |
| **Server Mode** | `./venv/bin/python main.py serve` | Starts the FastAPI server on `http://0.0.0.0:8080`. |
| **Test** | `./venv/bin/pytest tests/` | Runs the test suite using the virtual environment. |
| **Status Check** | `curl http://localhost:8080/system-status` | Returns the health of the orchestrator and sub-agents. |

## 📏 Development Conventions

### Nexus Engineering Standards
This project follows the **Nexus Engineering Standards**:
- **Educational Integrity**: All architectural commentary must use the `# EDUCATIONAL NOTE:` prefix.
- **Code Quality**: Enforce strict linting with Ruff and type safety with Mypy.
- **Test Isolation**: Ensure all tests use mocking to avoid external API hits.
- **Containerization**: Use multi-stage builds, non-root users, and native healthchecks.

### Agentic & Architectural Patterns
- **Hierarchical Delegation:** The `root_agent` should remain a lightweight router. Logic for specific domains must be encapsulated in sub-agents.
- **Adapter Pattern (`adapters/`)**: New foundation models must implement the `BaseLlm` interface and register themselves via `LLMRegistry`.
- **Tool Implementation (`tools.py`)**:
    - **Docstrings are Mandatory**: Agents use docstrings to understand tool purpose and arguments.
    - **Security First**: System-level tools (like bash execution) must use strict allow-lists.
- **Structured Outputs**: Use Pydantic models (like `OrchestratorResponse`) to define schemas for agent responses to ensure reliable parsing by frontends.

### Python Standards
- **AsyncIO:** All network-bound operations (FastAPI, ADK runners, LLM requests) must use `async`/`await`.
- **Type Hints:** Mandatory for all functions and classes to ensure maintainability and IDE support.
- **Logging:** Use the standard `logging` library. Silence noisy third-party loggers in `orchestrator_app.py` if necessary.

### Configuration (`config.py`)
- Centralize all environment variable access and validation in `config.py`.
- Use defaults for local development but allow overrides via environment variables for containerization.
