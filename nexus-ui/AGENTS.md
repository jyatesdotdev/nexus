# nexus-ui

This repo is the React frontend for the Nexus system, a learning project about
agents communicating with each other. Nexus consists of an orchestrator "root
agent" (Google ADK) that delegates work to sub-agents and remote services via
the A2A protocol and MCP. nexus-ui is the browser dashboard for that system: a
chat interface that POSTs user messages to the orchestrator's `/run_sse`
endpoint and renders the Server-Sent Events (SSE) stream in real time
(including LLM token deltas, agent-delegation notices, and human-in-the-loop
approval prompts), plus a health grid that polls the orchestrator's
`/system-status` endpoint every 5 seconds. Sibling repos in the workspace:
nexus-orchestrator (the backend this UI talks to), nexus-a2a, nexus-mcp,
nexus-common, nexus-dev-infra, nexus-stack (docker-compose that builds and runs
this UI as the `frontend` service).

Stack: React 19, TypeScript (strict), Vite, Tailwind CSS v4 (configured in CSS,
no tailwind.config.js), react-markdown, Vitest + React Testing Library (unit),
Playwright (e2e), OpenTelemetry web SDK (traces + metrics). The
runtime-relevant environment variables are `VITE_API_BASE_URL` (orchestrator
base URL, default `http://localhost:8080`) and `VITE_OTEL_EXPORTER_URL` (OTLP
collector base URL, default `http://localhost:4319`); note Vite inlines env
vars at **build** time, so a production bundle bakes the values in.

## Files at this level

- `package.json` — npm manifest (package name `nexus-ui`; note the nexus-stack
  compose service that runs this UI is still called `frontend`).
  Scripts: `dev`, `build` (`tsc -b && vite build`), `lint`, `preview`, `test`
  (Vitest unit tests), `test:e2e`, `test:e2e:ui`, `test:e2e:report`
  (Playwright). Contains npm `overrides` pinning `@opentelemetry/*` package
  versions so the OTel web SDK pieces stay mutually compatible — do not remove
  them casually.
- `vite.config.ts` — Vite plugins (react, `@tailwindcss/vite`) AND the Vitest
  config in the same file: jsdom environment, globals on, setup file
  `./src/setupTests.ts`, and `e2e/**` excluded so Vitest never picks up
  Playwright specs.
- `playwright.config.ts` — e2e config: tests live in `./e2e`, baseURL
  `http://localhost:5173`, Chromium only, HTML reporter. Playwright does NOT
  start any servers; the app and backend stack must already be running (see
  `e2e/AGENTS.md`).
- `index.html` — Vite entry HTML. `<html class="dark">` is set here (the
  components use `dark:` Tailwind variants). Mounts `#root` and loads
  `/src/main.tsx`. References `/favicon.svg` from `public/`.
- `tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json` — project
  references. `tsconfig.app.json` has `strict: true`, `noUnusedLocals`,
  `noUnusedParameters`; `npm run build` runs `tsc -b` first, so type errors and
  unused variables fail the build.
- `eslint.config.js` — flat ESLint config: typescript-eslint recommended,
  react-hooks, react-refresh; ignores `dist`.
- `Dockerfile` — **intentionally NOT a multi-stage build.** It is a plain
  nginx:alpine-slim image that copies a pre-built `nexus-ui/dist` from the
  build context; the host must run `npm run build` first. This is deliberate:
  running `tsc` inside Docker was OOM-killed in constrained environments. The
  COPY path `nexus-ui/dist` assumes the Docker build context is the workspace
  parent directory (nexus-stack's compose file uses `context: ..`,
  `dockerfile: nexus-ui/Dockerfile`). Runs as non-root `appuser`, exposes port
  80, defines a native HEALTHCHECK (wget on `/`). In the nexus-stack compose,
  the container's port 80 is published as host port 5173.
- `README.md` — human-facing docs (setup, SSE/delta/delegation explanations).
- `CHANGELOG.md` — brief release notes (housekeeping, HITL, SSE refactor,
  mock JWT).
- `public/` — static assets copied verbatim into the build: `favicon.svg`
  (used by index.html).
- `.gitignore` — standard Node/Vite ignores.

## Subdirectories

- `src/` — application source. See `src/AGENTS.md`.
- `e2e/` — Playwright browser tests against a live stack. See `e2e/AGENTS.md`.
- `dist/`, `node_modules/` — generated; never edit.

## Run / test / build

```bash
npm install                 # install dependencies
npm run dev                 # Vite dev server at http://localhost:5173
npm run build               # tsc -b && vite build -> dist/
npm run preview             # serve the production build locally
npm run test                # Vitest unit tests (jsdom, no network)
npm run lint                # ESLint
npm run test:e2e            # Playwright (requires running stack, see e2e/AGENTS.md)
VITE_API_BASE_URL=http://localhost:8080 npm run dev   # point at orchestrator
```

Docker (production image; build dist on the host first):

```bash
npm run build
cd .. && docker build -f nexus-ui/Dockerfile -t nexus-ui .   # context = workspace root
docker run -p 5173:80 nexus-ui
```

## Conventions

- Functional components with hooks only; strict TypeScript; prefer interfaces
  for data shapes.
- Utility-first Tailwind; use the `cn()` helper from `src/lib/utils.ts` for
  conditional/merged class names.
- This is an educational codebase: non-trivial choices carry
  `EDUCATIONAL NOTE:` comments explaining WHY/HOW. Preserve and extend that
  style when editing.
- Unit tests must never hit the network; mock `fetch` (see `src/App.test.tsx`).

## Caution / do not modify

- Do not convert the Dockerfile to a multi-stage build without checking memory
  constraints — the single-stage copy-from-host design is intentional.
- Do not change `app_name: 'containerized_agents'` or the request body shape in
  `src/App.tsx` without matching changes in nexus-orchestrator; they follow the
  Google ADK `/run_sse` API contract.
- The hardcoded JWT-looking `user_id` in `src/App.tsx` is an intentional mock
  identity for propagation demos, not a leaked secret.
- Do not remove the `@opentelemetry/*` entries from `overrides` in
  package.json without re-testing telemetry initialization.
- The service-status string literals (`Online`/`Offline`, `Connected`,
  `Reachable`) in `src/types.ts` are part of the orchestrator's
  `/system-status` response contract.
