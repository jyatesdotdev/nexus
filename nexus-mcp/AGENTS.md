# nexus-mcp — HR Directory MCP Server

This repository is the HR-directory MCP server of the Nexus multi-agent learning
project. It is a Python FastMCP server that exposes a small corporate HR database
(SQLite, via SQLModel) to LLM orchestrators over the Model Context Protocol using
the SSE transport on port 8000. In the full Nexus stack, the orchestrator repo
(`../nexus-orchestrator`, Google ADK) creates an `mcp_agent` that connects to this
server at `http://mcp-server:8000/sse`; the stack is wired together by
`../nexus-stack/docker-compose.yml` (service name `mcp-server`). This repo depends
on the sibling repo `../nexus-common` (installed editable via requirements.txt) for
the `/health` endpoint, OpenTelemetry/Prometheus bootstrap, and mock identity
parsing.

The codebase is intentionally educational: architectural decisions are annotated
with `# EDUCATIONAL NOTE:` comments. Keep that convention when editing. Code style
is enforced with Ruff (config in pyproject.toml); Python target is 3.14.

## Files at this level

- `server.py` — entry point and all MCP definitions. Importing this module has
  side effects: it calls `init_db()` (creates the schema and seeds mock data) and
  `bootstrap_starlette_service()` from nexus_common (registers `/health` and
  telemetry on the Starlette app returned by `mcp.sse_app()`). Exposes:
  - Tool `search_directory(department=None, name=None)` — filters the `users`
    table; name matching is partial (`contains`).
  - Tool `delete_user(email, ctx)` — deletes users by email. Admin-gated: the
    caller's user id is parsed from the `Authorization: Bearer` header via
    `nexus_common.IdentityContext`, and only the hard-coded id `mock_user_123`
    is allowed. This is deliberately mock auth for the lab (the token payload is
    trusted verbatim); do not treat it as real security, and do not remove the
    check — the orchestrator's human-in-the-loop demo depends on it.
  - Resource `system://status` — static status string.
  Run directly with `python server.py` (uvicorn on 0.0.0.0:8000; MCP endpoint is
  `/sse`, health at `/health`).
- `database.py` — SQLModel model and engine. One model: `User` (table `users`:
  id, name, department, email). Database URL comes from the `DATABASE_URL` env
  var, falling back to `sqlite:///hr.db` (relative to the current working
  directory). `init_db()` runs `SQLModel.metadata.create_all(engine)` and seeds
  4 mock employees (Alice Smith, Bob Jones, Charlie Brown, Diana Prince) only if
  the table is empty. Schema changes: edit the `User` model AND create an Alembic
  revision (see `alembic/AGENTS.md`) — but be aware the runtime schema actually
  comes from `create_all`, not from migrations (see the caution in
  alembic/AGENTS.md).
- `hr.db` — the generated local SQLite database. It is NOT git-tracked
  (`.gitignore` has `*.db`) and must stay untracked. It is fully regenerable:
  delete it and start the server (or import `server.py`); `init_db()` recreates
  the schema and reseeds the 4 mock users. It also contains an empty
  `alembic_version` table left behind by a failed `alembic upgrade` attempt;
  this is harmless. Do not commit it and do not rely on any data in it.
- `alembic.ini` — Alembic configuration. The `sqlalchemy.url` placeholder in this
  file is ignored: `alembic/env.py` overrides it with `DATABASE_URL` from
  `database.py`. `prepend_sys_path = .` means Alembic commands must be run from
  this repo root so `database.py` is importable.
- `alembic/` — migration environment and version scripts. See
  `alembic/AGENTS.md`. Important: the existing migration chain cannot build the
  schema from scratch and fails on SQLite; details there.
- `tests/` — pytest suite. See `tests/AGENTS.md`.
- `Dockerfile` — multi-stage build, non-root `appuser`, socket healthcheck,
  exposes 8000. The build context must be the WORKSPACE PARENT directory, not
  this repo, because it copies both `nexus-mcp/` and `nexus-common/`:
  `cd .. && docker build -f nexus-mcp/Dockerfile -t mcp-hr-server .`
  Running `docker build .` from inside this repo fails. Normally the image is
  built and run via `../nexus-stack/docker-compose.yml`, which also bind-mounts
  this repo into the container at `/app`.
- `requirements.txt` — runtime deps (mcp[sse], uvicorn, starlette, sqlmodel,
  alembic, psycopg2-binary) plus `-e ../nexus-common`. The sibling checkout at
  `../nexus-common` is required for install to succeed.
- `requirements-dev.txt` — pytest, pytest-asyncio, ruff, httpx. Note: mypy is
  configured (`strict = true` in pyproject.toml) but not listed here; install it
  separately if you want to run type checks.
- `pyproject.toml` — Ruff config (line length 88, py314, extra rule sets I/UP/B/
  S/PTH/TRY; S101 ignored in tests), pytest config (`testpaths = ["tests"]`,
  `pythonpath = "."`, strict markers), mypy strict.
- `README.md` — human-facing overview. Known inaccuracies as of 2026-07: it does
  not mention the `delete_user` tool, its "alembic upgrade head" setup step fails
  on a fresh database, and its `docker build .` instruction does not work from
  this directory (context must be the parent). Prefer this AGENTS.md for facts.
- `CHANGELOG.md` — hand-maintained changelog; add an entry for user-visible
  changes.
- `.gitignore` / `.dockerignore` — exclude venvs, caches, and `*.db` from the
  repo and the Docker image.
- `venv/` — local virtualenv, gitignored. Its bin scripts have stale shebangs
  from before the repo was moved (they point at `.../nexus-directory/...`), so
  `./venv/bin/pip` and `./venv/bin/pytest` fail with "bad interpreter". Use
  `./venv/bin/python -m pip ...` / `./venv/bin/python -m pytest`, or recreate
  the venv.
- `.idea/`, `.pytest_cache/` — IDE and cache directories; ignore.

## How to run and test

Fresh local setup (from this directory):

```bash
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt   # needs ../nexus-common to exist
./venv/bin/python -m pip install -r requirements-dev.txt
./venv/bin/python server.py                            # serves MCP SSE on :8000
```

Do NOT run `alembic upgrade head` as a setup step; it fails on a fresh database
(see alembic/AGENTS.md). The server creates its own schema on startup.

Tests (must be run from this repo root):

```bash
./venv/bin/python -m pytest
```

Lint/format:

```bash
./venv/bin/python -m ruff format .
./venv/bin/python -m ruff check --fix .
```

Full stack: `../nexus-stack` (docker compose; this service is `mcp-server`).

## Caution / do not modify

- Never commit `hr.db` or any `*.db` file.
- Do not remove the module-level `init_db()` call in `server.py`; fresh
  deployments depend on it because the migration chain cannot create the schema.
- Importing `server.py` or `database.py` binds the engine immediately, so any
  test or script must set `DATABASE_URL` BEFORE the import or it will touch
  `hr.db`.
- Do not weaken or remove the admin check in `delete_user`; it is a teaching
  fixture used by the orchestrator's confirmation flow.
- Keep `-e ../nexus-common` in requirements.txt; the sibling-directory layout is
  assumed by both local installs and the Dockerfile.
- Do not edit the existing migration `alembic/versions/668e2bd0edd6_*.py`
  (already published as history); add new revisions instead.
