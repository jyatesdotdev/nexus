---
inclusion: always
---

# Project Structure & Conventions

Monorepo (single `.git` at the workspace root) of independently deployable services. The Python services share one uv workspace (root `pyproject.toml` + `uv.lock` + `.venv/`); each service keeps its own Dockerfile, test suite, and (for the UI) node_modules. For tech stack details see `tech.md`; for product context see `product.md`.

## Directory Layout

```
nexus-orchestrator/          # Root Agent / Central Hub (Google ADK + FastAPI)
├── main.py                  # CLI entry point (Click)
├── orchestrator/
│   ├── app.py               # Agent init, persistence factory, Runner wrappers
│   ├── asgi.py              # ASGI entry for gunicorn
│   ├── server.py            # FastAPI app factory, /health, /system-status
│   ├── config.py            # Env-based config
│   ├── cli.py               # Click CLI: chat, serve, evals
│   ├── middleware.py         # Identity middleware, OTel context propagation
│   ├── reviewer.py          # ReviewerEnforcementRunner
│   ├── tools.py             # Tool functions with Pydantic return models
│   ├── eval_cases.py        # EvalCase models for LLM routing evaluation
│   ├── agents/
│   │   ├── core_agents.py   # @AgentRegistry.register decorated factories
│   │   └── dynamic_agents.py # Runtime MCP/A2A agent registration
│   ├── adapters/
│   │   ├── ollama_adapter.py # OllamaAdapter(BaseLlm)
│   │   └── bedrock_adapter.py # BedrockAdapter(BaseLlm) stub
│   ├── persistence/
│   │   ├── database_services.py  # Async SQLAlchemy session CRUD
│   │   ├── redis_services.py     # Redis session + memory
│   │   └── postgres_services.py  # pgvector embeddings + cosine search
│   └── registry/
│       └── agent_registry.py     # Decorator-based agent registration
├── tests/                   # One test file per module, all I/O mocked
├── pytest.ini               # asyncio_mode = strict
├── Dockerfile
├── requirements.txt
└── pyproject.toml

nexus-mcp/                   # MCP HR Directory Server
├── server.py                # FastMCP tools + resources + health
├── database.py              # SQLModel User model, engine factory, init_db()
├── alembic/                 # Database migrations
├── tests/
├── Dockerfile
├── requirements.txt
└── pyproject.toml

nexus-a2a/                   # A2A Weather Sub-Agent
├── server.py                # AgentExecutor, AgentCard, health
├── tests/
├── Dockerfile
├── requirements.txt
└── pyproject.toml

nexus-ui/                    # React Frontend
├── src/
│   ├── App.tsx              # Root: state, SSE stream, delta accumulation
│   ├── main.tsx             # React 19 entry (StrictMode)
│   ├── index.css            # Global styles, Tailwind imports
│   ├── telemetry.ts         # Browser OTel setup
│   ├── types.ts             # Shared types
│   ├── components/
│   │   ├── *.tsx            # Feature components
│   │   ├── *.test.tsx       # Co-located tests
│   │   └── ui/              # Primitive design system (barrel: index.ts)
│   └── lib/
│       └── utils.ts         # cn() helper
├── e2e/                     # Playwright specs
├── Dockerfile               # Nginx-only (pre-built dist)
├── package.json
├── vite.config.ts
└── tsconfig.json

nexus-common/                # Shared Python SDK
├── nexus_common/
│   ├── __init__.py          # Exports: setup_telemetry, IdentityContext, verify_token
│   ├── auth.py              # IdentityContext, mock JWT parsing
│   ├── telemetry.py         # OTel + Prometheus setup
│   └── py.typed             # PEP 561 marker — consumers' mypy sees real types
└── pyproject.toml           # hatchling build backend

nexus-stack/                 # Full Stack Orchestration
├── docker-compose.yml       # App services on nexus-net
├── Makefile                 # Primary interface for all cross-service ops
├── .env                     # Runtime secrets and config
├── .semgrep.yaml            # CI enforcement rules
└── DEPLOYMENT.md

nexus-dev-infra/             # Local Infrastructure (Postgres, Redis, Grafana, Prometheus, Tempo, OTel Collector)
├── docker-compose.yml
├── prometheus.yml
├── tempo.yaml
├── otel-collector-config.yaml
└── grafana/                 # Provisioned datasources + dashboards

nexus-integration/           # E2E Integration Tests (run in Docker)
├── test_a2a_integration.py
└── test_persistence_integration.py
```

## File Naming & Location Rules

