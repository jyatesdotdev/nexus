# __SERVICE_TITLE__ A2A Sub-Agent

A standalone sub-agent for the Nexus Multi-Agent Lab that follows the **Agent-to-Agent (A2A) protocol**. Scaffolded from `nexus-stack/templates/a2a-service` (`make new-agent NAME=__SERVICE_NAME__`), modeled on the canonical `nexus-a2a` weather agent.

## What it does

1. **Exposes an A2A-compliant interface** — an `AgentCard` at `GET /.well-known/agent-card.json` (discovery) and JSON-RPC at `POST /`. The orchestrator fetches the card at startup (via its `A2A_AGENT_URLS` list) and registers this agent under a name derived from the card's `name` field.
2. **Processes requests** — `process_query()` in `server.py` holds the domain logic. The scaffold echoes the request back; **replace the `TODO` inside it with your real capability.**
3. **Streams responses** — two-phase A2A streaming: a non-final "thinking" `TaskStatusUpdateEvent`, then a final result event (with optional `structured_data` metadata for the UI's generative widgets).

## Running the agent

### Environment variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `__SERVICE_UPPER___HOST` | Interface the server binds to. | `0.0.0.0` |
| `__SERVICE_UPPER___PORT` | Port the server listens on. | `__PORT__` |
| `__SERVICE_UPPER___PUBLIC_URL` | URL advertised for A2A discovery. | `http://__SERVICE_NAME__-agent:__PORT__` |
| `EXTERNAL_API_URL` | Optional upstream API to enrich answers. | unset (answer locally) |

### Docker (recommended)

Run as part of the stack (after wiring it into `nexus-stack/docker-compose.yml` — `make new-agent` printed the snippet):

```bash
cd ../nexus-stack && make up
```

### Manual setup

The workspace uses a shared [uv](https://docs.astral.sh/uv/) workspace — no per-service virtualenv. Add `"nexus-__SERVICE_NAME__"` to the root `pyproject.toml` workspace members first, then:

```bash
cd .. && uv sync && cd nexus-__SERVICE_NAME__
uv run ruff check .
uv run mypy server.py
uv run pytest
uv run python server.py   # http://localhost:__PORT__
```

## Health & discovery

- **Discovery card**: `GET /.well-known/agent-card.json`
- **JSON-RPC endpoint**: `POST /` (a2a-sdk default; handles `message/send`, `message/stream`)
- **Health**: `GET /health` (from `nexus-common`'s `bootstrap_starlette_service`, which also wires OpenTelemetry traces and Prometheus metrics)

## Nexus engineering standards

This service follows the workspace standards: `# EDUCATIONAL NOTE:` comments on non-obvious choices, strict Ruff/Mypy, fully isolated tests (respx mocking — never live APIs), and a multi-stage non-root Dockerfile with a native healthcheck. See `AGENTS.md` (and `tests/AGENTS.md`) for agent-facing detail.
