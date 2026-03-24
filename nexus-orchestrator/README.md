# Orchestrator (Root Agent)

The Orchestrator is the central hub of the multi-agent system. It acts as the **Root Agent**, responsible for understanding user intent and delegating tasks to a fleet of specialized sub-agents, remote services, and local tools.

## Project Overview

This project demonstrates how to build a sophisticated agentic system using the Google ADK (Agent Development Kit). It showcases:
- **Hierarchical Orchestration**: A root agent that manages several specialized sub-agents.
- **Model Agnostic Adapters**: Custom adapters for running local models via Ollama and skeletal support for Amazon Bedrock.
- **Remote Agent Integration (A2A)**: Connecting to external agents using the Agent-to-Agent protocol.
- **Tool-based Extensions (MCP)**: Integrating with external toolsets via the Model Context Protocol (MCP).
- **Production-Ready Server**: A FastAPI-based web server with SSE (Server-Sent Events) for real-time streaming.

## How It Works

### 1. The Root Orchestrator (`main.py`)
The `root_agent` is the entry point for all user interactions. It is configured with instructions that define its role as a router. It doesn't perform tasks directly; instead, it identifies which sub-agent is best suited for the user's request based on their descriptions and capabilities.

**Sub-Agents managed by the Orchestrator:**
- **Local Specialized Agents**: `sensor_agent` (IoT), `metric_agent` (DevOps), `api_agent` (Finance), `parsing_agent` (Data Extraction), and `system_agent` (Bash commands).
- **MCP Agent**: A remote sub-agent that connects to a SQLite database via an MCP server using SSE transport.
- **A2A Agent**: A remote weather agent discovered dynamically via its `.well-known/agent-card.json`.

### 2. Model Adapters (`adapters/`)
The Orchestrator is not locked into Gemini. It uses the ADK's `BaseLlm` interface to support diverse models:
- **Ollama Adapter**: Connects to the local Ollama API, allowing you to run models like Llama 3 or Mistral for privacy and cost-efficiency. It handles the conversion between GenAI content types and Ollama's chat format.
- **Bedrock Adapter**: A skeletal implementation demonstrating how to integrate Amazon Bedrock (e.g., Claude 3) by implementing the `generate_content_async` interface.

### 3. Web Server (`server.py`)
The Orchestrator is exposed via a FastAPI application powered by `AdkWebServer`. This provides a standardized set of endpoints for session management, history retrieval, and streaming chat.

---

## Nexus Engineering Standards

This project adheres to the **Nexus Engineering Standards**, ensuring it serves as a high-quality educational reference and a production-ready service.

### 1. Educational Integrity
All architectural and "Why" commentary is standardized using the `# EDUCATIONAL NOTE:` prefix. This allows learners to quickly identify key design decisions and their rationales within the source code.

### 2. Code Quality & Type Safety
The project enforces strict linting and static type checking to minimize runtime errors and improve maintainability.
- **Linter**: [Ruff](https://github.com/astral-sh/ruff) is used for fast, comprehensive linting and formatting.
- **Type Checker**: [Mypy](https://github.com/python/mypy) is used with strict mode enabled to ensure 100% type coverage.

### 3. Complete Test Isolation
Tests are designed to be 100% isolated. No test should ever hit an external API or a production resource. We use `unittest.mock` extensively to patch network clients (`httpx`) and system calls (`subprocess`).

### 4. Optimized Containerization
The `Dockerfile` uses a multi-stage build to keep the runtime image minimal and secure. It runs as a non-root user and includes a native `HEALTHCHECK` to ensure the service is responsive.

---

## Key Logic (EDUCATIONAL NOTES)

### Tool Routing
- **EDUCATIONAL NOTE: [How]** The `root_agent` is initialized with a list of `sub_agents`. When a request comes in, the underlying LLM compares the request against the `description` and `instruction` of each sub-agent.
- **EDUCATIONAL NOTE: [Why]** This "router" pattern keeps individual agents small, focused, and efficient. It prevents "prompt bloat" in the root agent and ensures that specialized knowledge remains encapsulated within the sub-agents.

### AdkWebServer
- **EDUCATIONAL NOTE: [How]** The `AdkWebServer` class (from `google.adk.cli.adk_web_server`) wraps the `root_agent` and several persistence services (`InMemorySessionService`, `InMemoryMemoryService`, etc.).
- **EDUCATIONAL NOTE: [Why]** It abstracts away the boilerplate of building a chat API. It provides a standard interface that the frontend can rely on, regardless of the underlying agent's complexity.

### SSE Streaming
- **EDUCATIONAL NOTE: [How]** The `AdkWebServer` implements a chat endpoint that streams `LlmResponse` objects using Server-Sent Events. The `InMemoryRunner` also supports `run_async` which yields events.
- **EDUCATIONAL NOTE: [Why]** LLM responses can be slow. SSE allows the system to provide immediate, partial feedback to the user (streaming text) as it's generated, significantly improving the perceived responsiveness of the UI.

---

## Running the Orchestrator

### Prerequisites
- Python 3.10+
- A valid `GOOGLE_API_KEY` or `GEMINI_API_KEY` set in your environment.
- (Optional) Ollama running locally if using `ollama/` models.

### Installation
```bash
pip install -r requirements.txt
```

### CLI Mode (One-off Prompt)
```bash
python main.py "How's the weather in London and what's the system uptime?"
```

### Interactive CLI Mode
```bash
python main.py
```

### Server Mode (for Frontend Integration)
```bash
python server.py
```
The server will start on `http://0.0.0.0:8080` (configurable via `PORT` environment variable).

### Health Checks
You can check the real-time status of the Orchestrator and its distributed sub-agents by visiting:
`GET http://localhost:8080/system-status`

---

## Configuration (`config.py`)
- `AGENT_MODEL`: The LLM to use (default: `gemini-2.5-flash`). To use Ollama, set this to `ollama/llama3`.
- `MCP_SERVER_URL`: URL of the MCP server (default: `http://mcp-server:8000/sse`).
- `A2A_AGENT_URL`: URL of the A2A agent's card (default: `http://a2a-agent:8001/.well-known/agent-card.json`).
