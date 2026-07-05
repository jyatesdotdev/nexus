# nexus-dev-infra

This directory holds the local infrastructure and observability stack for the Nexus
multi-agent learning lab: Postgres, Redis, Grafana Tempo (traces), Prometheus (metrics),
Grafana (dashboards), and an OpenTelemetry Collector, all defined in one docker-compose
file. The application services (orchestrator, MCP server, A2A agent, frontend) live in a
separate compose file in `../nexus-stack` and join the same external Docker network,
`nexus-net`, so containers from both stacks resolve each other by service name. This stack
is normally started indirectly by `make up` in `../nexus-stack`, which runs
`docker compose up -d` here first. This directory is part of the single workspace-root git repository.

Telemetry flow: application services send OTLP/HTTP to `otel-collector:4319` (set via
`OTEL_EXPORTER_OTLP_ENDPOINT` in `nexus-stack/docker-compose.yml`); the collector forwards
traces to `tempo:4317` and metrics to Prometheus's OTLP endpoint. Prometheus additionally
scrapes each service's `/metrics` endpoint (exposed by the shared `nexus-common` library).
Grafana is pre-provisioned with both datasources and two dashboards.

## Files at this level

- `docker-compose.yml` — defines six services on the external `nexus-net` network:
  - `postgres` (postgres:15-alpine, host port 5432, user `nexus` / password `password` /
    db `nexus_dev`, persistent volume `postgres_data`). The orchestrator's Postgres
    persistence backend and `nexus-integration/test_persistence_integration.py` hardcode
    these credentials as defaults — change them here and you must change them there.
  - `redis` (host port 6379) — orchestrator session/memory backend.
  - `tempo` (grafana/tempo:2.10.1, ports 3200 UI/API, 4317 OTLP gRPC, 4318 OTLP HTTP),
    configured by `tempo.yaml`.
  - `prometheus` (host port 9090), configured by `prometheus.yml`; started with
    `--web.enable-otlp-receiver` so the OTel collector can push metrics to it.
  - `grafana` (host port 3000, admin password `admin`), auto-provisioned from `grafana/`.
  - `otel-collector` (otel/opentelemetry-collector-contrib, host port 4319), configured by
    `otel-collector-config.yaml`.
  The network is declared `external: true`: it must already exist
  (`docker network create nexus-net`; `make up` in nexus-stack does this for you).
- `prometheus.yml` — scrape config, 5s interval. Scrape targets `orchestrator:8080`,
  `mcp-server:8000`, `a2a-agent:8001` are Docker DNS names that must exactly match the
  service names and container ports in `nexus-stack/docker-compose.yml`. Also scrapes
  itself and `tempo:3200`. Add a scrape target here whenever a new service is added to the
  stack.
- `tempo.yaml` — Tempo single-binary config: local storage under /tmp/tempo, OTLP
  receivers on 4317 (gRPC) and 4318 (HTTP), 1h block retention, memberlist coordination,
  and a metrics_generator with `service-graphs`, `span-metrics`, and `local-blocks`
  processors (the `local-blocks` processor and its `traces_storage` path are required for
  TraceQL metrics queries; the memberlist block avoids "empty ring" errors — do not remove
  either).
- `otel-collector-config.yaml` — receives OTLP/HTTP on 0.0.0.0:4319 with CORS allowed for
  `http://localhost:5173` and `http://localhost:80` (the browser UI sends telemetry
  directly to this port, so the CORS list must include the frontend origin). A
  `transform/ui` processor rewrites `service.name` from `unknown_service` to `nexus-ui`,
  working around a browser OTel SDK resource-propagation bug. Exports traces to
  `tempo:4317` and metrics to `http://prometheus:9090/api/v1/otlp`, plus a verbose `debug`
  exporter on both pipelines.
- `README.md` — human-facing quickstart. Its second half documents running local MLX
  models via Docker Model Runner on macOS; note the DMR API at `localhost:8000` collides
  with the MCP server's host port 8000 if both run at once.
- `grafana/` — datasource and dashboard provisioning; see `grafana/AGENTS.md`.

## How to run

```bash
docker network create nexus-net   # only if it does not exist yet
cd <workspace-root>/nexus-dev-infra
docker compose up -d
docker compose ps                 # all services should become healthy
docker compose down               # stop (postgres/prometheus data persist in volumes)
```

Endpoints once up: Grafana http://localhost:3000 (admin/admin), Prometheus
http://localhost:9090, Tempo http://localhost:3200, Postgres localhost:5432,
Redis localhost:6379, OTLP intake http://localhost:4319 (collector) and 4317/4318 (Tempo
direct).

## Caution / do not modify

- Service names (`postgres`, `redis`, `tempo`, `prometheus`, `grafana`, `otel-collector`)
  are DNS names referenced by `nexus-stack/docker-compose.yml` environment variables,
  by `prometheus.yml`, by `otel-collector-config.yaml`, by
  `grafana/provisioning/datasources/datasources.yml`, and by the integration tests.
  Renaming any of them breaks cross-stack wiring.
- Host ports 3000, 3200, 4317, 4318, 4319, 5432, 6379, 9090 are assumed by the app stack,
  tests, and docs. The collector's 4319 in particular is baked into
  `OTEL_EXPORTER_OTLP_ENDPOINT` in nexus-stack.
- Postgres credentials (`nexus`/`password`/`nexus_dev`) are duplicated in
  nexus-stack's orchestrator env and in nexus-integration's test defaults.
- Do not remove `external: true` from the network block; making the network non-external
  would isolate this stack from the application containers.
