# Nexus Integration Tests

Cross-service integration tests for the Nexus multi-agent learning lab. Unlike the unit
tests inside each service repo (which mock all I/O), these tests hit real running
containers over the network. They are the "is the wiring alive" layer between per-service
unit tests and the Playwright browser E2E tests that live in `nexus-ui/e2e/`.

This directory is its own git repository and intentionally has **no** `pyproject.toml` or
`requirements.txt`: the tests are designed to run inside the orchestrator container, which
already ships every dependency they import (`pytest`, `pytest-asyncio`, `httpx`, `redis`,
`asyncpg`).

## Test Files

### `test_a2a_integration.py`
- **What it does**: One async test, `test_a2a_communication`, which verifies that the A2A
  weather sub-agent is reachable and correctly implements A2A discovery.
- **HOW**: It sends an HTTP GET to the agent's discovery endpoint
  `/.well-known/agent-card.json` and asserts status 200 and that the card's `name` is
  `"Weather Sub-Agent"` (the exact string set in `nexus-a2a/server.py`).
- **Configuration**: The base URL comes from `A2A_AGENT_URL` (default
  `http://localhost:8001`). If the variable already ends in `agent-card.json` it is used
  as-is — the orchestrator container sets the full card URL, so both forms work.
- **WHY**: A2A agents are "pluggable." The root orchestrator discovers their capabilities
  dynamically via this "business card." If the endpoint is down or the schema is wrong,
  the orchestrator cannot delegate tasks to it.

### `test_persistence_integration.py`
- **What it does**: Two async tests verifying the persistence backends are reachable.
  `test_redis_connection` pings Redis; `test_postgres_connection` connects with `asyncpg`
  and runs `SELECT version()`.
- **Configuration**: `REDIS_URL` (default `redis://redis:6379`) and `DATABASE_URL`
  (default `postgresql://nexus:password@postgres:5432/nexus_dev`). The default hostnames
  are Docker DNS names on the `nexus-net` network and the credentials mirror
  `nexus-dev-infra/docker-compose.yml`, so by default these tests only pass inside a
  container attached to that network.
- **WHY**: The orchestrator's session persistence depends on this wiring; a green unit
  suite says nothing about whether the live containers can actually reach Redis/Postgres.

## Running the Tests

The recommended path is `make test` from `../nexus-stack`, which (after the unit tests)
runs this suite inside the orchestrator container. `nexus-stack/docker-compose.yml`
bind-mounts this directory into the orchestrator at `/e2e_tests`, so the tests always
reflect your working tree without a rebuild.

```bash
cd ../nexus-stack
make up      # create nexus-net, start infra + app stacks
make test    # unit tests for each service, then this suite in-container
```

To run just this suite in-container:

```bash
cd ../nexus-stack
docker compose run --rm -e PYTHONPATH=/app orchestrator \
  pytest /e2e_tests/test_a2a_integration.py /e2e_tests/test_persistence_integration.py -v
```

To run from the host instead (requires
`pip install pytest pytest-asyncio httpx redis asyncpg` and the containers running —
host ports are published for the A2A agent, Redis, and Postgres):

```bash
REDIS_URL=redis://localhost:6379 \
DATABASE_URL=postgresql://nexus:password@localhost:5432/nexus_dev \
pytest -v
```

Services that must be running for the whole suite to pass:
- `a2a-agent` (from `nexus-stack/docker-compose.yml`)
- `redis` and `postgres` (from `nexus-dev-infra/docker-compose.yml`)
- the shared Docker network `nexus-net` (created by `make up` in nexus-stack)

## Future Roadmap
- **SSE Stream Verification**: Add tests that listen to the orchestrator's `/run_sse`
  stream and assert that specific "thought" or "call" events from the MCP/A2A sub-agents
  appear in the event stream.
- **Auth Simulation**: Add tests that verify token propagation from the frontend through
  the orchestrator to the sub-agents.

## 📏 Nexus Engineering Standards

This project adheres to the **Nexus Engineering Standards**, prioritizing educational
clarity, production-grade quality, and architectural consistency:

- **Educational Integrity**: Architectural and "why" commentary is standardized with the
  `# EDUCATIONAL NOTE:` prefix.
- **Testing Isolation**: These tests intentionally hit live *local* containers, but must
  never call external/public APIs — enforced by Semgrep (`nexus-stack/.semgrep.yaml`).
- **Contracts**: Default URLs and credentials in the tests are contracts with
  `nexus-stack/docker-compose.yml` and `nexus-dev-infra/docker-compose.yml`. Keep them in
  sync if either compose file changes service names, ports, or Postgres credentials.
- **Living Reference**: `AGENTS.md` and `README.md` must be kept in sync with the
  project's actual state.
