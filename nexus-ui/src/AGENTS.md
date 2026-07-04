# nexus-ui/src

Application source for nexus-ui, the React 19 + TypeScript + Vite frontend of
the Nexus multi-agent system. The UI is a chat dashboard that streams responses
from the Nexus orchestrator backend (Google ADK) over Server-Sent Events and
shows the live health of the backend services (orchestrator, MCP server, A2A
agent). All backend URLs derive from the env var `VITE_API_BASE_URL`
(default `http://localhost:8080`), read via `import.meta.env` and therefore
baked in at build time.

`App.tsx` owns essentially all application state and network logic; the
components under `components/` are presentational and receive state via props.
There is no router, no global state library, and no context provider.

## Files at this level

- `main.tsx` — entry point (loaded by `../index.html`). Order matters: it
  imports `./telemetry` FIRST as a side effect (OpenTelemetry must initialize
  before any fetch happens), then `./index.css`, then renders `<App />` inside
  `<StrictMode>` into `#root`. StrictMode double-invokes effects in dev, which
  is why the status poll may fire twice on mount during development.
- `App.tsx` — root component and the owner of all runtime behavior:
  - State: `messages`, `input`, `isLoading`, a per-mount random `sessionId`
    (`session_<random>`), and `status` (ServiceStatus).
  - Health polling: on mount, fetches `GET {base}/system-status` every 5
    seconds; any failure sets every service to Offline. The input box is
    disabled whenever `status.orchestrator === 'Offline'`.
  - `sendRequest(body)` — the SSE core. POSTs JSON to `{base}/run_sse` with
    `app_name: 'containerized_agents'` (must match the ADK app name on the
    orchestrator), a hardcoded mock-JWT `user_id` (intentional, for identity
    propagation demos), `session_id`, `streaming: true`. Reads
    `response.body.getReader()` chunk by chunk, splits on newlines, and parses
    lines starting with `data: ` as JSON ADK events. Handles:
    - Delta accumulation: `data.partial === true` appends the event text to a
      buffer; `partial === false` (or absent) REPLACES the buffer with the
      authoritative final text. The last agent message in `messages` is
      updated in place (matched by `role === 'agent'` and same/absent
      `author`) rather than appended.
    - Delegation tracking: `data.actions.transferToAgent` pushes a system
      message "Delegating to X..." once per distinct target (deduped via a
      local `announcedDelegation` variable) and resets the text buffer.
    - Human-in-the-loop: `data.actions.requestedToolConfirmations` (also
      accepts snake_case `requested_tool_confirmations`) pushes a system
      message carrying an `actionId`, which MessageList renders as an
      Approve button.
    - Generative UI: `data.metadata.structured_data` is attached to the agent
      message as `data`, which MessageList uses to render widgets.
  - `handleSend` — wraps the user's input as
    `new_message: { role: 'user', parts: [{ text }] }` and calls sendRequest.
  - `handleApprove(actionId)` — resumes a paused HITL workflow by sending a
    `function_response` part with name `adk_request_confirmation`, the
    actionId, and `response: { confirmed: true }`. The name and shape are an
    ADK contract; do not rename.
  - Gotcha: the initial `status` state sets `a2a_agent: 'Online'` while all
    other services start `'Offline'` — an inconsistency that the first poll
    overwrites within ~1s.
- `App.test.tsx` — Vitest + React Testing Library tests for App. Replaces
  `globalThis.fetch` with `vi.fn()` so no real network is touched; returns a
  mocked all-online `/system-status` payload. Follow this pattern for any new
  tests: unit tests must never hit real endpoints.
- `types.ts` — shared interfaces. `Message` (`role: 'user' | 'agent' |
  'system'`, `text`, optional `data` for generative-UI payloads, optional
  `author`, optional `actionId` for HITL). `ServiceStatus` uses exact string
  literals that mirror the orchestrator's `/system-status` response:
  `orchestrator`/`mcp_server`/`a2a_agent` are `'Online' | 'Offline'`, `mcp_db`
  is `'Connected' | 'Offline'`, `a2a_api` is `'Reachable' | 'Offline'`.
  Changing these breaks SystemStatusGrid's `isOnline` check and the backend
  contract.
- `telemetry.ts` — OpenTelemetry setup, imported for side effects by main.tsx.
  Registers a WebTracerProvider and MeterProvider with OTLP/HTTP exporters
  pointed at a hardcoded collector `http://localhost:4319/v1/traces` and
  `/v1/metrics` (the nexus-dev-infra observability stack); service name
  `nexus-ui`. Fetch instrumentation propagates W3C trace headers only to URLs
  matching `http://localhost:8080` (the orchestrator). Exports a `meter` for
  custom metrics (currently unused elsewhere). Requires `zone.js` (imported at
  the top) for async context propagation. The collector URL is NOT
  env-configurable — a known limitation.
- `setupTests.ts` — global Vitest setup (wired via `test.setupFiles` in
  `../vite.config.ts`): imports `@testing-library/jest-dom` matchers and mocks
  `HTMLElement.prototype.scrollIntoView`, which jsdom does not implement and
  which App's auto-scroll effect calls on every message change.
- `index.css` — the real global stylesheet. Loads the "Outfit" Google font,
  then Tailwind v4 via `@import "tailwindcss"` and
  `@plugin "@tailwindcss/typography"` (this is where the Tailwind typography
  plugin used by markdown `prose` classes is enabled — there is no
  tailwind.config.js). Sets the dark slate page background.
- `App.css` — leftover Vite template stylesheet, NOT imported by anything.
  Safe to ignore; candidate for deletion.
- `assets/` — `hero.png`, `react.svg`, `vite.svg`; none are referenced by any
  source file. Leftover template/demo assets; candidate for deletion. No
  AGENTS.md there.

## Subdirectories

- `components/` — presentational chat and status components; see
  `components/AGENTS.md`.
- `lib/` — small utilities (the `cn()` class-name helper); see
  `lib/AGENTS.md`.

## Run / test

From the repo root (`nexus-ui/`):

```bash
npm run dev     # dev server at http://localhost:5173
npm run test    # Vitest (jsdom); config lives in ../vite.config.ts
npm run lint    # ESLint
npm run build   # tsc -b && vite build (strict TS: unused vars fail the build)
```

## Caution / do not modify

- The `import './telemetry'` line must stay the first import in main.tsx.
- Do not change `app_name`, the mock `user_id`, the `/run_sse` body shape, or
  the `adk_request_confirmation` function-response name without coordinating
  with nexus-orchestrator.
- The SSE event field names handled in App.tsx (`partial`, `content.parts`,
  `author`, `actions.transferToAgent`, `actions.requestedToolConfirmations`,
  `metadata.structured_data`) are the Google ADK event schema — treat as an
  external contract.
- Keep the `EDUCATIONAL NOTE:` comment style intact; this is an educational
  codebase and those comments are a project requirement.
