# nexus-dev-infra/grafana

Grafana provisioning files for the Nexus observability stack. The `grafana` service in
`../docker-compose.yml` bind-mounts these directories into the official Grafana container
so that datasources and dashboards exist automatically on first start — nobody configures
Grafana by hand. Grafana runs at http://localhost:3000 (user `admin`, password `admin`)
once the parent compose stack is up.

## Layout and files

- `provisioning/datasources/datasources.yml` — mounted at
  `/etc/grafana/provisioning/datasources`. Declares two datasources:
  - `Prometheus` at `http://prometheus:9090` (the default datasource), with a derived
    field that links log/metric values to Tempo traces.
  - `Tempo` at `http://tempo:3200`, with the fixed `uid: Tempo`. The Prometheus derived
    field references `datasourceUid: Tempo`, so do not change that uid without updating
    the reference. The URLs use Docker DNS names of services in `../docker-compose.yml`;
    they must stay in sync with those service names.

- `provisioning/dashboards/nexus.yml` — mounted at
  `/etc/grafana/provisioning/dashboards`. A file provider that loads every JSON file found
  at `/etc/grafana/dashboards` inside the container, which is a mount of `../dashboards`
  (the `dashboards/` directory next to `provisioning/`). Drop a new dashboard JSON into
  `dashboards/` and restart the grafana container to add a dashboard.

- `dashboards/nexus-overview.json` — "Nexus System Overview" dashboard: request rate and
  average response latency panels. These panels query the Prometheus metrics
  `nexus_http_requests_total` and `nexus_http_request_duration_seconds`, which are emitted
  by the shared `nexus-common` library in every Python service. If those metric names or
  their labels (`method`, `endpoint`, `status`, `service`) change in
  `nexus-common/nexus_common/telemetry.py`, these panels go blank.

- `dashboards/tempo-health.json` — "Tempo Tracing Health" dashboard: Tempo ingestion rate,
  a global request rate derived from trace span metrics, and a trace search/visualization
  panel. Depends on Tempo's metrics_generator processors (`span-metrics`, etc.) enabled in
  `../tempo.yaml`.

## Editing dashboards

The practical workflow is: edit the dashboard in the Grafana UI, use Share > Export to get
JSON, and save it over the file here (the provider sets `editable: true` and
`disableDeletion: false`, but UI edits are not written back to these files — persist them
by exporting). Keep datasource references pointing at the provisioned names/uids
(`Prometheus`, `Tempo`).
