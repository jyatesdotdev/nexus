# nexus-orchestrator

This repository is the central "root agent" of the Nexus multi-agent learning project. It is a Python service built on the Google Agent Development Kit (ADK) that receives user requests (via CLI or a FastAPI/SSE web server), decides which specialized sub-agent should handle each request, and delegates to it. Sub-agents include local tool-using agents (sensors, Prometheus metrics, YNAB budgets, entity parsing, safe bash), a remote HR agent reached over the Model Context Protocol (MCP, served by the sibling repo nexus-mcp), and a remote weather agent reached over the Agent-to-Agent (A2A) protocol (served by nexus-a2a). A reviewer sub-agent critiques every response out-of-band after it streams (review-then-revise: a REVISION verdict triggers one revision cycle so the user always ends with a real answer, never the raw critique).

Sibling repos in the workspace: nexus-a2a (weather A2A server), nexus-mcp (HR directory MCP server), nexus-ui (React frontend that talks to this server), nexus-common (shared Python library, installed editable from `../nexus-common`), nexus-dev-infra (Grafana/Tempo/Prometheus), nexus-stack (docker-compose deployment that builds and runs this service). The default LLM is Gemini (`gemini-2.5-flash`); local models via Ollama are supported through an adapter.

## Files at this level

- `main.py` — Intentionally tiny (4 lines). Entry point that imports and runs the Click CLI from `orchestrator/cli.py`. Used for local runs (`python main.py chat|serve|evals`). The Docker image does NOT run main.py; it runs Gunicorn against `orchestrator.asgi:app`.
- `Dockerfile` — Multi-stage build (python:3.14-slim), non-root `appuser`, healthcheck on `GET /health`. IMPORTANT: the build context is the workspace root, not this repo — it does `COPY nexus-orchestrator/requirements.txt` and `COPY nexus-common /nexus-common`. Build it from the parent directory (nexus-stack's compose file does this). Runtime command: `gunicorn orchestrator.asgi:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080`. Sets `PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc` (required for correct Prometheus metrics across Gunicorn workers) and wipes that dir on start.
- `requirements.txt` — Manual mirror of the pyproject deps (runtime + dev tooling: google-adk, a2a-sdk, mcp[sse], fastapi, redis, asyncpg, pgvector, pytest, ruff, mypy...), kept ONLY for the Dockerfile and CI installs; update it together with pyproject.toml when deps change. Ends with `-e ../nexus-common`, so installing requires the sibling nexus-common checkout to exist. Local dev uses the uv workspace instead. Note: SQLAlchemy (used by `orchestrator/persistence/`) is not pinned here; it arrives transitively via google-adk.
- `pyproject.toml` — `[project]` runtime deps + `[dependency-groups]` dev for the workspace-root uv workspace (`nexus-common` is a `{ workspace = true }` source; `[tool.uv] package = false` — the project is not installable as a package), plus tool config: Ruff targets py314, Mypy strict.
- `pytest.ini` — Sets `asyncio_mode = strict` (every async test needs `@pytest.mark.asyncio`) and silences DeprecationWarning/UserWarning.
- `README.md` — Human-facing overview. Refreshed 2026-07-03: root agent documented at `orchestrator/app.py`, tracing via Grafana Tempo (OTLP endpoint env var), default model `gemini-2.5-flash`.
- `CHANGELOG.md` — Reverse-chronological notes; newest entry goes at the top. Older entries are historical (e.g. the "src layout / src/agent_app/" entry describes a structure that no longer exists — leave history as-is).
- `.dockerignore` / `.gitignore` — Standard excludes. `.env` is git-ignored; secrets never go in the repo.

## Subdirectories

- `orchestrator/` — All application code. See `orchestrator/AGENTS.md`.
- `tests/` — Pytest suite (fully mocked, no network). See `tests/AGENTS.md`.
- `.mypy_cache/`, `.pytest_cache/`, `__pycache__/` — Local artifacts; never edit or commit. (The per-service `venv/` was removed 2026-07-04; the local environment is the shared `.venv/` at the workspace root, managed by `uv sync`.)

## How to run and test

Environment: create a `.env` file (or export vars) with at least `GEMINI_API_KEY` (or `GOOGLE_API_KEY`). The CLI refuses to start without one. Optional: `AGENT_MODEL` (default `gemini-2.5-flash`; `ollama/llama3` for local), `PERSISTENCE_BACKEND` (`in_memory` default, `redis`, or `postgres`), `MCP_SERVER_URLS`, `A2A_AGENT_URLS` (comma-separated A2A endpoints — base or agent-card URLs — discovered via each service's agent card at startup), `REVIEWER_ENFORCEMENT` (`true` default; toggles the programmatic reviewer-critic pipeline on both the CLI and HTTP paths).

```bash
cd <workspace-root> && uv sync      # once; creates the shared workspace .venv at the repo root
cd nexus-orchestrator
uv run python main.py chat "What is the weather in Paris?"   # one-shot prompt
uv run python main.py chat                          # interactive chat
uv run python main.py serve                         # FastAPI server on 0.0.0.0:8080
uv run python main.py evals                         # LLM routing evals (hits real model)
uv run pytest tests/                                # unit tests (no API key or network needed)
uv run ruff check orchestrator tests                # lint
uv run mypy orchestrator                            # strict type check
```

Full-stack (all services in Docker): `cd ../nexus-stack && make up` / `make down` / `make test`. Health probes on a running server: `curl http://localhost:8080/health` and `curl http://localhost:8080/system-status`.

Known state as of 2026-07-04: all 45 tests pass (25 pre-existing + 16 added with the trace-header/reviewer-wiring/A2A-discovery features + 3 net new with the streaming-safe reviewer semantics + 1 with the isolated-revision-session rework — see reviewer notes in `orchestrator/AGENTS.md`).

## Active-agent handoff semantics

Delegation in ADK is a TRANSFER, not a one-shot call: after the root agent transfers to a sub-agent, that sub-agent (not root) is the "active" agent that handles subsequent user turns, and it may transfer DIRECTLY to peer agents without going back through root. Verified against the installed google-adk (2.3.0): `AutoFlow` allows transfers parent→sub-agent, sub-agent→parent, and sub-agent→peers (peer transfers require the parent to be an `LlmAgent` and are on by default), and `Runner._find_agent_to_run` picks the LAST agent that replied — falling back to root only when that agent cannot transfer back up the tree. The opt-out knobs are `LlmAgent` fields `disallow_transfer_to_peers` and `disallow_transfer_to_parent` (both default `False`). For strict hub-and-spoke routing (every turn re-routed by root), set `disallow_transfer_to_peers=True` on each sub-agent so peers disappear from its transfer targets and handoffs must go via the root; do NOT set `disallow_transfer_to_parent=True` on sub-agents — that strands the sub-agent (it can never hand back). This repo deliberately keeps the ADK defaults (educational lab); this section documents the behavior, it does not change routing config.

## Caution / do not modify

- Do not commit `.env`, the workspace-root `.venv/`, or cache directories.
- Do not move `main.py` or rename `orchestrator.asgi:app` without updating the Dockerfile CMD and nexus-stack's compose config.
- The Dockerfile's COPY paths assume the workspace-root build context; changing them breaks the nexus-stack build.
- Project convention: explanatory architecture comments in code use the `# EDUCATIONAL NOTE:` prefix; keep that convention when adding commentary.
