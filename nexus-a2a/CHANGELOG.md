# Changelog - Nexus Weather (A2A)

## [Tooling] - 2026-07-04
- **uv workspace:** Runtime deps moved into `pyproject.toml` `[project]` (the `a2a-sdk[http-server]==0.3.25` pin unchanged) with dev tooling in `[dependency-groups]`; `nexus-common` is now a `{ workspace = true }` source. The per-service `venv/` is gone — `uv sync` at the workspace root creates the shared `.venv`, and `uv run pytest|ruff|mypy` replaces the venv-bin invocations. `requirements.txt` stays as a hand-kept mirror for the Dockerfile and CI (header comment documents the sync rule).
- **pytest:** `pythonpath = ["."]` added to pyproject so tests can `import server` without a manual `PYTHONPATH=.`.
- **Typing:** nexus-common now ships `py.typed`, so mypy follows its real types here.

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
