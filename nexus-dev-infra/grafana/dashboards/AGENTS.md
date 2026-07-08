# nexus-dev-infra/grafana/dashboards

Dashboard JSON definitions, auto-loaded by the file provider in
`../provisioning/dashboards/nexus.yml`. Edit workflow: export the JSON from Grafana's UI
(or edit by hand), save here, restart the Grafana container.

## Files at this level

- `nexus-overview.json` — service health/traffic overview built on the Prometheus
  datasource; panels query the `nexus_http_requests_total` /
  `nexus_http_request_duration_seconds` metrics that every service emits via
  nexus-common. Labels: `method`, `endpoint`, `service` on both metrics; the
  `nexus_http_requests_total` counter additionally carries a `status` label (the
  latency histogram does not — grouping a latency panel by `status` returns nothing).
- `tempo-health.json` — trace-oriented dashboard against the Tempo datasource.

## Caution

Panel queries depend on the metric names and label sets defined in
`nexus-common/nexus_common/telemetry.py` and on Prometheus scrape targets in
`../../prometheus.yml` (which key off compose service names). Renaming a metric, label,
or service breaks panels silently — check these dashboards when touching those.
