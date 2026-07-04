# nexus-stack

This directory is the deployment/orchestration hub for the Nexus multi-agent learning lab.
It contains no application code: it holds the docker-compose file that runs the
application services and the Makefile that is the primary interface for cross-service
operations (build, up/down, tests, lint, evals, standards verification). The system it
deploys: a root orchestrator agent (`../nexus-orchestrator`, Google ADK + FastAPI) that
delegates to a weather sub-agent over the A2A protocol (`../nexus-a2a`) and an HR
directory server over MCP (`../nexus-mcp`), plus a React frontend (`../nexus-ui`). Shared
Python utilities live in `../nexus-common`; integration tests in `../nexus-integration`.

Two compose stacks cooperate over one external Docker network, `nexus-net`:
- this directory's `docker-compose.yml` runs the application services;
- `../nexus-dev-infra/docker-compose.yml` runs infrastructure (Postgres, Redis, Tempo,
  Prometheus, Grafana, OTel collector).
`make up` here creates the network, starts the infra stack, then starts the app stack.
Everything assumes the sibling `nexus-*` directories are checked out next to this one,
because the compose build contexts point at the parent directory (`..`).

## Files at this level

- `docker-compose.yml` — four services, all on external network `nexus-net`:
  - `mcp-server` (host port 8000): MCP HR directory server. Healthcheck probes
    `http://localhost:8000/sse` (the SSE endpoint, not `/health`).
  - `a2a-agent` (host port 8001): A2A weather agent. Healthcheck probes
    `/.well-known/agent-card.json`.
  - `orchestrator` (host port 8080): root agent. `depends_on` both sub-agents with
    `condition: service_healthy`. Its environment wires the whole system together:
    `MCP_SERVER_URL=http://mcp-server:8000/sse`,
    `A2A_AGENT_URL=http://a2a-agent:8001/.well-known/agent-card.json`,
    `REDIS_URL=redis://redis:6379`,
    `POSTGRES_URL=postgresql+asyncpg://nexus:password@postgres:5432/nexus_dev`,
    `PROMETHEUS_URL=http://prometheus:9090`,
    `PERSISTENCE_BACKEND` (default `redis`), `GEMINI_API_KEY` and `AGENT_MODEL` from
    `.env` (compose fallback `gemini-1.5-flash`; `.env` currently sets `gemini-2.5-flash`).
    The hostnames `redis`, `postgres`, `prometheus`, `otel-collector` are services defined
    in `../nexus-dev-infra/docker-compose.yml` — the infra stack must be up or the
    orchestrator's persistence and telemetry fail.
  - `frontend` (host port 5173 -> container 80): nginx serving the pre-built UI.
  All Python services mount their source repo into the container (live reload without
  rebuild) and mount `../nexus-common` at `/nexus-common`; the orchestrator additionally
  mounts `../nexus-integration` at `/e2e_tests`. All set
  `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4319` for tracing. Service names
  (`mcp-server`, `a2a-agent`, `orchestrator`, `frontend`) are contracts: Prometheus scrape
  targets in `../nexus-dev-infra/prometheus.yml` and the integration tests depend on them.
- `Makefile` — the intended entry point for everything (see "How to run" below). Gotchas:
  `build` first runs `npm install && npm run build` in `../nexus-ui` because the UI
  Dockerfile is nginx-only and serves a pre-built `dist/` — a bare `docker compose build`
  fails for the frontend without that step. `test`, `lint`, and `type-check` reuse the
  orchestrator's virtualenv (`../nexus-orchestrator/venv`) to run tools for nexus-mcp and
  nexus-a2a as well, so that venv must exist with dev dependencies installed. `clean` runs
  `docker system prune -f` (removes ALL dangling images/containers machine-wide, not just
  Nexus ones). `verify-all` runs lint + type-check + evals first, then Semgrep and Checkov
  in Docker against the whole parent directory.
