# nexus-integration

Cross-service integration tests for the Nexus multi-agent learning lab. Unlike the unit
tests inside each service repo (which mock all I/O), these tests hit real running
containers over the network: they verify that the A2A weather sub-agent answers protocol
discovery requests, that the persistence backends (Redis, Postgres) are reachable, and
that the orchestrator's root agent actually routes prompts to the correct sub-agent over
`/run_sse`. They are the "is the wiring alive" layer between per-service unit tests and
the Playwright browser E2E tests that live in `nexus-ui/e2e/`.

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
- `test_routing_integration.py` — two async tests exercising true end-to-end routing
  through the orchestrator's `POST /run_sse` endpoint (the same endpoint the React UI
  calls): a weather prompt that must be delegated to `weather_a2a_agent` and an HR prompt
  that must be delegated to `mcp_agent`. Each test POSTs a prompt (with the UI's mock
  JWT as `user_id` and a fresh `session_id`), consumes the SSE stream to completion under
  a hard 120 s timeout, asserts a non-empty final answer, and asserts the expected
  sub-agent appears in the stream — delegation is detected from ADK event `author` fields
  and `actions.transferToAgent`, exactly the fields the UI's "Delegating to ..." banner
  uses. Base URL comes from `ORCHESTRATOR_URL` (default `http://localhost:8080`; host
  port 8080 is published, so it works from the host; inside a container on `nexus-net`
  set `ORCHESTRATOR_URL=http://orchestrator:8080`). If `GET /health` is unreachable the
  tests `pytest.skip` instead of failing, so a stackless run stays green. Prompts and
  expected agent names mirror `nexus-orchestrator/orchestrator/eval_cases.py`; the agent
  names are contracts with `nexus-orchestrator/orchestrator/agents/dynamic_agents.py`
  (single-URL naming). Requires: the full app stack (`make up`) AND a valid
  `GEMINI_API_KEY`, since routing is a live LLM decision. `make test` in
  `../nexus-stack` discovers all tests in this directory automatically, so it runs
  in-container as part of the normal suite.
- `README.md` — human-facing overview of the test files and how to run them
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
docker compose run --rm -e PYTHONPATH=/app -e ORCHESTRATOR_URL=http://orchestrator:8080 orchestrator \
  pytest /e2e_tests/test_a2a_integration.py /e2e_tests/test_persistence_integration.py \
         /e2e_tests/test_routing_integration.py -v
```

From the host (requires `pip install pytest pytest-asyncio httpx redis asyncpg`
and the containers running):

```bash
cd /Users/jyates/Repositories/nexus/nexus-integration
REDIS_URL=redis://localhost:6379 \
DATABASE_URL=postgresql://nexus:password@localhost:5432/nexus_dev \
pytest -v
```

(`ORCHESTRATOR_URL` defaults to `http://localhost:8080`, which is correct for host runs.)

Services that must be running for the whole suite to pass:
- `orchestrator` and `a2a-agent` (from `nexus-stack/docker-compose.yml`); the routing
  test additionally needs `mcp-server` and a valid `GEMINI_API_KEY` in `nexus-stack/.env`
- `redis` and `postgres` (from `nexus-dev-infra/docker-compose.yml`)
- the shared Docker network `nexus-net` must exist (created by `make up` in nexus-stack).

## CI

`.github/workflows/ci.yml` at the workspace root runs per-service lint/type-check/unit
tests, Semgrep, and a static Checkov Dockerfile scan on push/PR (path-filtered per
service). This directory's tests are deliberately EXCLUDED from CI — they need the live
Docker stack (and, for routing, a `GEMINI_API_KEY`) — as are the LLM evals and the
Playwright E2E suite. If CI ever gains a Docker-in-Docker stage, this suite is the
natural candidate to wire in; the routing test already self-skips when the stack is
absent.

## Caution

- These tests intentionally hit live local containers, but must never call external/public
  APIs — that isolation rule is enforced by Semgrep (`nexus-stack/.semgrep.yaml`) across
  this directory.
- Default URLs and credentials in the tests are contracts with the two compose files
  (`nexus-stack/docker-compose.yml`, `nexus-dev-infra/docker-compose.yml`). Keep them in
  sync if either compose file changes service names, ports, or Postgres credentials.
