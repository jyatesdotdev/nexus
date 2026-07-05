# nexus-dev-infra/grafana/provisioning

Grafana provisioning config, bind-mounted into the Grafana container at
`/etc/grafana/provisioning` by `../../docker-compose.yml`. Grafana reads this tree at
startup to auto-configure datasources and dashboards — no clicking around the UI, and
changes here require a Grafana container restart to apply.

Subdirectories: `datasources/` (Prometheus + Tempo connections — see its AGENTS.md; the
Tempo datasource uid is a cross-service contract) and `dashboards/` (the file provider
that loads dashboard JSON from `../dashboards`).
