import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from './App'
import '@testing-library/jest-dom'

// Mock fetch
globalThis.fetch = vi.fn()

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
        } as any
      }
      return { ok: true, body: null } as any
    })
  })

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
})