- `.env` — runtime secrets/config loaded automatically by docker compose:
  `GEMINI_API_KEY` (a real key — treat as secret, never commit or paste it),
  `AGENT_MODEL`, `OLLAMA_BASE_URL`, `GOOGLE_GENAI_USE_VERTEXAI=0`. It is gitignored;
  every fresh clone must recreate it or the orchestrator cannot call Gemini.
- `.semgrep.yaml` — custom CI/standards rules run by `make verify-all` across ALL sibling
  repos: (1) every source file (python/ts/js/dockerfile/yaml) must contain an
  `# EDUCATIONAL NOTE:` comment, excluding tests, changelogs, TODO.md, lockfiles, venvs;
  (2) test files must not call live external APIs (flags `api.google.com` and
  `api.open-meteo.com` URLs in test paths). When adding files anywhere in the workspace,
  include an educational note or Semgrep fails the build.
- `DEPLOYMENT.md` — describes the intended release model: each service repo does its own
  CI and publishes versioned images; this repo is the source of truth that promotes image
  tags and runs the `nexus-integration` suite before deploying. Note this is largely
  aspirational: the actual `docker-compose.yml` builds from local source with `build:`
  directives and mounts code as volumes; there is no private registry or pinned image tag
  in use today. `make verify-all` (Semgrep + Checkov) is the part that is real.
- `README.md` — human-facing overview and quickstart. Mostly accurate, but it still refers
  to the pre-split `projects/` layout in one heading and to `nexus-orchestrator/server.py`
  / `main.py` paths that have since moved under `nexus-orchestrator/orchestrator/`.
- `TODO.md` — historical task list from the original monorepo cleanup; every item is
  checked off. Keep for history; do not treat its paths (`src/`, `projects/`) as current.
- `CHANGELOG.md` — reverse-chronological history, also predating the polyrepo split.
- `.gitignore` — ignores `.env`, venvs, caches, `*.db`.

This directory IS its own git repository. There are no subdirectories to document.

## How to run

All commands from this directory (`/Users/jyates/Repositories/nexus/nexus-stack`):

```bash
make build       # npm-build the UI, then docker compose build all images
make up          # create nexus-net, start infra (../nexus-dev-infra), start app stack
make down        # stop app stack, then infra stack
make logs        # tail all app-stack logs
make chat        # interactive CLI chat with the orchestrator (docker compose run)
make test        # unit tests for orchestrator/mcp/a2a/ui, then integration tests in-container
make test-e2e    # make up, then Playwright browser tests from ../nexus-ui
make lint        # ruff (python services) + eslint (ui)
make type-check  # mypy (python services) + tsc (ui)
make evals       # LLM routing evals via the orchestrator CLI (needs valid GEMINI_API_KEY)
make verify-all  # lint + type-check + evals + Semgrep standards + Checkov docker checks
make clean       # make down + docker system prune -f (affects non-Nexus images too)
```

After `make up`: UI at http://localhost:5173, orchestrator API at http://localhost:8080
(`/health`, `/system-status`), MCP at http://localhost:8000, A2A at http://localhost:8001,
Grafana at http://localhost:3000 (admin/admin).

Adding a new service to the stack: give it a `/health` endpoint (use `nexus-common`
bootstrap helpers), add it here with a healthcheck on `nexus-net`, add a scrape target in
`../nexus-dev-infra/prometheus.yml`, and include `# EDUCATIONAL NOTE:` comments to satisfy
Semgrep.

## Caution / do not modify

- `.env` contains a live API key. Never commit it, echo it into logs, or copy it into
  other files. It is gitignored — keep it that way.
- Do not remove `external: true` from the `nexus-net` network or rename the services;
  names and ports (8000/8001/8080/5173) are referenced by nexus-dev-infra's Prometheus
  config, nexus-integration's tests, the orchestrator's env defaults, and the UI.
- The Postgres credentials in the orchestrator's `POSTGRES_URL` must match
  `../nexus-dev-infra/docker-compose.yml`.
- Do not "fix" the mcp-server healthcheck to `/health` without verifying the MCP server
  exposes it on that transport — the current check intentionally uses `/sse`.
- `make clean` prunes Docker system-wide; do not run it casually on a machine with other
  Docker workloads.
