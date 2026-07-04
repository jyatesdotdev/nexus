# nexus-ui/e2e

Playwright end-to-end tests for nexus-ui, the React frontend of the Nexus
multi-agent system. Unlike the Vitest unit tests under `src/` (which run in
jsdom and mock all network I/O), these tests drive a real Chromium browser
against a LIVE running stack: the frontend at `http://localhost:5173` plus the
full backend (orchestrator on 8080, MCP server, A2A agent — normally started
via the docker-compose in the sibling nexus-stack repo). The chat test sends a
real message through the orchestrator to an actual LLM, so these tests are
deliberately NOT isolated: they cost tokens, need network access, and will
fail if any backend service is down. Never run them in a context that must
avoid external API calls.

Configuration lives at the repo root in `../playwright.config.ts`: `testDir`
is this directory, baseURL `http://localhost:5173`, Chromium only, HTML
reporter (never auto-opens), 2 retries + 1 worker when `CI` is set, trace on
first retry. Playwright does not start any servers itself — everything must
already be running. Vitest is configured (in `../vite.config.ts`) to exclude
`e2e/**`, so `npm run test` never touches these files; conversely
`npx playwright test` only picks up files in this directory.

## Files at this level

- `chat.spec.ts` — two tests in a "Nexus Chat Interface" describe block:
  1. Loads `/` and waits (up to 15s) for at least one "Online" badge, proving
     the `/system-status` polling round-trip works.
  2. Waits for the input placeholder "Message Nexus..." to be enabled (the
     input is disabled until the orchestrator reports Online), sends the
     message `Hello, can you hear me? Just reply with "Yes I can" if so.`,
     asserts the user bubble appears, then waits up to 30s for the literal
     text "Yes I can" to stream back — proving the SSE POST to `/run_sse`,
     stream parsing, and markdown rendering all work end to end. Note this
     assertion depends on the LLM following the instruction; occasional
     flakiness is inherent.

  Gotchas the selectors depend on: the "Message Nexus..." placeholder text
  (`src/components/MessageInput.tsx`), the "Send" button label, the "Online"
  badge text (`src/components/SystemStatusGrid.tsx` / `ui/Badge.tsx`), and the
  heading text "Nexus". Renaming any of those in the components breaks these
  tests.

## Run

From the repo root (`nexus-ui/`), with the stack up:

```bash
# 1. Start the backend stack (from the workspace root's nexus-stack repo):
#    cd ../nexus-stack && docker compose up -d
# 2. Serve the frontend on port 5173 — either the docker "frontend" service
#    (published as 5173) or a local dev server:
npm run dev &
# 3. Run the tests:
npx playwright install chromium   # first time only
npm run test:e2e                  # headless run
npm run test:e2e:ui               # interactive UI mode
npm run test:e2e:report           # open the last HTML report
```

## Caution / do not modify

- Do not add these tests to the Vitest run or remove the `e2e/**` exclusion
  in `../vite.config.ts`.
- Do not point baseURL at production or a shared environment; the second test
  sends real prompts to the LLM.
- Keep timeouts generous (15s status / 30s LLM response); the first token can
  legitimately take that long on a cold stack.