- Python service entry points: `server.py` (or `main.py` for orchestrator CLI)
- Shared Python code: `nexus-common/`, a uv-workspace source (`{ workspace = true }`) locally; Docker/CI install it as `pip install -e ../nexus-common` via requirements.txt
- Python deps: `[project]`/`[dependency-groups]` in each service's `pyproject.toml` (uv workspace at the repo root); each `requirements.txt` is a hand-kept mirror for Docker/CI — update both together
- Tests: `tests/` directory within each service; co-located `*.test.tsx` in nexus-ui
- Python config (ruff, mypy, pytest): `pyproject.toml` per service (orchestrator also has `pytest.ini`)
- Documentation per service: `README.md` (user-facing) + `AGENTS.md` (AI context, one per directory level) — keep in sync
- Changelogs: `CHANGELOG.md` per service, reverse chronological, with category tags like `[Refinement]`
- Root-level `AGENTS.md`: workspace map and canonical engineering standards reference

## Orchestrator Patterns

When modifying `nexus-orchestrator/`:

- Register agents with `@AgentRegistry.register("name")` decorator on factory functions
- Core agents go in `agents/core_agents.py`; dynamic MCP/A2A agents in `agents/dynamic_agents.py`
- Model adapters implement `BaseLlm` and register via `LLMRegistry.register(AdapterClass)` at import time
- All tools must return Pydantic `BaseModel` subclasses
- Bash tool: only allowlisted commands (`uptime`, `df -h`, `free -m`)
- Runner pipeline order: `Runner` → `LoopDetectionRunner` → `ReviewerEnforcementRunner`
- ASGI production entry: `orchestrator.asgi:app`
- CLI entry: `main.py` → Click group (`chat`, `serve`, `evals`)
- Tests: `sys.path.append` for root dir; mock all external I/O

## MCP Server Patterns

When modifying `nexus-mcp/`:

- Define tools with `@mcp.tool()` on plain functions; FastMCP generates schemas from type hints
- Define resources with `@mcp.resource("uri")`
- Database access: SQLModel `Session` context managers + `select()` queries — no raw SQL
- `init_db()` runs at module import: creates tables + seeds mock data if empty
- Authorization: helper functions `_get_identity_from_context`, `_is_admin`; sensitive ops check MCP context headers
- Alembic `env.py` imports `DATABASE_URL` from `database.py`
- Starlette SSE app via `mcp.sse_app()` for custom routes/middleware
- Tests: set `DATABASE_URL` to temp SQLite via `os.environ` before importing app modules

## A2A Agent Patterns

When modifying `nexus-a2a/`:

- Implement `AgentExecutor` interface (`execute()` + `cancel()`)
- Stream via `EventQueue.enqueue_event()` with `TaskStatusUpdateEvent`
- Two-phase response: "thinking" (`final=False`) then result (`final=True`)
- `AgentCard` at `/.well-known/agent-card.json` for discovery
- Extract domain logic into pure functions (e.g., `extract_city`) for testability
- Extract external API calls into helper methods
- Tests: `respx` for httpx mocking; cover success, HTTP error, parse error, network error paths
- Fixtures: `MagicMock(spec=RequestContext)`, `AsyncMock(spec=EventQueue)`

## UI Patterns

When modifying `nexus-ui/`:

- Functional components only; props via TypeScript interfaces above each component
- State: React hooks only (useState, useEffect, useRef) — no external state library
- Co-locate tests: `Component.tsx` + `Component.test.tsx`
- Primitives in `src/components/ui/` with barrel export via `index.ts`
- All primitives accept `className` and merge via `cn()` (clsx + tailwind-merge)
- Primitives extend native HTML element props (e.g., `React.ButtonHTMLAttributes`)
- Use variant pattern for visual states (Badge: success/error/neutral, Button: primary/ghost)
- SSE parsing: Web Streams API (`response.body.getReader()`) with delta accumulation
- Generative UI: messages with `data.type` render bespoke widgets (e.g., `weather_forecast` → WeatherWidget)
- HITL actions render an Approve button; system messages as small uppercase text

## nexus-common Patterns

When modifying `nexus-common/`:

- `setup_telemetry(service_name, app, app_type)` handles FastAPI and Starlette
- Starlette: raw ASGI middleware (not BaseHTTPMiddleware) to avoid SSE streaming issues
- Metrics: `nexus_http_requests_total` counter, `nexus_http_request_duration_seconds` histogram (labels: method, endpoint, status, service)
- `/metrics` and `/health` excluded from metric recording
- Supports `PROMETHEUS_MULTIPROC_DIR` for gunicorn multi-worker aggregation
- `IdentityContext` parses mock JWT from `Authorization: Bearer` header

## Required Annotations

Every Python source file must include at least one `# EDUCATIONAL NOTE:` comment explaining a non-obvious design choice. This is enforced by Semgrep in CI.

## Adding a New Service

1. Implement protocol interface: A2A `AgentExecutor` or MCP `@mcp.tool()`
2. Add `/health` endpoint returning JSON status
3. Integrate `nexus-common` for telemetry and identity
4. Add `# EDUCATIONAL NOTE:` comments
5. Add to `nexus-stack/docker-compose.yml` with healthcheck on `nexus-net`
6. Add Prometheus scrape target in `nexus-dev-infra/prometheus.yml`
7. Create `README.md` and `AGENTS.md` (one per directory level)
8. Write unit tests mocking all external I/O
