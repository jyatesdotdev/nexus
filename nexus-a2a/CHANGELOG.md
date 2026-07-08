# Changelog - Nexus Weather (A2A)

## [Refinement] - 2026-07-07
- **DRY the success-path "thinking" event:** the happy path reconstructed the initial `TaskStatusUpdateEvent` inline, byte-for-byte identical to what the `_enqueue_status` helper (already used on the clarification paths) produces. Routed it through the helper; behavior-preserving (tests unchanged, 8 pass). AGENTS.md's two-event description updated to name which paths use the helper vs the inline `metadata=`-carrying final event.

## [Bugfix] - 2026-07-04
- **Never report weather for non-locations:** Live incident: after an HR question, "What's the weather like?" (no location) was delegated with "in the engineering department" spliced in by the orchestrator; `extract_city` grabbed it and wttr.in fuzzy-geocoded the nonsense into a confident forecast. Two layers of defense added:
  - `extract_city` now returns `Optional[str]` — no more `"London"` fallback. Candidates are sanitized (trailing temporal words, leading articles) and rejected when they contain obvious non-place words (department/team/office/morning/...); `None` makes the executor ask for a specific location (two-phase streaming contract preserved: thinking update, then a final clarification, no wttr.in call).
  - `resolved_area_matches`: after fetching, the j1 payload's `nearest_area` (areaName/region/country) must loosely token-overlap the requested candidate; otherwise the fuzzy-geocoded result is discarded and the agent asks for clarification. Missing `nearest_area` counts as a match (can't validate).
- **Testing:** Suite grows 5 → 8: no-location query → clarification with zero HTTP calls; nonsense candidate resolved to an unrelated area → clarification without `structured_data`; extraction hardening cases (None for question-shaped/non-place inputs, "in Tokyo today" → Tokyo); happy path unchanged (Berlin mock now carries a matching `nearest_area`).

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
