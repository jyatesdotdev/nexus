/**
 * EDUCATIONAL NOTE: Trace Deep Links (UI -> Grafana Tempo)
 * WHY: The whole point of Nexus is making agent-to-agent communication
 * visible. The orchestrator returns the OpenTelemetry trace id of each
 * /run_sse request in an `X-Trace-Id` response header, and this module turns
 * that id into a Grafana Explore URL so a user can jump from a chat message
 * straight to the distributed trace (orchestrator -> MCP/A2A sub-agents).
 * HOW: Grafana's /explore view accepts a URL-encoded JSON "left" pane
 * describing the datasource and queries. We target the Tempo datasource
 * provisioned in nexus-dev-infra (uid "Tempo", see
 * nexus-dev-infra/grafana/provisioning/datasources/datasources.yml) with a
 * TraceQL query that is simply the trace id — Tempo treats a bare trace id
 * as a trace lookup.
 */

/**
 * The Tempo datasource uid provisioned by nexus-dev-infra's Grafana.
 * Contract: must match `uid: Tempo` in
 * nexus-dev-infra/grafana/provisioning/datasources/datasources.yml.
 */
export const TEMPO_DATASOURCE_UID = 'Tempo'

/**
 * Grafana base URL. Like every other env var in this app it is read via
 * import.meta.env, so Vite inlines it at BUILD time.
 * Default matches the Grafana port published by nexus-dev-infra.
 */
export function getGrafanaBaseUrl(): string {
  const base: string = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3000'
  // Strip a trailing slash so we never produce "//explore".
  return base.replace(/\/$/, '')
}

/**
 * Builds a Grafana Explore deep link that opens the given OTel trace id
 * (32-char hex) in the Tempo datasource.
 */
export function buildTraceUrl(traceId: string): string {
  const leftPane = {
    datasource: TEMPO_DATASOURCE_UID,
    queries: [
      {
        refId: 'A',
        datasource: { type: 'tempo', uid: TEMPO_DATASOURCE_UID },
        queryType: 'traceql',
        query: traceId
      }
    ],
    range: { from: 'now-1h', to: 'now' }
  }
  return `${getGrafanaBaseUrl()}/explore?orgId=1&left=${encodeURIComponent(JSON.stringify(leftPane))}`
}

/**
 * Short display form of a trace id (like a git short hash) for the chat chip.
 */
export function shortTraceId(traceId: string): string {
  return traceId.slice(0, 7)
}
