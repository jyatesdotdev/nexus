# Changelog - Nexus Weather (A2A)

## [Maintenance] - 2026-07-03
- **Dependencies:** Pinned `a2a-sdk[http-server]==0.3.25`; the 1.x line removes `a2a.server.apps.jsonrpc.starlette_app` and breaks `server.py` imports.
- **Error Handling:** Added an explicit parse-error branch for malformed wttr.in payloads ("Could not parse weather data for {city}.") instead of falling through to the generic handler.
- **Messaging:** Aligned the HTTP-error message with the test suite ("The service returned status {code}."); all 5 tests now pass.
- **Docs:** Replaced `GEMINI.md` with per-directory `AGENTS.md`; corrected the README's JSON-RPC endpoint from `POST /rpc` to `POST /`.

## [Observability & Security] - 2026-03-27
- **Observability:** Integrated OpenTelemetry for distributed tracing.
- **Security:** Implemented identity propagation via `Authorization` metadata.
- **User Experience:** Updated agent "thinking" messages to reflect authenticated state.

## [A2A Capability] - 2026-03-21
- **Protocol:** Integrated **Agent-to-Agent (A2A)** capabilities.
- **Server:** Created A2A weather forecasting service using `a2a-sdk`.
- **Client Template:** Added client template to demonstrate direct message exchange.
- **Integration:** Enabled seamless cross-service delegation with the root orchestrator.
