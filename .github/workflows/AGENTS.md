# .github/workflows

CI for the Nexus monorepo (dormant until the repo has a GitHub remote).

## Files at this level

- `ci.yml` — the single CI workflow, triggered on push to main and pull requests.
  Structure: a `changes` job (dorny/paths-filter) computes which services changed, and
  downstream jobs run only for those services. Jobs: Python services matrix
  (nexus-a2a / nexus-mcp / nexus-orchestrator: pip install from requirements.txt +
  `-e ./nexus-common`, then ruff + pytest; mypy is gated to nexus-mcp only — the only
  service that passes strict today, widen when others are fixed), nexus-common (ruff
  only), UI (npm ci / lint / vitest / build on Node 24), Semgrep (runs the standards
  rules from `nexus-stack/.semgrep.yaml` repo-wide), and an advisory soft-fail Checkov
  Dockerfile scan.

## Rules and gotchas

- CI installs Python deps from each service's `requirements.txt` (the hand-kept mirror
  of its pyproject) — NOT from the uv workspace. If you change deps, update both files
  or CI diverges from local.
- A change to `nexus-common/**` triggers all three Python service jobs (editable-dep
  coupling); the filters encode this.
- Deliberately excluded (comments in the yaml explain each): LLM evals (needs
  GEMINI_API_KEY secret + paid nondeterministic calls), nexus-integration tests and
  Playwright e2e (need the live docker stack).
- Python version is a quoted string ('3.14') — unquoted YAML floats truncate to 3.1.
- Validate edits with actionlint before committing if available.
