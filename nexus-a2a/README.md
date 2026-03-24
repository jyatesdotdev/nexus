# A2A Weather Sub-Agent

This project implements a standalone sub-agent that follows the **Agent-to-Agent (A2A) protocol**. It is designed to be discovered and utilized by a root orchestrator to provide specialized weather forecasting capabilities.

## 🌤️ What it Does
The A2A Weather Sub-Agent is a specialized microservice that:
1.  **Exposes an A2A-compliant interface**: It provides a standardized API for communication between AI agents.
2.  **Provides Weather Data**: It can extract a city name from natural language input and fetch real-time weather conditions using the [wttr.in](https://wttr.in) public API.
3.  **Streams Responses**: It uses asynchronous event queues to stream "thinking" messages and final results back to the caller.

## 📏 Engineering Standards

This project adheres strictly to **Educational Integrity** standards. This means:
- Code is heavily commented with **`EDUCATIONAL NOTE`** blocks explaining *why* decisions were made.
- We enforce strict **Code Quality** using Ruff, Mypy, and isolated virtual environments.
- **Testing Strategy** ensures complete isolation; we never touch external APIs during test runs, relying on `respx` for robust mocking.
- **Docker Deployment** follows best practices: using multi-stage builds, non-root users, strict `.dockerignore` files, and native healthchecks.

For complete details, please see the `GEMINI.md` file.

## 🏗️ Core Architecture (HOW & WHY)

### 1. `AgentExecutor` (WeatherAgentExecutor)
- **HOW**: We implement the `AgentExecutor` interface from the A2A SDK. This class contains the `execute` method where the actual task logic resides.
- **WHY**: The Executor defines the core intelligence of the sub-agent. By encapsulating logic here, we decouple the "what the agent does" (fetching weather) from the "how it communicates" (the A2A protocol). It allows the agent to asynchronously process requests and stream events back via the `EventQueue`.

### 2. `AgentCard`
- **HOW**: We define an `AgentCard` object that includes the agent's name, description, capabilities, and specific `AgentSkills` (like `weather_forecast`).
- **WHY**: This is the heart of the **A2A discovery protocol**. Instead of hardcoding routing logic in a central orchestrator, the orchestrator "reads" this card to understand what the sub-agent is capable of. This makes the system modular and allows for "plug-and-play" agent integration.

### 3. `A2AStarletteApplication`
- **HOW**: We use the `A2AStarletteApplication` builder to wrap our `AgentCard` and `DefaultRequestHandler` into a Starlette-compatible ASGI application.
- **WHY**: Compliance with the A2A standard requires specific JSON-RPC endpoints and schema validation. This utility handles the boilerplate of setting up the HTTP server, routing, and A2A-specific handshakes, allowing us to focus on the agent's unique logic.

## ⚙️ How it Works

1.  **Input Parsing**: When a request arrives, the `WeatherAgentExecutor` extracts the city name from the user's message. It looks for patterns like "in [City]" or uses the entire message if it's a simple query.
2.  **API Integration**: It makes an asynchronous HTTP request to `https://wttr.in/{city}?format=j1`. This provides a no-auth, JSON-based weather forecast.
3.  **Streaming Feedback**: Before the final answer, the agent sends a "thinking" message (e.g., "Fetching weather data for London...") to provide immediate feedback to the user via the orchestrator.
4.  **A2A Events**: The final result and the task completion status are enqueued as A2A-compliant events, ensuring the root orchestrator can track the lifecycle of the request.

## 🚀 Running the Agent

### Environment Variables
| Variable | Description | Default |
| :--- | :--- | :--- |
| `A2A_HOST` | The interface the server binds to. | `0.0.0.0` |
| `A2A_PORT` | The port the server listens on. | `8001` |
| `A2A_PUBLIC_URL` | The URL used for A2A discovery. | `http://a2a-agent:8001` |

### Using Docker (Recommended)
This agent is intended to be run as part of the project's `docker-compose.yml`:
```bash
# From the project root
docker compose up a2a-agent
```

### Manual Setup
If you want to run it locally without Docker:
1.  **Set up environment & Install Dependencies**:
    ```bash
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Code Quality & Testing**:
    ```bash
    ruff check .
    mypy server.py
    pytest
    ```
3.  **Start the Server**:
    ```bash
    python server.py
    ```
    The agent will be available at `http://localhost:8001`. You can view the discovery card at `http://localhost:8001/.well-known/agent-card.json`.

## 🩺 Health & Discovery
The agent provides a standard A2A discovery endpoint:
- **Discovery Card**: `GET /.well-known/agent-card.json`
- **JSON-RPC Endpoint**: `POST /rpc` (Handles A2A protocol methods like `execute`)
