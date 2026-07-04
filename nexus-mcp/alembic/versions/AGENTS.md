# alembic/versions/ — migration revision scripts for nexus-mcp

This directory holds the Alembic revision scripts for the nexus-mcp HR Directory
MCP server (repo root two levels up). Each file is one migration in a linked
chain (`revision` / `down_revision` identifiers). Revisions are generated with
`alembic revision --autogenerate -m "msg"` run from the repo root, and applied
with `alembic upgrade head`; the target database comes from the `DATABASE_URL`
env var (default `sqlite:///hr.db`). See `../AGENTS.md` for the full commands
and environment details.

## Files at this level

- `668e2bd0edd6_initial_migration.py` — the only revision (head,
  `down_revision = None`). Despite the name, it does NOT create the `users`
  table: it only runs `alter_column` on an existing table (tightening
  nullability and column types). Consequences, verified 2026-07:
  - `alembic upgrade head` on a fresh, empty database fails with
    "no such table: users".
  - On SQLite it fails anyway, because the emitted
    `ALTER TABLE users ALTER COLUMN ...` syntax is unsupported and batch mode is
    not enabled in `../env.py`.
  The real schema is created at server startup by
  `SQLModel.metadata.create_all()` in the repo-root `database.py` (`init_db()`).

## Caution / do not modify

- Do not edit `668e2bd0edd6_initial_migration.py`; it is published history. To
  change the schema, add a new revision whose `down_revision` is
  `"668e2bd0edd6"` (the current head).
- Every schema change must also be made to the `User` model in the repo-root
  `database.py`, or `--autogenerate` and the runtime schema will diverge.
- Keep `__pycache__` out of version control (already gitignored).
