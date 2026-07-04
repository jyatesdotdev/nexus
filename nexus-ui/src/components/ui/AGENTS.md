# nexus-ui/src/components/ui

Reusable UI primitives for nexus-ui, the React frontend of the Nexus
multi-agent system. These are small, dependency-free wrappers over native HTML
elements styled with Tailwind CSS v4. They exist so the feature components in
the parent directory (chat, status grid) stay visually consistent. Every
primitive accepts a `className` prop merged via the `cn()` helper from
`src/lib/utils.ts` (clsx + tailwind-merge), so callers can override individual
Tailwind utilities without class conflicts. All other native props are passed
through via `...props` spread.

Convention: import these through the barrel, e.g.
`import { Button, Card, Badge, Input } from './ui'` (from `src/components`) —
not from the individual files.

## Files at this level

- `index.ts` — barrel file re-exporting Card, Badge, Button, Input. Add any
  new primitive here or it will not be picked up by existing import sites.
- `Button.tsx` — button with `variant: 'primary' | 'ghost'` (default primary,
  an indigo/violet gradient) and an `isLoading` prop. When `isLoading` is
  true, the button disables itself and replaces its children with a spinner
  plus the literal text "Thinking" — `Button.test.tsx` asserts on that exact
  text. `disabled` is honored in addition to `isLoading`.
- `Button.test.tsx` — Vitest tests for Button.
- `Card.tsx` — translucent dark-slate rounded container with backdrop blur;
  the structural wrapper for the chat panel and status cards. No variants;
  customize via `className`.
- `Card.test.tsx` — Vitest tests for Card.
- `Badge.tsx` — status pill with `variant: 'success' | 'error' | 'neutral'`
  (default neutral). Used by SystemStatusGrid for Online/Offline labels:
  success is emerald, error is rose.
- `Badge.test.tsx` — Vitest tests for Badge.
- `Input.tsx` — styled native text input (dark background, indigo focus
  border). A plain controlled input: pass `value` and `onChange` from the
  parent.
- `Input.test.tsx` — Vitest tests for Input.

## Run / test

From the repo root (`nexus-ui/`):

```bash
npm run test                            # all Vitest tests
npx vitest run src/components/ui        # only this directory
```

## Caution / do not modify

- Do not remove the `cn(...)` merge or reorder it so the caller's `className`
  loses; caller overrides winning is the point of these primitives.
- The "Thinking" loading label in Button is asserted against in tests; change
  it only together with those tests.
- Keep new primitives exported from `index.ts` and follow the same
  props-spread + `cn()` pattern.
