# Orchestrator (Root Agent)

The Orchestrator is the central hub of the multi-agent system. It acts as the **Root Agent**, responsible for understanding user intent and delegating tasks to a fleet of specialized sub-agents, remote services, and local tools.

## Project Overview

This project demonstrates how to build a sophisticated agentic system using the Google ADK (Agent Development Kit). It showcases:
- **Hierarchical Orchestration**: A root agent that manages several specialized sub-agents.
- **Advanced Patterns**: Implements the **Critic/Reviewer** pattern for output quality and **Human-in-the-Loop (HITL)** for sensitive operations.
- **Distributed Observability**: OpenTelemetry integration for end-to-end tracing via Grafana Tempo.
- **Identity Propagation**: Securely propagates user identity (Mock JWT) down to sub-agents.
- **Model Agnostic Adapters**: Custom adapters for running local models via Ollama and skeletal support for Amazon Bedrock.
- **Remote Agent Integration (A2A)**: Connecting to external agents using the Agent-to-Agent protocol.
- **Tool-based Extensions (MCP)**: Integrating with external toolsets via the Model Context Protocol (MCP).
- **Production-Ready Server**: A FastAPI-based web server with SSE (Server-Sent Events) for real-time streaming.

## How It Works

### 1. The Root Orchestrator (`orchestrator/app.py`)
The `root_agent` is the entry point for all user interactions. It is configured with instructions that define its role as a router. It doesn't perform tasks directly; instead, it identifies which sub-agent is best suited for the user's request based on their descriptions and capabilities.

**Sub-Agents managed by the Orchestrator:**
- **Local Specialized Agents**: `sensor_agent` (IoT), `metric_agent` (DevOps), `api_agent` (Finance), `parsing_agent` (Data Extraction), and `system_agent` (Bash commands).
- **MCP Agent**: A remote sub-agent that connects to a SQLite database via an MCP server using SSE transport.
- **A2A Agent**: A remote weather agent discovered dynamically via its `.well-known/agent-card.json`. It supports identity-aware forecasting.
- **Reviewer Agent**: A dedicated QA sub-agent that critiques responses before they reach the user (Critic Pattern).

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

## Distributed Observability (New!)
The Orchestrator is instrumented with **OpenTelemetry**. When configured, it emits traces to an OTLP collector — the Nexus stack runs **Grafana Tempo** (via `nexus-dev-infra`) — allowing you to visualize the full call graph of a request as it traverses from the Orchestrator to various sub-agents and external APIs.

**Configuration:**
```env
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318/v1/traces
OTEL_SERVICE_NAME=orchestrator
```

---

## Security & Identity (New!)
Nexus supports **Identity Propagation**. The UI sends a mock JWT token which the Orchestrator propagates to MCP and A2A sub-agents. This enables:
- **Audit Logging**: Knowing exactly which user triggered a tool call.
- **Scoped Access**: Sub-agents can filter data based on the provided identity context.

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

The Orchestrator can be run in two primary modes: using a local model via Ollama for development and privacy, or using provider-based models like Google Gemini for cloud deployments.

### Prerequisites
- Python 3.10+
- A `.env` file for environment variables (see below).

### Installation
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Execution Environments & Configuration

#### 1. Local Model (Ollama)
This mode is ideal for local development, offline usage, or when data privacy is a primary concern. It uses a model running locally via the Ollama server.

**Configuration (`.env` file):**
```env
# Tell the orchestrator to use the ollama adapter and specify the model
AGENT_MODEL=ollama/llama3
```

- **Ollama URL**: By default, the adapter connects to `http://localhost:11434`. If you are running in a containerized environment (like Docker with Colima on macOS), `localhost` may not resolve correctly. You can override the URL with the `OLLAMA_BASE_URL` environment variable:
  ```env
  OLLAMA_BASE_URL=http://host.docker.internal:11434
  ```

#### 2. Provider-Based (Cloud)
This mode uses a foundation model from a cloud provider, such as Google Gemini or Amazon Bedrock. This is suitable for production deployments where scalability and access to cutting-edge models are required.

**Configuration (`.env` file):**
```env
# Set the API key for your chosen provider
GEMINI_API_KEY=your_google_api_key_here

# Specify the model to use (this is the default)
AGENT_MODEL=gemini-2.5-flash
```

#### 3. Persistence Layer (New!)
The Orchestrator now supports persistent state and long-term memory using Redis or PostgreSQL. This ensures that session context is preserved across restarts.

**Configuration (`.env` file):**
```env
# Choose your persistence backend: in_memory (default), redis, or postgres
PERSISTENCE_BACKEND=redis

# For Redis:
REDIS_URL=redis://localhost:6379

# For PostgreSQL (supports pgvector for memory):
POSTGRES_URL=postgresql+asyncpg://nexus:password@localhost:5432/nexus_dev
```

- **Redis**: Fast, in-memory persistence. Suitable for most use cases.
- **PostgreSQL**: Robust, relational persistence. Uses the `pgvector` extension for future-proofing long-term memory with vector search capabilities.
- **In-Memory**: Default behavior. Data is lost when the orchestrator stops.

**Other Configuration:**
The following environment variables can be set to configure the remote agents:
- `MCP_SERVER_URL`: URL of the MCP server (default: `http://mcp-server:8000/sse`).
- `A2A_AGENT_URL`: URL of the A2A agent's card (default: `http://a2a-agent:8001/.well-known/agent-card.json`).

### CLI Mode (One-off Prompt)
```bash
./venv/bin/python main.py chat "How's the weather in London and what's the system uptime?"
```

### Interactive CLI Mode
```bash
./venv/bin/python main.py chat
```

### Server Mode (for Frontend Integration)
```bash
./venv/bin/python main.py serve
```
The server will start on `http://0.0.0.0:8080` (configurable via `--port` option).

### Health Checks
You can check the real-time status of the Orchestrator and its distributed sub-agents by visiting:
`GET http://localhost:8080/system-status`
