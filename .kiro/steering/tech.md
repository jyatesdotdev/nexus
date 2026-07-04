---
inclusion: always
---

# Tech Stack & Code Style

Quick reference for languages, frameworks, quality rules, and commands. For project structure and conventions, see `structure.md`. For product context and architecture, see `product.md`.

## Languages & Runtimes

| Layer | Language | Version |
|-------|----------|---------|
| Backend services | Python | 3.14 |
| Frontend | TypeScript | ~5.9 (strict) |
| Async model | httpx, asyncio, ASGI throughout |

## Backend Dependencies

- Google ADK: `LlmAgent`, `Runner`, `InMemoryRunner`, `AdkWebServer`, `RemoteA2aAgent`, `McpToolset`
- Web: FastAPI, Pydantic, Click (CLI), python-dotenv
- Persistence: Redis (redis-py async), PostgreSQL (asyncpg, SQLAlchemy async, pgvector), Google GenAI embeddings (`text-embedding-004`)
- MCP: FastMCP with Starlette SSE transport
- A2A: a2a-sdk, Starlette, uvicorn
- ORM: SQLModel (nexus-mcp), SQLAlchemy async + DeclarativeBase (orchestrator)
- Migrations: Alembic (nexus-mcp only)
- HTTP: httpx (async everywhere)
- ASGI: uvicorn (dev), gunicorn + uvicorn workers (prod)
- Telemetry: OpenTelemetry SDK, prometheus_client, W3C TraceContext
- Testing: pytest, pytest-asyncio (strict mode), respx, unittest.mock, FastAPI TestClient

## Frontend Dependencies

- React 19, Vite 8, TypeScript ~5.9 (strict, ES2023)
- Tailwind CSS 4 (@tailwindcss/vite), @tailwindcss/typography
- Class merging: `cn()` helper (clsx + tailwind-merge) — use this for all conditional classes
- Markdown: react-markdown
- Icons: lucide-react
- Font: Outfit (Google Fonts)
- Telemetry: @opentelemetry/auto-instrumentations-web → OTel Collector at localhost:4319
- Unit tests: Vitest (jsdom), @testing-library/react, @testing-library/jest-dom
- E2E: Playwright (Chromium only, against localhost:5173)
- Build: `tsc -b && vite build` — Docker uses pre-built `dist/` (no Node build stage, OOM workaround)

## Code Quality Rules

### Python

- Formatter/linter: `ruff` (line-length 88)
- Ruff target: py314 in all four Python projects (`requires-python = ">=3.14"` everywhere)
- Extended ruff rules (nexus-mcp): isort (I), pyupgrade (UP), bugbear (B), bandit (S), pathlib (PTH), tryceratops (TRY)
- S101 (assert) suppressed in test files
- Type checking: `mypy --strict` in all Python services
- pytest: `asyncio_mode = strict` — all async tests need explicit `@pytest.mark.asyncio`
- All external I/O must be mocked in unit tests (httpx, redis, SQLAlchemy, subprocess)

### TypeScript

- ESLint flat config: typescript-eslint, react-hooks, react-refresh
- Type checking: `tsc -b` (project references: tsconfig.app.json + tsconfig.node.json)
- Strict flags: noUnusedLocals, noUnusedParameters, noFallthroughCasesInSwitch, verbatimModuleSyntax

### Enforced by CI

- Semgrep: every Python source file needs `# EDUCATIONAL NOTE:` comment; no live API URLs in tests
- Checkov: CKV_DOCKER_11 (multi-stage builds), CKV_DOCKER_7 (non-root users)

## Commands

### Python (uv workspace, since 2026-07-04)

One uv workspace at the repo root replaces the per-service venv ritual. `uv sync` there creates a single shared `.venv` (and maintains the committed `uv.lock`); each service's pyproject declares its deps, with `nexus-common` as a `{ workspace = true }` editable source.

```bash
uv sync              # from the workspace root, once (and after dep changes)
cd <service>         # then run tools through the workspace env:
uv run pytest
uv run ruff check .
uv run ruff format .
uv run mypy .
```

Docker and CI do NOT use uv: they pip-install each service's `requirements.txt`, which is a hand-maintained mirror of that service's pyproject deps — update both files together (see the header comment in each requirements.txt). To compare the mirror against the lock, `uv export --project <service> --no-hashes --no-emit-workspace` prints the locked requirement set for that service (review only — the mirrors deliberately keep loose pins).

### Frontend (run from nexus-ui/)

```bash
npm install
npm run build        # tsc -b && vite build
npm run lint         # eslint
npm test             # vitest --run (single execution, no watch)
npm run test:e2e     # playwright (needs live Docker stack)
```

### Full stack (run from nexus-stack/)

```bash
make doctor          # preflight: docker, .env/API key, nexus-net, node/npm
make up              # infra + app services
make demo            # guided scripted conversation with trace links (stack must be up)
make down            # stop everything
make test            # unit + integration across all services
make lint            # ruff + eslint
make type-check      # mypy + tsc
make verify-all      # lint + type-check + evals + semgrep + checkov
```

CI: `.github/workflows/ci.yml` runs path-filtered lint/type/unit/Semgrep on push and PR;
evals and stack-dependent suites are excluded (see comments in the workflow).

### Database migrations (nexus-mcp/)

```bash
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Docker & Infrastructure

- Multi-stage builds → slim final image, non-root `appuser`, native HEALTHCHECK
- `nexus-common` installed as `-e ../nexus-common` in each Python service
- Shared network: `nexus-net` (external, created by Makefile)
- Gunicorn + uvicorn workers for prod (orchestrator, A2A); Nginx for frontend
- `make build` runs frontend build on host first (avoids container OOM)

### Service Ports

| Service | Port |
|---------|------|
| nexus-orchestrator | 8080 |
| nexus-mcp | 8000 |
| nexus-a2a | 8001 |
| nexus-ui | 5173 (dev) / 80 (prod) |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Grafana | 3000 |
| Prometheus | 9090 |
| Tempo | 3200 (API), 4317 (gRPC), 4318 (HTTP) |
| OTel Collector | 4319 (OTLP HTTP) |

### Key Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `GEMINI_API_KEY` | LLM API key | (required) |
| `AGENT_MODEL` | Model selection | `gemini-2.5-flash` |
| `OLLAMA_BASE_URL` | Local model endpoint | — |
| `PERSISTENCE_BACKEND` | `in_memory` / `redis` / `postgres` | `in_memory` (bare config); `redis` in the compose stack |
| `DATABASE_URL` | PostgreSQL/SQLite connection | `sqlite:///hr.db` (MCP) |
| `A2A_AGENT_URLS` | Comma-separated A2A endpoints for dynamic discovery; agents named from their cards | in-stack a2a-agent card URL |
| `REVIEWER_ENFORCEMENT` | Reviewer-critic pass on all responses (CLI + HTTP) | `true` |
| `VITE_API_BASE_URL` | Frontend API target | `http://localhost:8080` |
| `VITE_GRAFANA_URL` | Frontend Tempo trace links (build-time) | `http://localhost:3000` |

`nexus-stack/.env.example` is the canonical env-var reference.
