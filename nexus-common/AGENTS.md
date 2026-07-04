# nexus-common

This directory is a small shared Python library ("Nexus Common SDK") used by the Python
services in the Nexus multi-agent learning lab. Nexus is a system of independently
deployable services: an orchestrator "root agent" (`nexus-orchestrator`, Google ADK +
FastAPI) that delegates to a weather sub-agent over the A2A protocol (`nexus-a2a`) and an
HR directory server over MCP (`nexus-mcp`), with a React frontend (`nexus-ui`). All three
Python services import this package to get identical telemetry, health-check, and
identity-propagation behavior, so a change here affects every service at once.

The importable package is `nexus_common` (underscore); the distribution name is
`nexus-common` (hyphen). For local development this is a uv-workspace member: each
service's pyproject declares `nexus-common` with `[tool.uv.sources] nexus-common =
{ workspace = true }`, so `uv sync` at the workspace root installs it editable into the
shared `.venv`. The Docker images still install it editable via each service's
requirements.txt (`-e ../nexus-common`), and the docker-compose file in `../nexus-stack`
bind-mounts this directory into each service container at `/nexus-common`. This directory
is part of the single workspace-root git repository.

## Files at this level

- `pyproject.toml` — hatchling packaging metadata (switched from setuptools 2026-07-04:
  hatchling's editable installs use a plain `.pth` path that mypy can follow, which the
  `py.typed` marker needs). Distribution `nexus-common`, version 0.1.0, requires
  Python >= 3.14 (matching the services and Dockerfiles). Dependencies are OpenTelemetry
  (API, SDK, OTLP exporter, Prometheus exporter, httpx/FastAPI/Starlette instrumentation)
  and `prometheus_client`. Note that `fastapi`, `starlette`, `redis`, etc. are
  deliberately NOT dependencies: the library imports them lazily inside functions and
  assumes the consuming service already has whichever framework it uses. Do not add heavy
  framework dependencies here. Also carries ruff (py314) and mypy strict config; both run
  clean.
- `README.md` — short human-facing description and the install story.
- `nexus_common/` — the actual package source, including `py.typed` (empty PEP 561
  marker, added 2026-07-04: consumers' strict mypy runs now follow this package's real
  types instead of treating it as untyped — nexus-mcp's old `ignore_missing_imports`
  override for `nexus_common.*` was removed on the back of it; do not delete the marker).
  See `nexus_common/AGENTS.md` for details on each module and the invariants (metric
  names, health-check contract, mock JWT format).

## How to work with it

There is no test suite inside this directory. Changes are validated indirectly through
the consuming services' test suites (`nexus-orchestrator/tests/`, `nexus-mcp/tests/`,
`nexus-a2a/tests/`) and the integration tests in `../nexus-integration`. After editing,
a reasonable smoke check is:

```bash
cd /Users/jyates/Repositories/nexus
uv run --project nexus-orchestrator pytest nexus-orchestrator/tests/
cd nexus-common && uv run mypy . && uv run ruff check .
```

Editable installs pick up source changes automatically; no reinstall is needed unless
`pyproject.toml` itself changes.

Project convention: every Python source file in the Nexus workspace must contain at least
one `# EDUCATIONAL NOTE:` comment explaining a non-obvious design choice (enforced by
Semgrep via `nexus-stack/.semgrep.yaml`). Keep existing notes and add one to any new file.

## Caution / do not modify

- Do not rename the public API re-exported from `nexus_common/__init__.py`
  (`setup_telemetry`, `IdentityContext`, `verify_token`, `bootstrap_starlette_service`,
  `bootstrap_fastapi_service`) — all services import these names.
- Do not change the Prometheus metric names or label sets (see `nexus_common/AGENTS.md`);
  Grafana dashboards in `../nexus-dev-infra` query them.
- Do not delete `nexus_common/py.typed`: nexus-mcp's strict mypy gate relies on it.
- Backwards compatibility matters more than usual here: this package is mounted into
  running containers, so a breaking change silently breaks three services.
