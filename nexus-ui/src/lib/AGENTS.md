# nexus-ui/src/lib

Small shared utilities for nexus-ui, the React frontend of the Nexus
multi-agent system. Currently this directory contains exactly one utility, the
`cn()` class-name helper, which every UI primitive in `src/components/ui/` and
several feature components use for Tailwind class composition. If you add
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
