# Project TODO List: Multi-Agent Learning Lab

This list outlines the tasks required to clean up the legacy codebase, enhance the educational value through explicit `HOW/WHY` documentation, and improve the overall architecture and developer experience.

## 🧹 Legacy Code Cleanup
- [x] **Remove `src/` Directory**: Delete the entire `src/agent_app/` directory. Its contents (`agent.py`, `mcp_server.py`, `a2a_server.py`, `tools.py`, `config.py`) have been fully migrated into the `projects/` microservices architecture.
- [x] **Migrate and Remove `tests/` Directory**: 
    - Port the logic from `tests/test_agent_judge.py` (LLM-as-a-judge) into `projects/orchestrator/test_orchestrator.py`.
    - Port the logic from `tests/test_a2a_integration.py` into a new integration test suite within the `projects/` structure (potentially a top-level `e2e_tests/` folder run via docker).
    - Delete the old `tests/` directory to prevent confusion.
- [x] **Update Root `pyproject.toml`**: Adjust the build system or remove it if the project is no longer meant to be installed as a single Python package, given that dependencies are now managed per-container via `requirements.txt`.

## 🧠 Backend & Architecture (Orchestrator, MCP, A2A)
- [x] **Add HOW/WHY Comments to Orchestrator**:
    - **HOW/WHY**: Explain the `AdkWebServer` setup in `projects/orchestrator/server.py` (Why are we using InMemory services? How does the agent loader work?).
    - **HOW/WHY**: Explain the `Agent` and `McpToolset` definitions in `projects/orchestrator/main.py` (Why do we need specific instructions for routing? How does `SseConnectionParams` connect containers?).
- [x] **Add HOW/WHY Comments to MCP/A2A**:
    - **HOW/WHY**: Explain the `@mcp.tool()` and `@mcp.resource()` decorators in `projects/mcp_server/server.py`.
    - **HOW/WHY**: Explain the `AgentCard`, `AgentExecutor`, and `A2AStarletteApplication` in `projects/a2a_agent/server.py`.
- [x] **Abstract Hardcoded URLs**: Remove hardcoded `http://localhost:8080` and internal Docker URLs from the Python scripts. Ensure everything strictly relies on parsed environment variables with sensible fallbacks.
- [x] **Upgrade MCP Server to a Real Use-Case**: Update it to demonstrate a real capability, such as querying a local SQLite database (e.g., a mock user database).
- [x] **Upgrade A2A Agent to a Real API**: Integrate the weather agent with a free, public API (like Open-Meteo) to show how sub-agents can act as gateways to external data.

## 🎨 Frontend (React + Vite)
- [x] **Componentize `App.tsx`**: Refactor the monolithic App file into smaller, reusable components (`ChatHeader.tsx`, `MessageList.tsx`, `MessageInput.tsx`, `SystemStatus.tsx`).
- [x] **Add HOW/WHY Comments to Frontend Logic**:
    - **HOW/WHY on SSE Parsing**: Heavily document the `TextDecoder` and string manipulation logic in the `fetch` loop. *Why* do we split by `\n`? *How* do we handle the `data: ` prefix?
    - **HOW/WHY on Delta Accumulation**: Explain the `data.partial === true/false` logic. *Why* do we accumulate text? *Why* do we replace it on the final chunk?
    - **HOW/WHY on Delegation Tracking**: Explain the `announcedDelegation` state. *Why* do we track the target agent to prevent duplicate UI notices?
- [x] **Environment Variables**: Replace the hardcoded `http://localhost:8080` in the `fetch` calls with a Vite environment variable (e.g., `import.meta.env.VITE_API_BASE_URL`).
- [x] **Markdown Support**: Add a library like `react-markdown` to parse and safely render the agent's responses.

## 📚 Documentation & Developer Experience (DevEx)
- [x] **Rewrite Root `README.md`**: Update the documentation to reflect the new containerized microservices architecture. Include an architectural diagram (Mermaid.js or text-based).
- [x] **Create a `Makefile`**: Add commands like `make build`, `make up`, `make test`, and `make clean` to abstract away complex `docker compose` and cleanup commands for learners.
- [x] **Implement Live Reloading**: Update `docker-compose.yml` to use volume mounts (`./projects/orchestrator:/app`) for the Python containers so learners can modify agent logic and see changes without rebuilding the images.

## 🚀 Productionization & Best Practices
- [x] **Multi-stage Docker Builds**: Update all `Dockerfile`s to use multi-stage builds. For example, compile the Vite app in a `build` stage and serve it using a lightweight Nginx container in the `production` stage.
- [x] **Production Web Server**: Replace the development `vite` server with a production-grade static file server (like Nginx or Caddy) in the frontend container.
- [x] **Non-root Docker Users**: Update all Dockerfiles to run processes as a non-root user for enhanced security.
- [x] **Gunicorn/Uvicorn Tuning**: Update the backend Dockerfiles to use Gunicorn as a process manager with Uvicorn workers (e.g., `gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker`) instead of running `uvicorn` directly, to handle concurrent requests efficiently.
- [x] **Health Checks & Auto-healing**: Ensure the `docker-compose.yml` includes restart policies (e.g., `restart: always` or `restart: unless-stopped`) and robust health checks that the orchestrator can use to degrade gracefully.
- [x] **Logging & Telemetry**: Implement structured JSON logging in the Python services and add placeholders/comments explaining how to integrate OpenTelemetry (since Google ADK supports it) for distributed tracing across the agents.
- [x] **CORS Configuration**: Lock down the `allow_origins=["*"]` in `server.py` to only allow requests from the specific frontend URL in production.
- [x] **Rate Limiting**: Add a simple rate limiter middleware to the FastAPI orchestrator to demonstrate API protection.

## 🔌 Foundation Model Abstraction
- [x] **Bedrock/Alternative Model Support**: Implement interfaces/adapters to allow the agents to use Amazon Bedrock APIs or other foundation models. Include instructions or a template explaining how learners can add support for additional model providers (e.g., OpenAI, Anthropic, local OSS models) while maintaining the same agent orchestration logic.
- [x] **Ollama Support**: Add support for running local models via Ollama. Create an adapter and provide instructions on how to start Ollama with a recommended model (e.g., Llama 3) and connect the orchestrator to the local endpoint.

## 📝 Documentation Generation
- [x] **Generate Documentation for `a2a_agent`**: Use a sub-agent to create comprehensive documentation for the A2A agent project.
- [x] **Generate Documentation for `e2e_tests`**: Use a sub-agent to create comprehensive documentation for the end-to-end tests project.
- [x] **Generate Documentation for `frontend`**: Use a sub-agent to create comprehensive documentation for the frontend React project.
- [x] **Generate Documentation for `mcp_server`**: Use a sub-agent to create comprehensive documentation for the MCP server project.
- [x] **Generate Documentation for `orchestrator`**: Use a sub-agent to create comprehensive documentation for the orchestrator project.