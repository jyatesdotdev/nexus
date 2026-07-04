# tests/ — pytest suite for nexus-mcp

This directory contains the automated tests for the nexus-mcp HR Directory MCP
server (the parent directory). The application under test is `../server.py`
(FastMCP tools/resources) backed by `../database.py` (SQLModel `User` model,
SQLite). Tests are configured in `../pyproject.toml`
(`testpaths = ["tests"]`, `pythonpath = "."`, `--strict-markers`), so they MUST
be run from the repo root, not from inside this directory. `assert` usage is
allowed here (Ruff rule S101 is ignored for `tests/*`).

Isolation rule for this suite: tests must never touch the developer's local
`../hr.db` or any external database. This is achieved by pointing
`DATABASE_URL` at a throwaway temp-file SQLite database BEFORE importing any
application module — importing `database.py`/`server.py` binds the engine
immediately, and importing `server.py` also runs `init_db()`, which creates the
schema and seeds exactly 4 mock users (Alice Smith, Bob Jones, Charlie Brown,
Diana Prince).

## Files at this level

- `test_server.py` — the whole suite (11 tests). Structure and gotchas:
  - The first ~25 lines create a `tempfile.mkstemp(suffix=".db")` database and
    set `os.environ["DATABASE_URL"]` before the `from database import ...` /
    `from server import ...` lines. This ordering is load-bearing; the imports
    carry `# noqa: E402` for that reason. Keep any new imports of application
    modules BELOW the env-var assignment.
  - `teardown_module` deletes the temp .db file after the module finishes.
  - Tools are tested by calling the decorated functions directly
    (`search_directory(...)`, `get_system_status()`); FastMCP's decorators
    return the original callables, so no MCP client/transport is involved.
  - `test_init_db` asserts the user count is exactly 4, so tests that insert or
    delete rows can break other tests depending on execution order. If you add
    mutating tests, leave the seeded 4-user dataset untouched (the existing
    `delete_user` admin test inserts its own throwaway row and deletes it) or
    use fixtures rather than relying on order.
  - The `delete_user` tool is covered (added 2026-07): admin-allowed deletion,
    admin not-found, non-admin denial, and missing-header (anonymous) denial.
    The MCP `Context` is mocked with a `SimpleNamespace` duck-type built by the
    `_mock_context()` helper — `server._get_identity_from_context` only reads
    `ctx.request_context.headers`, so no MCP transport is involved. The admin
    identity is the bearer token `mock_user_123`.

## How to run

From the repo root (`/Users/jyates/Repositories/nexus/nexus-mcp`):

```bash
./venv/bin/python -m pytest            # all tests
./venv/bin/python -m pytest tests/test_server.py -k search -v
```

Requirements: `requirements.txt` and `requirements-dev.txt` installed, which
includes the editable sibling package `../../nexus-common` (server.py imports
`nexus_common`; collection fails with ModuleNotFoundError without it). The venv
was recreated 2026-07, so `./venv/bin/pytest` also works directly.

## Caution / do not modify

- Never remove or reorder the `DATABASE_URL` assignment above the application
  imports in `test_server.py`; doing so silently redirects tests at the real
  `../hr.db`.
- Do not import application modules at the top of new test files without first
  setting `DATABASE_URL` in that file as well (each module import is
  process-wide, but the engine binds on first import — the safe pattern is the
  one already used here).
- Tests must not hit external services or real databases; mock everything at
  the boundary.
