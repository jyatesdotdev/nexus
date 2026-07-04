# Changelog - nexus-__SERVICE_NAME__

## [Scaffold] - __DATE__
- **Scaffolded** from `nexus-stack/templates/a2a-service` via `make new-agent NAME=__SERVICE_NAME__` (port __PORT__).
- **Protocol:** A2A sub-agent (a2a-sdk 0.3.x + Starlette) with agent-card discovery, two-phase streaming, `/health` + telemetry via nexus-common.
- **Next:** implement the real capability in `server.py`'s `process_query()` (see the TODO) and update the `AgentCard`.
