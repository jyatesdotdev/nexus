# nexus-ui/src/lib

Small shared utilities for nexus-ui, the React frontend of the Nexus
multi-agent system. This directory contains the `cn()` class-name helper,
which every UI primitive in `src/components/ui/` and several feature
components use for Tailwind class composition, and the Grafana Tempo
trace-link builder used by the per-message trace chips. If you add
framework-agnostic helper functions, put them here with a colocated Vitest
test file.

## Files at this level

- `utils.ts` — exports `cn(...inputs: ClassValue[]): string`, a composition of
  `clsx` (conditional class names from strings/objects/arrays, drops falsy
  values) and `tailwind-merge` (resolves conflicting Tailwind utilities so the
  LAST one wins, e.g. `cn('p-4', 'p-2')` yields `'p-2'`). This last-wins
  behavior is what lets components accept a `className` prop that overrides
  their built-in styles — components pass their defaults first and the
  caller's `className` last.
- `utils.test.ts` — Vitest tests covering string merging, conditional
  objects, arrays, falsy filtering, and Tailwind conflict resolution.
- `trace.ts` — Grafana Tempo deep-link helpers used by
  `src/components/TraceLink.tsx`: `buildTraceUrl(traceId)` builds a Grafana
  `/explore?orgId=1&left=<url-encoded JSON pane>` URL with a TraceQL query
  that is the bare OTel trace id; `shortTraceId(traceId)` returns the
  7-char display prefix; `getGrafanaBaseUrl()` reads `VITE_GRAFANA_URL`
  (default `http://localhost:3000`, build-time inlined by Vite).
  `TEMPO_DATASOURCE_UID` is `'Tempo'` and must match `uid: Tempo` in
  `nexus-dev-infra/grafana/provisioning/datasources/datasources.yml` — a
  cross-repo contract; change them together or not at all.
- `trace.test.ts` — Vitest tests: default base URL, decoded left-pane
  structure (datasource uid, traceql query, range), short-id prefix.

## Run / test

From the repo root (`nexus-ui/`):

```bash
npm run test                    # all Vitest tests
npx vitest run src/lib          # only this directory
```

## Caution / do not modify

- Do not swap the order of `twMerge(clsx(...))` or remove `tailwind-merge`;
  callers throughout `src/components/` depend on later classes overriding
  earlier ones.
