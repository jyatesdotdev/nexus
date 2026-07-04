# nexus-stack/templates — service scaffold templates

Source trees for `make new-agent` (see `../scripts/new-agent.sh`). Files here are **templates, not live code**: they contain placeholder tokens that the generator substitutes when copying a template to a new sibling service directory.

## Tokens

| Token | Meaning | Example (`NAME=stock-ticker`, `PORT=8002`) |
|---|---|---|
| `__SERVICE_NAME__` | Raw service name as given to `NAME=` (lowercase, hyphens allowed) | `stock-ticker` |
| `__SERVICE_SNAKE__` | Name with hyphens as underscores (Python identifiers, skill ids) | `stock_ticker` |
| `__SERVICE_UPPER__` | Uppercase snake (env-var prefix) | `STOCK_TICKER` |
| `__SERVICE_TITLE__` | PascalCase (class names, card name) | `StockTicker` |
| `__PORT__` | Host/container port | `8002` |
| `__DATE__` | Scaffold date (YYYY-MM-DD) | `2026-07-04` |

## Subdirectories

- `a2a-service/` — a complete A2A sub-agent service closely modeled on the real `../../nexus-a2a` weather agent (the canonical example): `server.py` (AgentExecutor with two-phase streaming, AgentCard whose `name` drives the orchestrator-side agent name, `/health` + telemetry via nexus-common, a pure `process_query()` domain function with the learner TODO), multi-stage non-root Dockerfile, pyproject.toml + requirements.txt mirror, respx-mocked test suite that passes out of the box, and per-directory docs (AGENTS.md, README.md, CHANGELOG.md, tests/AGENTS.md).

## Rules

- Every template `.py` and the Dockerfile must carry an `# EDUCATIONAL NOTE:` comment: templates live under `nexus-stack/**`, so the Semgrep educational-note rule in `../.semgrep.yaml` scans them like any other source (a deliberate choice — templates are example code learners read, and scaffolded copies must comply too). Template `tests/` are excluded by the existing `**/tests/**` exclusion.
- Template Python files must stay syntactically valid with the tokens in place (tokens are legal identifiers / appear inside strings), so tooling can parse them.
- If you change the template's structure or tokens, update `../scripts/new-agent.sh` (the substitution list and the printed next-steps checklist) in the same change, and keep it aligned with the real `nexus-a2a` service when that evolves.
