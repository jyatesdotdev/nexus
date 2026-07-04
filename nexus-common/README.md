# Nexus Common SDK

Shared utilities and foundational logic for the Nexus Multi-Agent Learning Lab.

## Features
- **Telemetry**: Standardized OpenTelemetry setup for FastAPI and Starlette.
- **Auth**: Standardized `IdentityContext` for propagation across agents.

## Installation
For local development this package is a member of the uv workspace at the
repository root — `uv sync` there installs it editable into the shared `.venv`
for every service automatically.

The Docker images (and CI) still install it in editable mode via each
service's requirements.txt:
```bash
pip install -e ../nexus-common
```

The package ships a `py.typed` marker (PEP 561), so consumers' mypy runs see
its real types.
