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
  - `orchestrator` (host port 8080, overridable via `ORCHESTRATOR_HOST_PORT` in `.env`):
    root agent. `depends_on` both sub-agents with
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
  - `frontend` (host port 5173 -> container 80; host port overridable via
    `FRONTEND_HOST_PORT` in `.env`): nginx serving the pre-built UI.
  All Python services mount their source repo into the container (live reload without
  rebuild) and mount `../nexus-common` at `/nexus-common`; the orchestrator additionally
  mounts `../nexus-integration` at `/e2e_tests`. All set
  `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4319` for tracing. Service names
  (`mcp-server`, `a2a-agent`, `orchestrator`, `frontend`) are contracts: Prometheus scrape
  targets in `../nexus-dev-infra/prometheus.yml` and the integration tests depend on them.
- `Makefile` — the intended entry point for everything (see "How to run" below). Gotchas:
  `build` first runs `npm install && npm run build` in `../nexus-ui` because the UI
  Dockerfile is nginx-only and serves a pre-built `dist/` — a bare `docker compose build`
  fails for the frontend without that step. `test`, `lint`, and `type-check` run the
  Python tools through the uv workspace at the repo root (since 2026-07-04): each target
  does one `uv sync` at the root, then `uv run --no-sync` per service against the shared
  `.venv` — no per-service virtualenvs exist anymore. `test`'s
  integration step points pytest at the mounted `/e2e_tests` directory (default
  `test_*.py` discovery), so new files in `../nexus-integration` are picked up without
  Makefile edits. `doctor` and `demo` delegate to `scripts/doctor.sh` and
  `scripts/demo.sh`. `clean` runs `docker compose down --rmi local` for both compose
  projects (removing only the Nexus-built images) plus `docker image prune -f` and
  `docker builder prune -f` — those prunes are machine-wide but safe (unreferenced dangling
  images and build cache only, never volumes or other projects' containers); `clean-all
  FORCE=1` additionally deletes the Nexus data volumes. `verify-all` runs lint + type-check + evals first, then Semgrep and Checkov
  in Docker against the whole parent directory.
- `scripts/doctor.sh` — preflight checks behind `make doctor`: Docker CLI + daemon, `.env`
  exists with a non-placeholder `GEMINI_API_KEY` (presence tested with `grep -q` only —
  the value is never read into a variable or printed), the external `nexus-net` network,
  Node/npm (needed because the UI builds on the host), and uv (needed by the
  test/lint/type-check targets). Reports every problem with a fix suggestion and exits
  nonzero if any check fails.
- `scripts/new-agent.sh` — scaffold generator behind `make new-agent NAME=<name>`
  (PORT optional; defaults to the first port ≥ 8002 not already mentioned in
  `docker-compose.yml` or `../nexus-dev-infra/prometheus.yml`). Copies
  `templates/a2a-service/` to `../nexus-<name>` (refusing to overwrite an existing
  directory), substitutes the placeholder tokens (`__SERVICE_NAME__`, `__SERVICE_SNAKE__`,
  `__SERVICE_UPPER__`, `__SERVICE_TITLE__`, `__PORT__`, `__DATE__` — table in
  `templates/AGENTS.md`), then prints a numbered next-steps checklist instead of editing
  shared files: a ready-to-paste compose service snippet (healthcheck, nexus-net,
  nexus-common mount), the `A2A_AGENT_URLS` line for the orchestrator (which discovers
  A2A agents dynamically — one sub-agent per reachable card, named from the card's
  `name`), the Prometheus scrape target, and the root uv-workspace member + `uv sync`.
  NAME must match `^[a-z][a-z0-9-]*$`.
- `templates/` — template trees consumed by `scripts/new-agent.sh`; currently one,
  `a2a-service/`, a complete A2A sub-agent closely modeled on the real `../nexus-a2a`
  (AgentExecutor with two-phase streaming, AgentCard, `/health` + telemetry via
  nexus-common, a pure `process_query()` domain function with the learner TODO,
  multi-stage non-root Dockerfile, respx-mocked tests that pass out of the box, per-level
  docs). See `templates/AGENTS.md` for the token table and rules. Template `.py` files
  and the Dockerfile live under `nexus-stack/**`, so the Semgrep educational-note rule
  scans them — they carry the notes and comply (a deliberate choice over extending the
  exclusion list: templates are example code learners read); template `tests/` fall under
  the existing `**/tests/**` exclusion.
- `scripts/demo.sh` — guided demo behind `make demo`. Requires a running stack: it probes
  `http://localhost:8080/health` and exits with "run make up" guidance if down. Then an
  embedded python3 (stdlib-only) POSTs three canned prompts to `/run_sse` — MCP
  delegation ("Who works in the engineering department?"), A2A delegation (Tokyo
  weather), and a local sensor tool — using phrasings mirrored from the orchestrator's
  `eval_cases.py` so routing is known-good, and deliberately avoiding prompts that
  trigger human-in-the-loop approval (they would stall a headless script). For each
  prompt it parses the SSE stream (same partial/final delta semantics as the UI), prints
  delegation hops, the final response, and the `X-Trace-Id` response header with a
  Grafana Tempo explore link (gracefully notes when the header is absent). Override
  targets with `ORCH_URL` / `GRAFANA_URL` env vars.
- `.env` — runtime secrets/config loaded automatically by docker compose:
  `GEMINI_API_KEY` (a real key — treat as secret, never commit or paste it),
  `AGENT_MODEL`, `OLLAMA_BASE_URL`, `GOOGLE_GENAI_USE_VERTEXAI=0`. It is gitignored;
  every fresh clone must recreate it (start from `.env.example`) or the orchestrator
  cannot call Gemini.
- `.env.example` — committed template for `.env`: every variable the stack consumes with
  placeholder values and one-line comments, including optional overrides
  (`GOOGLE_API_KEY`, `MCP_SERVER_URLS`, `A2A_AGENT_URLS`, `REVIEWER_ENFORCEMENT`) and a
  comment section on UI build-time `VITE_*` variables (which Vite bakes in at
  `make build` time and are NOT read from `.env`). Keep it in sync with
  `docker-compose.yml` and `../nexus-orchestrator/orchestrator/config.py`.
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
- `README.md` — human-facing overview and quickstart (cp .env.example → make doctor →
  make up → make demo).
- `TODO.md` — historical task list from the original monorepo cleanup; every item is
  checked off. Keep for history; do not treat its paths (`src/`, `projects/`) as current.
- `CHANGELOG.md` — reverse-chronological history, also predating the polyrepo split.
- `.gitignore` — ignores `.env`, venvs, caches, `*.db`.

This directory is part of the single workspace-root git repository. Subdirectories:
`scripts/` (doctor.sh, demo.sh, new-agent.sh — described above) and `templates/`
(service scaffolds for `make new-agent`; has its own AGENTS.md).

## How to run

All commands from this directory (`<workspace-root>/nexus-stack`):

```bash
make doctor      # preflight: docker, .env/GEMINI_API_KEY, nexus-net, node/npm, uv
make build       # npm-build the UI, then docker compose build all images
make up          # create nexus-net, start infra (../nexus-dev-infra), start app stack
make demo        # guided scripted conversation (MCP, A2A, local tool) — needs a running stack
make down        # stop app stack, then infra stack
make logs        # tail all app-stack logs
make chat        # interactive CLI chat with the orchestrator (docker compose run)
make test        # unit tests for orchestrator/mcp/a2a/ui, then integration tests in-container
make test-e2e    # make up, then Playwright browser tests from ../nexus-ui
make lint        # ruff (python services) + eslint (ui)
make type-check  # mypy (python services) + tsc (ui)
make evals       # LLM routing evals via the orchestrator CLI (needs valid GEMINI_API_KEY)
make verify-all  # lint + type-check + evals + Semgrep standards + Checkov docker checks
make clean       # down + remove Nexus-built images + prune dangling/build cache (no volumes)
make clean-all FORCE=1  # clean + DELETE Nexus data volumes (refuses without FORCE=1)
make new-agent NAME=<name> [PORT=<port>]  # scaffold ../nexus-<name> from templates/a2a-service
```

After `make up`: UI at http://localhost:5173, orchestrator API at http://localhost:8080
(`/health`, `/system-status`), MCP at http://localhost:8000, A2A at http://localhost:8001,
Grafana at http://localhost:3000 (admin/admin). The orchestrator and UI **host** ports
default to 8080/5173 but are overridable via `ORCHESTRATOR_HOST_PORT` / `FRONTEND_HOST_PORT`
in `.env` (see `.env.example`) — `make demo` picks the override up automatically, and a
squatted host port makes the VM port-forward fail silently while healthchecks stay green.

Adding a new A2A sub-agent to the stack: run `make new-agent NAME=<name>` and follow the
printed checklist — it scaffolds a complete service (protocol code, `/health` via
`nexus-common`, `# EDUCATIONAL NOTE:` comments, tests, Dockerfile, docs) and tells you
exactly what to paste into `docker-compose.yml`, the orchestrator's `A2A_AGENT_URLS`,
`../nexus-dev-infra/prometheus.yml`, and the root uv workspace. For non-A2A services, do
those same steps by hand: `/health` endpoint (nexus-common bootstrap helpers), compose
entry with healthcheck on `nexus-net`, Prometheus scrape target, educational notes.

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
- `make clean` removes only Nexus compose-built images; its `docker image prune` /
  `docker builder prune` are machine-wide but always safe — they delete only unreferenced
  dangling images and build cache, never volumes or other projects' containers.
  `make clean-all FORCE=1` additionally deletes the Nexus data volumes (Postgres/Redis/Grafana).
