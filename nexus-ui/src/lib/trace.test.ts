/**
 * EDUCATIONAL NOTE: Testing URL Builders
 * WHY: The Grafana Explore link is a contract with an external tool. Rather
 * than eyeballing an encoded blob, we decode the URL back into JSON and
 * assert on its structure — this keeps the test readable and resilient to
 * key ordering.
 */
import { describe, it, expect } from 'vitest'
import { buildTraceUrl, shortTraceId, TEMPO_DATASOURCE_UID } from './trace'

const TRACE_ID = 'abcdef0123456789abcdef0123456789'

describe('buildTraceUrl', () => {
  it('targets the default Grafana base URL and /explore path', () => {
    // VITE_GRAFANA_URL is unset in unit tests, so the default applies.
    const url = buildTraceUrl(TRACE_ID)
    expect(url.startsWith('http://localhost:3000/explore?orgId=1&left=')).toBe(true)
  })

  it('encodes a Tempo traceql query for the provisioned datasource uid', () => {
    const url = buildTraceUrl(TRACE_ID)
    const left = new URL(url).searchParams.get('left')
    expect(left).not.toBeNull()

    const pane = JSON.parse(left!)
    expect(pane.datasource).toBe(TEMPO_DATASOURCE_UID)
    expect(pane.queries).toHaveLength(1)
    expect(pane.queries[0]).toMatchObject({
      queryType: 'traceql',
      query: TRACE_ID,
      datasource: { type: 'tempo', uid: TEMPO_DATASOURCE_UID }
    })
    expect(pane.range).toEqual({ from: 'now-1h', to: 'now' })
  })
})

describe('shortTraceId', () => {
  it('returns a 7-character prefix', () => {
    expect(shortTraceId(TRACE_ID)).toBe('abcdef0')
  })
})
