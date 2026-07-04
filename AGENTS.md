# Nexus Workspace

Nexus is an educational multi-agent orchestration platform. Its purpose is to demonstrate how specialized AI agents communicate over open protocols — A2A (agent-to-agent, JSON-RPC) and MCP (Model Context Protocol) — in a distributed, containerized system orchestrated by Google ADK. It is a learning lab, not a production product: clarity and teachability beat cleverness in every design decision here.

If you are an AI agent working anywhere in this workspace: every meaningful directory contains an AGENTS.md describing the files at that level and their business rules. Read the AGENTS.md in whatever directory you are working in before modifying files there. This root file is the map; the per-directory files are the detail.

## Architecture

```
User <-> nexus-ui (React, SSE) <-> nexus-orchestrator (ADK root agent, :8080)
                                       |-- nexus-mcp  (HR directory, MCP over SSE, :8000)
                                       |-- nexus-a2a  (weather agent, A2A JSON-RPC, :8001)
```

The orchestrator is the single entry point for user requests. It routes each request to a specialized sub-agent: local tool agents, the HR directory over MCP, or the weather agent over A2A (discovered via its agent card at `/.well-known/agent-card.json`). Identity propagates between services as a mock JWT in the `Authorization` header. Every Python service uses `nexus-common` for telemetry (OpenTelemetry traces, Prometheus metrics) and identity parsing; traces and metrics flow to the infrastructure stack in `nexus-dev-infra`.

## Directory map

| Directory | What it is |
|---|---|
| `nexus-orchestrator/` | Google ADK "root agent" service (CLI + FastAPI/SSE server on :8080) that routes user requests to specialized sub-agents — local tool agents, the nexus-mcp HR agent over MCP, and the nexus-a2a weather agent over A2A — with a reviewer-critic pattern and pluggable Redis/Postgres persistence. |
| `nexus-mcp/` | HR-directory MCP server: FastMCP over SSE on :8000 (compose service name `mcp-server`), exposing a SQLite/SQLModel employee directory via `search_directory` and an admin-gated `delete_user` tool. |
| `nexus-a2a/` | A2A-protocol weather sub-agent (a2a-sdk 0.3.x + Starlette on :8001): parses a city from natural language, fetches wttr.in, streams two-phase task-status events back to the orchestrator. |
| `nexus-ui/` | React 19 + TypeScript + Vite chat dashboard: streams orchestrator responses over SSE (`POST /run_sse`), renders delegation notices, human-in-the-loop approval buttons, generative-UI widgets, and a live service-health grid. |
| `nexus-common/` | Shared Python library (`nexus_common` package): identical `/health` bootstrap, OTel tracing, Prometheus metrics, and mock-JWT identity for every Python service. Installed editable (`pip install -e ../nexus-common`) and volume-mounted into containers. |
| `nexus-dev-infra/` | Docker-compose infrastructure: Postgres, Redis, Tempo, Prometheus, Grafana, OTel Collector on the external `nexus-net` network. |
| `nexus-stack/` | Deployment hub: docker-compose for the four app services, the cross-service Makefile (`make up/test/lint/verify-all`), `.env` secrets, workspace-wide Semgrep rules. |
| `nexus-integration/` | Live-container integration tests (A2A discovery, Redis/Postgres persistence), run inside the orchestrator container via nexus-stack's `make test`. |
| `.kiro/steering/` | Workspace-wide steering docs: `product.md` (architecture and domain concepts), `structure.md` (layout and per-service conventions), `tech.md` (stack, quality rules, ports, env vars). Read these before cross-service changes. |

Each of these directories has its own AGENTS.md with per-file detail; nested directories (e.g. `nexus-orchestrator/orchestrator/persistence/`, `nexus-ui/src/components/`) have their own as well.

## Version-control layout

This workspace is ONE git repository rooted here (consolidated from per-service repos on 2026-07-04; each service's prior history was preserved and is browsable with `git log -- <service-dir>/`). Commit from the workspace root. Cross-service changes (e.g. an SSE event-shape change touching both the orchestrator and the UI) should land as a single atomic commit. The services remain independently deployable containers — that boundary lives in `nexus-stack/docker-compose.yml`, not in repo layout.


## Running and testing

Full-stack operations run from `nexus-stack/` (see `nexus-stack/AGENTS.md`):

```bash
cd nexus-stack
make up          # start infrastructure + app services
make test        # unit + integration tests across all services
make verify-all  # lint + type-check + evals + semgrep + checkov
make down        # stop everything
```

Per-service dev loops are documented in each service's AGENTS.md. Requires `GEMINI_API_KEY` in `nexus-stack/.env` (that file contains a live key — never commit or print it).

## Cross-cutting rules (enforced or load-bearing)

- Every Python source file must contain at least one `# EDUCATIONAL NOTE:` comment explaining a non-obvious design choice (enforced by Semgrep via `nexus-stack/.semgrep.yaml`).
- Unit tests mock all external I/O (HTTP, Redis, SQL, subprocess); no live network calls, no live API URLs in test files (Semgrep-enforced).
- Orchestrator tools return Pydantic `BaseModel` subclasses; the UI's generative widgets key off the structured `data.type` field, so changing a tool's return shape means updating the matching UI widget.
- Service names, ports, and the `nexus-net` network are agreed across `nexus-stack/docker-compose.yml`, `nexus-dev-infra/prometheus.yml`, and the orchestrator's service discovery — change them together or not at all.
- Each service keeps `README.md` (human-facing) and per-directory `AGENTS.md` (agent-facing) in sync with the code. `CHANGELOG.md` per service, reverse chronological. (Older docs referenced GEMINI.md files; those have been converted to AGENTS.md.)

## Files at this level

- `AGENTS.md` — this file. The only file that belongs at the workspace root; everything else lives inside a service directory.
