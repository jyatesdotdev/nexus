import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TraceLink } from './TraceLink'
import { buildTraceUrl } from '../lib/trace'
import '@testing-library/jest-dom'

const TRACE_ID = 'deadbeefdeadbeefdeadbeefdeadbeef'

describe('TraceLink', () => {
  it('renders a chip with the short trace id linking to Grafana Tempo', () => {
    render(<TraceLink traceId={TRACE_ID} />)

    const link = screen.getByRole('link', { name: /trace deadbee/i })
    expect(link).toHaveAttribute('href', buildTraceUrl(TRACE_ID))
    // The full 32-char id belongs in the tooltip, not the visible label.
    expect(link).toHaveAttribute('title', expect.stringContaining(TRACE_ID))
  })

  it('opens in a new tab without leaking the opener window', () => {
    render(<TraceLink traceId={TRACE_ID} />)

    const link = screen.getByRole('link')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
