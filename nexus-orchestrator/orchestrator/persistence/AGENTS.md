# orchestrator/persistence/ — session and memory backends

This package provides persistent implementations of Google ADK's two storage interfaces so the Nexus orchestrator can keep chat state across restarts: `BaseSessionService` (per-session event history and state) and `BaseMemoryService` (long-term, cross-session memory search). Which backend is used is decided once, at import time of `orchestrator/app.py`, from the `PERSISTENCE_BACKEND` env var: `in_memory` (default, ADK built-ins), `redis` (uses `REDIS_URL`, default `redis://localhost:6379`), or `postgres` (uses `POSTGRES_URL`, default `postgresql+asyncpg://nexus:password@localhost:5432/nexus_dev`). Note the mixed pairing for postgres: sessions come from `database_services.DatabaseSessionService` and memory from `postgres_services.PostgresMemoryService`.

Contract notes that apply to all implementations: ADK service methods take keyword-only arguments (`app_name=`, `user_id=`, `session_id=`) — positional calls raise TypeError (a positional call bug exists in `orchestrator/middleware.py`). `append_event` must skip events with `event.partial` set (streaming chunks) and must call `super().append_event(...)` before persisting so the in-memory Session object is updated first.

## Files

- `__init__.py` — Empty.
- `redis_services.py` — `RedisSessionService`: stores each session as one JSON blob under `session:{app_name}:{user_id}:{session_id}` plus a set `sessions_list:{app_name}:{user_id}` for listing. Gotchas: `create_session` checks `exists` but then does nothing with the answer and unconditionally SETs a fresh empty session — calling it for an existing id WIPES that session's history (the middleware's auto-create path can trigger this on every /run_sse request); `list_sessions` without a `user_id` returns nothing; listed sessions have `events` stripped for efficiency. `RedisMemoryService`: LPUSHes event JSON to `memory:{app_name}:{user_id}` and does naive case-insensitive word-overlap search (no embeddings).
- `postgres_services.py` — `PostgresMemoryService`: semantic long-term memory backed by PostgreSQL + pgvector. Table `memory_entries` with a `Vector(768)` column; embeddings generated via Gemini `text-embedding-004` (768 dims — the column size and model must stay in sync). Requires `GEMINI_API_KEY` or `GOOGLE_API_KEY` for embeddings; if embedding fails it logs and falls back to a chronological (non-semantic) top-5 query, so it degrades rather than crashes. On first use it runs `CREATE EXTENSION IF NOT EXISTS vector` and creates tables — the DB role needs permission for that, and the pgvector extension must be available in the server image. Search uses cosine distance (`<=>`), limit 5.
- `database_services.py` — `DatabaseSessionService`: generic SQLAlchemy-async session store (table `sessions`, whole event list serialized in a JSON column; `id` alone is the primary key, so session ids are globally unique across apps/users). Works with any async SQLAlchemy URL, in practice `postgresql+asyncpg://...` (a plain `postgresql://` URL will fail — the async driver suffix is required). Tables auto-create on first use. `append_event` rewrites the full JSON event list each time — fine for a lab, not for huge histories.

SQLAlchemy is not listed in `requirements.txt`; it comes in transitively via `google-adk`. `asyncpg` and `pgvector` are listed explicitly.

## How to test

```bash
cd <workspace-root>/nexus-orchestrator
uv run pytest tests/test_redis_services.py tests/test_postgres_services.py tests/test_database_session_service.py
```

All tests mock the Redis client / SQLAlchemy engine; no infrastructure needed. For a live run, nexus-stack's docker-compose provides Redis and Postgres and sets `PERSISTENCE_BACKEND` accordingly.

## Caution

- Do not change the Redis key formats or table names without a migration story — existing deployed state (nexus-stack volumes) uses them.
- Keep the embedding model and `Vector(768)` dimension in sync; changing either invalidates stored vectors.
- Keep `append_event`'s partial-event skip; persisting streaming chunks would corrupt histories.
- `create_session` overwrite semantics (Redis) and duplicate-PK behavior (Postgres) differ from ADK's in-memory service, which raises on duplicates — be careful when writing code that assumes one behavior.
