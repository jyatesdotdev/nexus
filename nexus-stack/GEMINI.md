# GEMINI.md - Multi-Agent & MCP Learning Lab

This document serves as the foundational context and instructional guide for the Multi-Agent & MCP Learning Lab. It outlines the project's architecture, development standards, and operational procedures.

## 🚀 Project Overview

The **Multi-Agent & MCP Learning Lab** is an educational repository for building modular, containerized, and agentic systems. It leverages the **Google Agent Development Kit (ADK)**, the **Model Context Protocol (MCP)**, and the **Agent-to-Agent (A2A) Protocol** to demonstrate a distributed microservices-based AI architecture.

### Key Technologies
- **Orchestration:** Google ADK, FastAPI, Python 3.14.
- **Sub-Agents:** FastMCP (MCP Server), A2A SDK (Weather Agent).
- **Frontend:** React 19, Vite, Tailwind CSS, Server-Sent Events (SSE).
- **Infrastructure:** Docker Compose, Makefile.
- **Foundational Models:** Gemini (default), with adapters for Bedrock and Ollama.

## 🏗️ Architecture & Components

The system is structured as a collection of specialized services in the `projects/` directory:

1.  **`orchestrator`**: The central hub. Runs a FastAPI server (`AdkWebServer`) that routes user requests to specialized sub-agents based on context.
2.  **`mcp_server`**: A standalone tool server using `FastMCP`. It exposes a local SQLite HR directory to the orchestrator via the Model Context Protocol.
3.  **`a2a_agent`**: A weather sub-agent that complies with the A2A Protocol. It uses an `AgentCard` for dynamic capability discovery over HTTP.
4.  **`frontend`**: A real-time React UI that parses SSE streams from the orchestrator to provide a smooth chat experience.
5.  **`e2e_tests`**: Integration tests verifying the communication between the orchestrator and sub-agents.

## 🛠️ Building and Running

The project uses a `Makefile` to simplify Docker-based operations.

| Task | Command | Description |
| :--- | :--- | :--- |
| **Build** | `make build` | Builds all Docker images for the stack. |
| **Start** | `make up` | Starts all services in the background. |
| **Stop** | `make down` | Stops and removes all containers. |
| **Test** | `make test` | Runs backend (Pytest) and frontend (Vitest) tests. |
| **CLI Chat** | `make chat` | Starts an interactive CLI chat session with the orchestrator. |
| **Logs** | `make logs` | Tails logs from all running containers. |
| **Clean** | `make clean` | Performs a deep cleanup of containers and images. |

### Environment Setup
Ensure a `.env` file exists in the root directory with your `GEMINI_API_KEY`:
```env
GEMINI_API_KEY=your_actual_key_here
```

## 📏 Development Conventions

### Python Standards
- **Type Hints:** Mandatory for all functions and classes to ensure maintainability and IDE support.
- **Docstrings:** **CRITICAL**. AI agents use docstrings to understand tool purpose and arguments. Always provide clear, descriptive docstrings for functions decorated with `@mcp.tool()` or passed to `Agent(tools=...)`.
- **Pydantic:** Used for data validation and defining structured output schemas for agents.
- **AsyncIO:** Use `async`/`await` for all network-bound operations (FastAPI, HTTPX, ADK runners).

### Agentic Patterns
- **Specialization:** Prefer creating a specialized `Agent` for specific domains (e.g., `sensor_agent`, `hr_agent`) rather than a single monolithic agent.
- **Delegation:** The `root_agent` in `projects/orchestrator/main.py` is the primary router. Use it to delegate tasks to sub-agents.
- **Tool Safety:** Never allow arbitrary code execution. Use allow-lists for system-level commands (see `projects/orchestrator/tools.py`).

### Frontend Standards
- **Real-time Streaming:** Use the SSE-based fetch loop in `App.tsx` for progressive text updates.
- **Styling:** Tailwind CSS is used for all styling. Follow the existing patterns in `App.tsx` and `App.css`.

### Testing
- **Backend:** Located in `projects/orchestrator` and `projects/e2e_tests`. Run via `pytest`.
- **Frontend:** Located in `projects/frontend/src`. Run via `vitest`.
- **LLM-as-a-judge:** Some tests utilize LLMs to evaluate the correctness of agent responses.

## 📁 Key Files to Watch
- `projects/orchestrator/main.py`: The entry point for orchestration logic and agent definitions.
- `projects/orchestrator/server.py`: The FastAPI server configuration.
- `projects/mcp_server/server.py`: The MCP tool definitions.
- `projects/a2a_agent/server.py`: The A2A sub-agent implementation.
- `projects/frontend/src/App.tsx`: The main UI component handling SSE streams.
