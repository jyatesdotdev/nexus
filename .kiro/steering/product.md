---
inclusion: always
---

# Nexus — Product Context

Nexus is an educational multi-agent orchestration platform demonstrating how specialized AI agents communicate via standard protocols (A2A, MCP) in a distributed, containerized architecture orchestrated by Google ADK.

## Purpose

This is a learning lab, not a production SaaS. Every design choice prioritizes clarity and teachability. Code should be easy to read, well-commented, and demonstrate patterns explicitly rather than abstracting them away.

## Architecture Overview

```
User ↔ nexus-ui (React) ↔ nexus-orchestrator (ADK root agent)
                                ├── nexus-mcp (HR Directory, MCP/SSE)
                                └── nexus-a2a (Weather Agent, A2A/JSON-RPC)
```

- The orchestrator is the single entry point for all user interactions.
- Sub-agents are independently deployable microservices discovered at runtime.
- Communication uses two open protocols: MCP (tool/resource access over SSE) and A2A (agent-to-agent via JSON-RPC).
- Identity propagates across all services via mock JWT tokens in `Authorization` headers.
- Observability (traces + metrics) flows from every service through `nexus-common` to the OTel Collector.

## Service Roles

| Service | Role | Protocol |
|---|---|---|
| nexus-orchestrator | Root agent, request routing, persistence, CLI | FastAPI + ADK SSE |
| nexus-mcp | HR directory (search, delete users) | MCP over SSE |
| nexus-a2a | Weather lookups (wttr.in) | A2A (JSON-RPC) |
| nexus-ui | Chat interface, generative UI, health dashboard | React SSE client |
| nexus-common | Shared telemetry + identity SDK | Python package |
| nexus-dev-infra | Postgres, Redis, Grafana, Prometheus, Tempo, OTel Collector | Docker Compose |
| nexus-stack | Full-stack orchestration, Makefile, CI rules | Docker Compose + Make |
| nexus-integration | E2E smoke tests against live stack | pytest in Docker |

## Domain Concepts

- **Agent Card**: JSON metadata at `/.well-known/agent-card.json` describing an A2A agent's capabilities and skills. The orchestrator uses these for dynamic discovery.
- **Agent Registry**: Decorator-based pattern (`@AgentRegistry.register`) for registering agent factory functions. Core agents are static; MCP/A2A agents register dynamically at startup.
- **Generative UI**: Agent responses carrying a `data.type` field trigger bespoke UI widgets (e.g., `weather_forecast` → WeatherWidget). The UI inspects structured data, not free text.
- **Human-in-the-Loop (HITL)**: Certain agent actions surface an Approve button in the UI, requiring explicit user confirmation before proceeding.
- **Reviewer/Critic Pattern**: `ReviewerEnforcementRunner` wraps the agent runner to programmatically enforce QA review of all responses. Responses are either APPROVED or sent back for REVISION.
- **Loop Detection**: `LoopDetectionRunner` monitors delegation sequences to prevent infinite agent-to-agent cycles.
- **Persistence Backends**: Selectable via `PERSISTENCE_BACKEND` env var — `in_memory` (default), `redis` (session + keyword memory), `postgres` (session + pgvector RAG with Gemini embeddings).
- **Two-Phase Streaming**: A2A responses stream a "thinking" event (`final=False`) followed by the result (`final=True`). The UI accumulates deltas for real-time rendering.

## Cross-Cutting Rules

- Every Python source file must include at least one `# EDUCATIONAL NOTE:` comment explaining a non-obvious design choice. Enforced by Semgrep.
- Test files must not contain live API URLs. Enforced by Semgrep.
- All external I/O (HTTP, Redis, SQL, subprocess) must be mocked in unit tests. No live network calls.
- All tools in the orchestrator return Pydantic `BaseModel` subclasses for structured output.
- The bash tool restricts execution to an explicit allowlist of commands.
- Each service maintains `README.md` (user-facing) and `AGENTS.md` (AI/LLM context). Both must stay in sync with code. `AGENTS.md` files exist at each directory level and describe the business rules of the files at that level, written so a low-context agent can work from a single directory's file alone.
- `CHANGELOG.md` in each service tracks changes in reverse chronological order with category tags (e.g., `[Refinement]`, `[Advanced Features]`).

## When Adding a New Service or Agent

1. Implement the appropriate protocol interface (A2A `AgentExecutor` or MCP `@mcp.tool()`).
2. Add a `/health` endpoint returning JSON status.
3. Integrate `nexus-common` for telemetry and identity.
4. Include `# EDUCATIONAL NOTE:` comments throughout.
5. Add the service to `nexus-stack/docker-compose.yml` with a healthcheck and `nexus-net` network.
6. Add a Prometheus scrape target in `nexus-dev-infra/prometheus.yml`.
7. Create both `README.md` and `AGENTS.md` (one per directory level).
8. Write unit tests mocking all external I/O.

## When Modifying Existing Behavior

- Check whether the change affects the orchestrator's agent tree or runner pipeline (`Runner` → `LoopDetectionRunner` → `ReviewerEnforcementRunner`).
- If changing a tool's return type, update the corresponding Pydantic model and any UI widgets that consume it.
- If changing SSE event shapes, update both the orchestrator's streaming logic and the UI's delta accumulation parser.
- Run `make verify-all` from `nexus-stack/` to validate lint, types, evals, Semgrep, and Checkov.
