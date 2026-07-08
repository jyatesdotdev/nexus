# Changelog

## [Refinement] - 2026-07-07
- **Added missing `type-check` script:** `package.json` had no `type-check` script, so `make type-check`'s `npm run type-check` step failed. Added `"type-check": "tsc -b"` (matches the build's type-check half). - Nexus UI
- **De-duplicated App.tsx:** hoisted `API_BASE_URL` and the all-`Offline` `OFFLINE_STATUS` snapshot to module-level constants (each was written verbatim twice), and `WeatherWidget` now reuses the shared `WeatherForecastData` type from `types.ts` instead of a field-for-field local copy. Behavior-preserving; 44 tests green. - Nexus UI

## [Branding] - 2026-07-05
- **Nexus favicon:** Replaced the leftover template lightning-bolt with a hand-authored Nexus mark — the letter N drawn as a network graph (hub node at the crossing, indigo palette matching the app, one emerald "healthy agent" satellite). 9.3K of blur filters down to 860 bytes. - Nexus UI

## [Trace Visibility] - 2026-07-04
- **Feature:** Per-message trace links. `sendRequest` now reads the `X-Trace-Id` response header from `POST /run_sse` (OTel trace id, CORS-exposed by the orchestrator) and attaches it to the agent messages of that turn (`Message.traceId` in `src/types.ts`).
- **Component:** New `TraceLink` chip (`src/components/TraceLink.tsx`) rendered on agent messages that carry a trace id: shows a short prefix of the id and deep-links (new tab) to Grafana Explore with a Tempo TraceQL query. Messages without a trace id render exactly as before, so the feature degrades gracefully until the orchestrator change lands.
- **Config:** New env var `VITE_GRAFANA_URL` (default `http://localhost:3000`) for the Grafana base URL; the Explore link targets the `Tempo` datasource uid provisioned by nexus-dev-infra (`src/lib/trace.ts`).
- **Tests:** Added streaming-fetch mocks asserting the chip renders with the correct href when the header is present and is absent otherwise (App, MessageList, TraceLink, trace URL builder) — suite grows from 35 to 44 tests.

## [Housekeeping] - 2026-07-03
- **Cleanup:** Removed dead files left over from the Vite template: `src/App.css`, `src/assets/` (`hero.png`, `react.svg`, `vite.svg`), and unreferenced `public/icons.svg`.
- **Config:** OTLP collector URL in `src/telemetry.ts` is now configurable via `VITE_OTEL_EXPORTER_URL` (default `http://localhost:4319`), mirroring `VITE_API_BASE_URL`.
- **Fix:** Initial system-status state now starts `a2a_agent` as `Offline` like every other service (the first poll previously overwrote the inconsistent `Online` default).
- **Naming:** Renamed the npm package from `frontend` to `nexus-ui`.
- **Docs:** Converted `GEMINI.md` into per-directory `AGENTS.md` files; refreshed stale README claims (SSE parsing lives in `sendRequest`, tests mock `globalThis.fetch` rather than using MSW, Docker build instructions).
- **Tests:** Updated stale Card/Input class assertions left over from the dark-theme restyle so the unit suite passes again.
- **Types:** Replaced `any` with a typed `StructuredData` union for generative-UI payloads (`src/types.ts`) and `as unknown as Response` casts in `App.test.tsx`, fixing all ESLint `no-explicit-any` errors.

## [Advanced Orchestration UI] - 2026-03-27
- **HITL:** Implemented Human-in-the-Loop UI with interactive "Approve" buttons for sensitive tool calls.
- **SSE:** Refactored SSE parsing logic for robust multi-agent state tracking and delta accumulation.
- **Security:** Integrated Mock JWT identity propagation in all backend requests.
- **Branding:** Standardized educational notes and component structure.

## [Initial Release] - 2026-03-21
- Initial React-based chat interface.
- SSE-based streaming support for real-time agent responses.
