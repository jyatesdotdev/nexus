# nexus-dev-infra/grafana/provisioning/datasources

Grafana datasource provisioning. One file:

- `datasources.yml` — defines the Prometheus datasource (`http://prometheus:9090`) and
  the Tempo datasource (`http://tempo:3200`) by their compose service names on the
  `nexus-net` network.

## Caution — cross-service contract

The Tempo datasource `uid: Tempo` is load-bearing outside this repo: the chat UI builds
per-message trace deep-links against it (`nexus-ui/src/lib/trace.ts`,
`TEMPO_DATASOURCE_UID = 'Tempo'`), and `nexus-stack/scripts/demo.sh` prints links in the
same format. If you change the uid here, update those consumers or every trace link in
the product silently breaks (Grafana shows "datasource not found").
