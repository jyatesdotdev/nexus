# GEMINI.md - A2A Weather Sub-Agent

This document provides instructional context and development standards for the **A2A Weather Sub-Agent**, a specialized microservice within the Multi-Agent & MCP Learning Lab.

## 🚀 Project Overview

The **A2A Weather Sub-Agent** is a standalone AI agent that complies with the **Agent-to-Agent (A2A) Protocol**. It provides real-time weather forecasting capabilities by extracting city names from natural language queries and fetching data from the [wttr.in](https://wttr.in) public API.

### Key Technologies
- **Language:** Python 3.14 (with `asyncio` and `httpx`).
- **Protocol:** A2A SDK (v0.3.25+), supporting dynamic capability discovery via `AgentCard`.
- **Server:** Starlette (via `A2AStarletteApplication`) and Uvicorn/Gunicorn.
- **Integration:** Designed for discovery by a root orchestrator via JSON-RPC.

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

## 📏 Development Conventions

### A2A Protocol Compliance
- **Streaming:** The agent MUST stream its progress. Use `event_queue.enqueue_event()` to send intermediate "thinking" messages and final results.
- **Task Lifecycle:** Always signal completion by enqueuing a `TaskStatusUpdateEvent` with `state=TaskState.completed`.
- **Discovery:** Ensure the `AgentCard` in `server.py` is updated when new skills or capabilities are added.

### Python Standards
- **AsyncIO:** Use `async`/`await` for all I/O operations (HTTP requests, event enqueuing).
- **Type Hints:** Mandatory for all functions and classes to ensure maintainability.
- **Docstrings:** **CRITICAL**. AI agents use docstrings to understand tool purpose and arguments. Provide clear, descriptive docstrings for all public methods.
- **Error Handling:** Gracefully handle API failures (e.g., `wttr.in` timeouts) by returning informative error messages rather than crashing.

## 📁 Key Files
- `server.py`: The entry point containing the `WeatherAgentExecutor`, `AgentCard`, and Starlette app configuration.
- `requirements.txt`: Project dependencies.
- `Dockerfile`: Containerization configuration using `python:3.14-slim`.
