import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from './App'
import { buildTraceUrl } from './lib/trace'
import '@testing-library/jest-dom'

// Mock fetch
globalThis.fetch = vi.fn()

/**
 * EDUCATIONAL NOTE: Mocking a Streaming Response
 * WHY: sendRequest consumes response.body.getReader() chunk by chunk, so a
 * plain `json()` mock is not enough — we must fake the Web Streams reader.
 * HOW: A minimal reader that yields the whole SSE payload as one chunk,
 * then reports done. `headers` uses the real Headers class so
 * response.headers.get('X-Trace-Id') behaves exactly like the browser.
 */
function mockSseResponse(events: object[], headers: Record<string, string> = {}): Response {
  const payload = events.map((e) => `data: ${JSON.stringify(e)}\n`).join('\n')
  let delivered = false
  return {
    ok: true,
    headers: new Headers(headers),
    body: {
      getReader: () => ({
        read: async () => {
          if (delivered) return { done: true, value: undefined }
          delivered = true
          return { done: false, value: new TextEncoder().encode(payload) }
        }
      })
    }
  } as unknown as Response
}

const AGENT_EVENT = {
  author: 'nexus_orchestrator',
  partial: false,
  content: { parts: [{ text: 'Hi there' }] }
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Setup a default 'online' response for status check
    vi.mocked(fetch).mockImplementation(async (url) => {
      if (url.toString().includes('/system-status')) {
        return {
          ok: true,
          json: async () => ({
            orchestrator: 'Online',
            mcp_server: 'Online',
            mcp_db: 'Connected',
            a2a_agent: 'Online',
            a2a_api: 'Reachable'
          })
        } as unknown as Response
      }
      return { ok: true, body: null } as unknown as Response
    })
  })

  /**
   * Helper: waits for the app to come online, types a message, and sends it.
   */
  const sendMessage = async (text: string) => {
    await waitFor(() => {
      expect(screen.queryByPlaceholderText('Message Nexus...')).not.toBeDisabled()
    }, { timeout: 5000 })

    fireEvent.change(screen.getByPlaceholderText('Message Nexus...'), { target: { value: text } })
    fireEvent.click(screen.getByText('Send'))
  }

  it('renders correctly and shows online status', async () => {
    render(<App />)
    // Wait for the status check to complete and UI to update
    await waitFor(() => {
      const onlineBadges = screen.getAllByText('Online')
      expect(onlineBadges.length).toBeGreaterThanOrEqual(1)
    }, { timeout: 5000 })

    expect(screen.getByText('Nexus')).toBeInTheDocument()
  })

  it('allows entering text and clicking send', async () => {
    render(<App />)

    // Wait for app to be 'online' so input is enabled
    await waitFor(() => {
      expect(screen.queryByPlaceholderText('Message Nexus...')).not.toBeDisabled()
    }, { timeout: 5000 })

    const input = screen.getByPlaceholderText('Message Nexus...')
    fireEvent.change(input, { target: { value: 'Hello' } })
    expect(input).toHaveValue('Hello')

    const sendButton = screen.getByText('Send')
    fireEvent.click(sendButton)

    // Check if user message appears
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('renders a Tempo trace link when /run_sse returns an X-Trace-Id header', async () => {
    const traceId = 'abcdef0123456789abcdef0123456789'
    vi.mocked(fetch).mockImplementation(async (url) => {
      if (url.toString().includes('/system-status')) {
        return {
          ok: true,
          json: async () => ({
            orchestrator: 'Online',
            mcp_server: 'Online',
            mcp_db: 'Connected',
            a2a_agent: 'Online',
            a2a_api: 'Reachable'
          })
        } as unknown as Response
      }
      return mockSseResponse([AGENT_EVENT], { 'X-Trace-Id': traceId })
    })

    render(<App />)
    await sendMessage('Hello')

    // The agent reply streams in, carrying the trace chip.
    await waitFor(() => {
      expect(screen.getByText('Hi there')).toBeInTheDocument()
    })
    const link = screen.getByRole('link', { name: /trace abcdef0/i })
    expect(link).toHaveAttribute('href', buildTraceUrl(traceId))
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('renders no trace link when the X-Trace-Id header is absent', async () => {
    vi.mocked(fetch).mockImplementation(async (url) => {
      if (url.toString().includes('/system-status')) {
        return {
          ok: true,
          json: async () => ({
            orchestrator: 'Online',
            mcp_server: 'Online',
            mcp_db: 'Connected',
            a2a_agent: 'Online',
            a2a_api: 'Reachable'
          })
        } as unknown as Response
      }
      return mockSseResponse([AGENT_EVENT])
    })

    render(<App />)
    await sendMessage('Hello')

    await waitFor(() => {
      expect(screen.getByText('Hi there')).toBeInTheDocument()
    })
    expect(screen.queryByRole('link', { name: /trace/i })).not.toBeInTheDocument()
  })
})
