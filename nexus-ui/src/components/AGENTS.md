# nexus-ui/src/components

Presentational React components for the nexus-ui chat dashboard (the frontend
of the Nexus multi-agent system). These components are stateless with respect
to application data: all state (messages, input text, loading flags, service
status) lives in `../App.tsx` and is passed down as props, and all network I/O
happens in App.tsx as well. Styling is Tailwind CSS v4 utility classes; shared
primitives (Button, Card, Input, Badge) come from the `ui/` subdirectory and
are imported via the barrel `./ui`.

Each component has a colocated `*.test.tsx` Vitest + React Testing Library
test. Tests run in jsdom with `../setupTests.ts` applied (jest-dom matchers,
`scrollIntoView` mocked) and must not perform real network calls.

## Files at this level

- `ChatHeader.tsx` — top bar of the chat card. Props: `status: 'Online' |
  'Offline'` (the orchestrator's status only) and `sessionId`. Renders a
  pulsing green dot when Online, red when Offline, and shows the session ID in
  monospace.
- `MessageList.tsx` — renders the conversation. Behaviors to preserve:
  - Empty state: when there are no messages, shows three suggested-query pill
    buttons ("HR Directory", "Weather Forecast", "System Status") that call
    `setInput(query)` — they fill the input box, they do not send.
  - `role === 'system'` messages render as small uppercase status lines (used
    for "Delegating to X..." notices). If a system message carries an
    `actionId` and a `handleApprove` prop was given, an "Approve" button is
    rendered — this is the human-in-the-loop (HITL) consent UI; clicking it
    calls `handleApprove(actionId)` which resumes the paused backend workflow.
  - User/agent messages render as chat bubbles (user right/indigo, agent
    left/slate) with the optional `author` label, body rendered through
    `ReactMarkdown` styled by Tailwind Typography `prose` classes (enabled in
    `../index.css`).
  - Generative UI: if `message.data?.type === 'weather_forecast'`, a
    `WeatherWidget` is rendered inside the bubble in addition to the text.
  - Trace visibility: agent messages with a `traceId` (set by App.tsx from
    the `X-Trace-Id` response header) render a `TraceLink` chip inside the
    bubble; messages without one render exactly as before.
  - The trailing empty `<div ref={messagesEndRef} />` is the scroll anchor
    App.tsx scrolls to on every new message — do not remove it.
- `MessageList.test.tsx` — tests for the above.
- `MessageInput.tsx` — controlled form at the bottom of the chat card. Props:
  `input`, `setInput`, `isLoading`, `isOffline`, `handleSend`. Submitting the
  form (Enter or the Send button) calls `handleSend`. The input is disabled
  while loading or when the orchestrator is offline (placeholder switches to
  "Nexus is offline"); the Send button is disabled when the input is
  empty/whitespace or the app is offline, and shows the Button's built-in
  spinner while loading.
- `MessageInput.test.tsx` — tests for the above.
- `SystemStatusGrid.tsx` — three-card health grid fed by the `ServiceStatus`
  object App.tsx polls from `/system-status`. Cards are hardcoded: Nexus Core
  (orchestrator, port 8080), MCP Server (port 8000, sub-status "Database" from
  `status.mcp_db`), A2A Agent (port 8001, sub-status "Weather API" from
  `status.a2a_api`). The helper `isOnline()` treats exactly `'Online'`,
  `'Connected'`, and `'Reachable'` as healthy — these literals mirror the
  backend contract in `../types.ts`, so keep them in sync. The port labels are
  display-only; changing real ports happens in the backend repos.
- `SystemStatusGrid.test.tsx` — tests for the above.
- `TraceLink.tsx` — small chip rendered on agent messages that carry a
  `traceId`: an anchor labeled `trace <first-7-hex-chars>` (full id in the
  `title` tooltip) that opens the message's distributed trace in Grafana
  Tempo in a new tab (`target="_blank"` + `rel="noopener noreferrer"`). The
  href comes from `buildTraceUrl()` in `../lib/trace.ts` (Grafana `/explore`
  with a URL-encoded left pane querying the `Tempo` datasource via TraceQL).
  Props: `traceId` (32-char hex OTel trace id) and optional `className`
  merged via `cn()`.
- `TraceLink.test.tsx` — tests for the above (href/label, new-tab rel).
- `WeatherWidget.tsx` — "generative UI" component: renders a structured
  `weather_forecast` payload (produced by the weather A2A agent and forwarded
  through the orchestrator as `metadata.structured_data`) as a rich card
  instead of plain text. Expects fields `city`, `temp_f`, `temp_c`,
  `description`, `humidity`, `wind_speed` (most optional). Uses lucide-react
  icons. If you add new structured payload types, follow this pattern and add
  a new `data.type` branch in MessageList.

## Subdirectories

- `ui/` — reusable UI primitives (Button, Card, Input, Badge) exported through
  a barrel `index.ts`. See `ui/AGENTS.md`.

## Run / test

From the repo root (`nexus-ui/`):

```bash
npm run test                        # run all Vitest tests
npx vitest run src/components       # run only this directory's tests
```

## Caution / do not modify

- Do not remove the scroll-anchor div at the end of MessageList.
- Do not change the `'Online' | 'Connected' | 'Reachable'` healthy-state
  literals without updating `../types.ts` and the orchestrator's
  `/system-status` response together.
- The `data.type === 'weather_forecast'` string is a contract with the
  backend's structured-data metadata.
- Keep the `EDUCATIONAL NOTE:` comments; they are a project convention.
