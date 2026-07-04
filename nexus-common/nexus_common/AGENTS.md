# nexus_common (package source)

This is the importable `nexus_common` Python package — the shared SDK for the Nexus
multi-agent learning lab. Every Python service in the system (the Google ADK orchestrator
in `nexus-orchestrator`, the A2A weather agent in `nexus-a2a`, the MCP HR server in
`nexus-mcp`) calls into this package to get a `/health` endpoint, OpenTelemetry tracing,
Prometheus metrics, and mock identity propagation. Because three services share this code,
any signature or behavior change here must be checked against all of them.

## Files at this level

- `__init__.py` — public API surface. Re-exports `setup_telemetry`, `IdentityContext`,
  `verify_token`, `bootstrap_starlette_service`, `bootstrap_fastapi_service`. Services
  import from `nexus_common` directly, so keep these names stable.

- `service.py` — one-call bootstrap for a service. `bootstrap_fastapi_service(service_name,
  app)` (used by the orchestrator) and `bootstrap_starlette_service(service_name, app)`
  (used by the A2A and MCP servers) each register a `GET /health` route returning
  `{"status": "ok"}` and then call `setup_telemetry`. Invariant: every Nexus service must
  expose `/health`, because Docker healthchecks in `nexus-stack/docker-compose.yml` and the
  orchestrator's `/system-status` endpoint probe it. The `service_name` argument becomes the
  `service` label on metrics and the OTel `service.name` — it should match the compose
  service name (`orchestrator`, `mcp-server` uses `mcp-server`, A2A uses `a2a-agent`).

- `telemetry.py` — `setup_telemetry(service_name, app=None, app_type="fastapi")` does three
  things: (1) if `OTEL_EXPORTER_OTLP_ENDPOINT` is set, configures an OTLP HTTP trace
  exporter with W3C TraceContext + Baggage propagation (traces land in Tempo via the OTel
  collector in `nexus-dev-infra`); (2) defines two Prometheus metrics; (3) instruments the
  app (middleware + `/metrics` route) and httpx clients. Gotchas and invariants:
  - Metric names are load-bearing: `nexus_http_requests_total` (Counter; labels `method`,
    `endpoint`, `status`, `service`) and `nexus_http_request_duration_seconds` (Histogram;
    labels `method`, `endpoint`, `service`). The Grafana dashboards in
    `nexus-dev-infra/grafana/dashboards/` query these names. Do not rename or relabel.
  - The Starlette path uses a raw ASGI middleware class, NOT `BaseHTTPMiddleware`, on
    purpose: `BaseHTTPMiddleware` buffers/breaks SSE streaming responses, which both the
    MCP server (SSE transport) and A2A agent rely on. Do not "simplify" it back.
  - The Starlette middleware skips recording for `/metrics` and `/health`; the FastAPI
    middleware currently records all paths (a known asymmetry).
  - `PROMETHEUS_MULTIPROC_DIR`, if set, switches to prometheus_client multiprocess mode so
    metrics aggregate across gunicorn workers (the orchestrator runs under gunicorn).
  - All framework imports are lazy (inside the function) and the whole body is wrapped in
    try/except: missing OTel packages degrade to a logged warning, not a crash.
  - Calling `setup_telemetry` twice in one process will raise a duplicate-metric error from
    prometheus_client; call it once per process (the bootstrap functions do this for you).

- `auth.py` — mock identity propagation. `IdentityContext(auth_header)` parses an
  `Authorization: Bearer <token>` header; if the token looks like a JWT (contains dots) the
  middle segment is used verbatim as `user_id` (no base64 decoding, no signature check —
  this is intentional for the lab; a token like `header.mock_user_123.sig` yields user_id
  `mock_user_123`). Otherwise the whole token is the user_id; no header means `anonymous`.
  `get_auth_header()` returns the header dict for forwarding to downstream agents — this is
  how identity flows orchestrator -> A2A/MCP. `verify_token(token)` only checks shape
  (exactly two dots, starts with `eyJ`). None of this is real security; do not present it
  as such, and do not add real JWT verification without updating every service that mints
  mock tokens.

## Testing

This package has no tests of its own. Behavior is covered by the consuming services' unit
tests and by `nexus-integration/`. Convention: every file here must keep at least one
`# EDUCATIONAL NOTE:` comment (Semgrep-enforced workspace-wide).
