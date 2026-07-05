# nexus-dev-infra/grafana/provisioning/dashboards

Dashboard *provider* config (not the dashboards themselves). One file:

- `nexus.yml` — a file-based provider telling Grafana to load every dashboard JSON found
  in the container path that `../../dashboards/` is mounted at. To add a dashboard, drop
  its JSON in `../../dashboards/` — this file normally never changes.
