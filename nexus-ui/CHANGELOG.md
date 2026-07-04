# Changelog - Nexus UI

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
