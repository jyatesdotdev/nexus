# Nexus Integration Tests

Cross-service integration tests for the Nexus multi-agent learning lab. Unlike the unit
tests inside each service repo (which mock all I/O), these tests hit real running
containers over the network. They are the "is the wiring alive" layer between per-service
unit tests and the Playwright browser E2E tests that live in `nexus-ui/e2e/`.

This directory is part of the single workspace-root git repository and intentionally has **no** `pyproject.toml` or
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

### `test_routing_integration.py`
- **What it does**: Two async tests (`test_weather_prompt_routes_to_a2a_agent`,
  `test_hr_prompt_routes_to_mcp_agent`) that drive the orchestrator end-to-end through
  its real user-facing endpoint, `POST /run_sse` — the same endpoint (and the same mock
  JWT) the React UI uses.
- **HOW**: Each test sends a natural-language prompt taken from the orchestrator's own
  routing baseline (`orchestrator/eval_cases.py`), consumes the SSE event stream to
  completion under a hard 120-second timeout, and asserts (a) a non-empty final answer
  and (b) that the expected sub-agent (`weather_a2a_agent` or `mcp_agent`) appears in the
  stream. Delegation is detected from ADK event `author` fields and
  `actions.transferToAgent` — the same fields that drive the UI's "Delegating to ..."
  banner.
- **Configuration**: `ORCHESTRATOR_URL` (default `http://localhost:8080`, which works
  from the host because the port is published; inside a container on `nexus-net`, set
  `ORCHESTRATOR_URL=http://orchestrator:8080`).
- **Graceful skip**: If the orchestrator's `/health` endpoint is unreachable, the tests
  `pytest.skip` with a clear message instead of failing — a stackless run stays green.
- **WHY**: Reachability tests prove the containers are alive; this test proves the
  *system* works — identity middleware, ADK root agent, live LLM routing decision, and a
  real sub-agent round-trip over A2A/MCP. Requires the full stack (`make up`) and a valid
  `GEMINI_API_KEY` in `nexus-stack/.env`, since routing is a live LLM decision.
- **Note**: `make test` in `../nexus-stack` discovers all tests in this directory
  automatically, so this test runs in-container as part of the normal suite.

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
docker compose run --rm -e PYTHONPATH=/app -e ORCHESTRATOR_URL=http://orchestrator:8080 orchestrator \
  pytest /e2e_tests/test_a2a_integration.py /e2e_tests/test_persistence_integration.py \
         /e2e_tests/test_routing_integration.py -v
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
- `orchestrator` and `a2a-agent` (from `nexus-stack/docker-compose.yml`) — the routing
  test also needs `mcp-server` and a valid `GEMINI_API_KEY` in `nexus-stack/.env`
- `redis` and `postgres` (from `nexus-dev-infra/docker-compose.yml`)
- the shared Docker network `nexus-net` (created by `make up` in nexus-stack)

## Continuous Integration

The workspace has a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs
per-service lint, type-check, and unit tests plus Semgrep and a static Checkov Dockerfile
scan, path-filtered so only changed services rebuild. **This directory's tests are
deliberately excluded from CI**: they require the live Docker stack, and the routing test
additionally requires a real `GEMINI_API_KEY`. The same is true of the LLM evals and the
Playwright browser E2E suite. Run stack-dependent suites locally via `nexus-stack`.

## Future Roadmap
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
