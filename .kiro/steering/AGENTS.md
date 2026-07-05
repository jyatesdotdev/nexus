# .kiro/steering

Three workspace-wide steering docs for the Nexus multi-agent learning lab. They are the
system-level counterpart to the per-directory AGENTS.md files: AGENTS.md files describe
the files at one level; these describe the whole system. Keep them consistent with
reality — when you change architecture, conventions, ports, or env vars, update the
matching doc here.

## Files at this level

- `product.md` — what Nexus is (educational multi-agent orchestration lab), the
  architecture overview, domain concepts (agent cards, generative UI, HITL,
  reviewer/critic pattern, loop detection, persistence backends, two-phase streaming),
  and the cross-cutting rules (EDUCATIONAL NOTE comments, mocked I/O in unit tests,
  Pydantic tool returns, README+AGENTS.md sync).
- `structure.md` — directory layout of the monorepo, file naming/location rules, and
  per-service coding patterns (orchestrator, MCP server, A2A agent, UI, nexus-common).
- `tech.md` — languages/versions (Python 3.14, TS ~5.9), dependency stack, code-quality
  rules, the command reference (uv workspace, make targets), Docker/port table, and the
  key environment variables table (`nexus-stack/.env.example` is the canonical env-var
  reference).

## Caution

- The frontmatter `inclusion: always` is Kiro IDE metadata; leave it in place.
- These docs are load-bearing for AI agents: stale claims here propagate into wrong
  changes elsewhere. If you find a contradiction between a steering doc and the code,
  the code is the truth — fix the doc.
