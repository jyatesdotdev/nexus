# nexus-integration

Cross-service integration tests for the Nexus multi-agent learning lab. Unlike the unit
tests inside each service repo (which mock all I/O), these tests hit real running
containers over the network: they verify that the A2A weather sub-agent answers protocol
discovery requests and that the persistence backends (Redis, Postgres) are reachable. They
are the "is the wiring alive" layer between per-service unit tests and the Playwright
browser E2E tests that live in `nexus-ui/e2e/`.

There is no pyproject/requirements file here. The intended way to run these tests is
inside the orchestrator container: `nexus-stack/docker-compose.yml` bind-mounts this
directory into the orchestrator at `/e2e_tests`, and the orchestrator image already has
every dependency the tests import (`pytest`, `pytest-asyncio`, `httpx`, `redis`,
`asyncpg`). This directory is part of the single workspace-root git repository.

## Files at this level

- `test_a2a_integration.py` — one async test, `test_a2a_communication`. It performs an
  HTTP GET on the A2A agent's discovery endpoint `/.well-known/agent-card.json` and
  asserts status 200 and that the card's `name` equals `"Weather Sub-Agent"` (that exact
  string is set in `nexus-a2a/server.py`; if the agent is renamed, this test must change).
  The base URL comes from `A2A_AGENT_URL`, defaulting to `http://localhost:8001`; if the
  variable already ends in `agent-card.json` it is used as-is (the orchestrator container
  sets it to the full card URL, so both forms work). Requires: the `a2a-agent` service
  from `nexus-stack/docker-compose.yml` running (host port 8001 is published, so this test
  also passes from the host with no env vars).
- `test_persistence_integration.py` — two async tests. `test_redis_connection` pings Redis
  at `REDIS_URL` (default `redis://redis:6379`); `test_postgres_connection` connects with
  asyncpg to `DATABASE_URL` (default `postgresql://nexus:password@postgres:5432/nexus_dev`)
  and runs `SELECT version()`. The default hostnames `redis` and `postgres` are Docker DNS
  names on the `nexus-net` network, and the credentials mirror
  `nexus-dev-infra/docker-compose.yml` — so by default these tests only pass inside a
  container attached to `nexus-net`. To run them from the host, override:
  `REDIS_URL=redis://localhost:6379 DATABASE_URL=postgresql://nexus:password@localhost:5432/nexus_dev`.
  Requires: the `redis` and `postgres` services from `nexus-dev-infra/docker-compose.yml`
  running.
- `README.md` — human-facing overview of the two test files and how to run them
  (in-container via `make test` from `../nexus-stack`, or from the host with overridden
  URLs). Rewritten 2026-07-03 to match reality; keep it in sync with this AGENTS.md.
- `CHANGELOG.md` — brief history. Older entries predate the polyrepo split and reference
  an old layout; do not rewrite them.
- `.pytest_cache/` — pytest artifact, ignore.

## How to run

Recommended path (matches `make test` in `../nexus-stack`), from `../nexus-stack` with the
full stack up (`make up`):

```bash
cd /Users/jyates/Repositories/nexus/nexus-stack
docker compose run --rm -e PYTHONPATH=/app orchestrator \
  pytest /e2e_tests/test_a2a_integration.py /e2e_tests/test_persistence_integration.py -v
```

From the host (requires `pip install pytest pytest-asyncio httpx redis asyncpg`
and the containers running):

```bash
cd /Users/jyates/Repositories/nexus/nexus-integration
REDIS_URL=redis://localhost:6379 \
DATABASE_URL=postgresql://nexus:password@localhost:5432/nexus_dev \
pytest -v
```

Services that must be running for the whole suite to pass:
- `a2a-agent` (from `nexus-stack/docker-compose.yml`)
- `redis` and `postgres` (from `nexus-dev-infra/docker-compose.yml`)
- the shared Docker network `nexus-net` must exist (created by `make up` in nexus-stack).

## Caution

- These tests intentionally hit live local containers, but must never call external/public
  APIs — that isolation rule is enforced by Semgrep (`nexus-stack/.semgrep.yaml`) across
  this directory.
- Default URLs and credentials in the tests are contracts with the two compose files
  (`nexus-stack/docker-compose.yml`, `nexus-dev-infra/docker-compose.yml`). Keep them in
  sync if either compose file changes service names, ports, or Postgres credentials.
