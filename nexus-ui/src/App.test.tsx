/**
 * EDUCATIONAL: Complex Application Testing
 * WHY: The App component ties everything together. It involves asynchronous operations,
 * timers, and complex mock setup. This file demonstrates advanced testing patterns.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import App from './App'
import '@testing-library/jest-dom'

/**
 * WHY: We don't want to make actual network requests during tests (they are slow, 
 * flaky, and require a backend to be running).
 * HOW: `globalThis.fetch = vi.fn()` replaces the native browser `fetch` API 
 * with a Vitest spy function globally. We can control what this spy returns in each test.
 */
// Mock fetch
globalThis.fetch = vi.fn()

describe('App', () => {
  // `beforeEach` runs before EVERY `it` block in this describe suite.
  beforeEach(() => {
    // WHY: We clear mock history before each test so that assertions (like 
    // `toHaveBeenCalledTimes`) aren't polluted by previous tests.
    vi.clearAllMocks()
  })

  // `afterEach` runs after EVERY `it` block.
  afterEach(() => {
    // WHY: If a test uses fake timers, we must reset to real timers afterward 
    // to avoid breaking other tests that depend on standard timing.
    vi.useRealTimers()
  })

  // A helper function to quickly set up a successful "online" fetch response.
  const mockOnlineStatus = () => {
    // `mockResolvedValueOnce` tells our mocked fetch what to return the NEXT time it is called.
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        orchestrator: 'Online',
        mcp_server: 'Online',
        a2a_agent: 'Online'
      })
    })
  }

  it('correctly handles streaming SSE without duplication', async () => {
    mockOnlineStatus()

    // Mock SSE response for chat
    const sseData = [
      'data: {"partial": true, "author": "agent", "content": {"parts": [{"text": "Hello"}]}}\n\n',
      'data: {"partial": true, "author": "agent", "content": {"parts": [{"text": " World"}]}}\n\n',
      'data: {"partial": false, "author": "agent", "content": {"parts": [{"text": "Hello World"}]}}\n\n'
    ]

    // HOW: We simulate Server-Sent Events by constructing a standard `ReadableStream` 
    // and passing it as the body of our mocked fetch response.
    const stream = new ReadableStream({
      start(controller) {
        sseData.forEach(chunk => controller.enqueue(new TextEncoder().encode(chunk)))
        controller.close()
      }
    })

    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      body: stream
    })

    render(<App />)

    // `waitFor` is crucial for async tests. It repeatedly evaluates the callback 
    // until it doesn't throw an error or it times out. 
    // WHY: React components take time to render after fetching data.
    // Wait for status to be "Online"
    await waitFor(() => expect(screen.getAllByText('Online').length).toBe(3))

    const input = screen.getByPlaceholderText('Message orchestrator...')
    const button = screen.getByText('Send')

    // `fireEvent.change` simulates a user typing into an input field.
    fireEvent.change(input, { target: { value: 'hi' } })
    fireEvent.click(button)

    // `findByText` is a shortcut for `waitFor(() => screen.getByText(...))`.
    // It's the best way to wait for an element to appear asynchronously.
    const messageElement = await screen.findByText('Hello World')
    expect(messageElement).toBeInTheDocument()
    
    // `queryAllByText` is used instead of `getAllByText` when we want to check 
    // that something appears exactly X times, or doesn't appear at all. 
    // `getBy...` throws an error if it finds nothing, but `queryBy...` returns an empty array or null.
    const allMessages = screen.queryAllByText('Hello World')
    expect(allMessages.length).toBe(1)
  })

  it('displays delegation indicator only once when transferToAgent is repeated', async () => {
    mockOnlineStatus()

    // SSE with repeated delegation in multiple chunks
    const sseData = [
      'data: {"partial": true, "author": "root_agent", "actions": {"transferToAgent": "mcp_agent"}}\n\n',
      'data: {"partial": true, "author": "root_agent", "actions": {"transferToAgent": "mcp_agent"}}\n\n',
      'data: {"partial": false, "author": "mcp_agent", "content": {"parts": [{"text": "Agent response"}]}}\n\n'
    ]

    const stream = new ReadableStream({
      start(controller) {
        sseData.forEach(chunk => controller.enqueue(new TextEncoder().encode(chunk)))
        controller.close()
      }
    })

    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      body: stream
    })

    render(<App />)

    await waitFor(() => expect(screen.getAllByText('Online').length).toBe(3))

    const input = screen.getByPlaceholderText('Message orchestrator...')
    const button = screen.getByText('Send')

    fireEvent.change(input, { target: { value: 'quote' } })
    fireEvent.click(button)

    // Wait for system message (using regex for flexible matching)
    await screen.findByText(/Delegating to mcp_agent.../i)
    
    // Ensure only ONE delegation message exists
    const allDelegations = screen.queryAllByText(/Delegating to mcp_agent.../i)
    expect(allDelegations.length).toBe(1)
    
    // Should see agent response
    const agentMsg = await screen.findByText('Agent response')
    expect(agentMsg).toBeInTheDocument()
  })

  it('handles system status fetch failure', async () => {
    /**
     * WHY: We need to ensure the UI gracefully handles backend failures. 
     * If the status check fails, the services should be marked as "Offline".
     * HOW: We mock fetch to reject (simulate network error), then verify that the Offline badges appear.
     */
    ;(fetch as any).mockRejectedValueOnce(new Error('Network error'))
    
    render(<App />)

    // Wait for statuses to be "Offline"
    await waitFor(() => expect(screen.getAllByText('Offline').length).toBe(5))
  })

  it('handles system status fetch non-ok response', async () => {
    /**
     * WHY: Coverage for line 79 where throw new Error('Failed to fetch status') is called.
     * HOW: We mock a resolved fetch response where `ok` is false.
     */
    ;(fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500
    })
    
    render(<App />)

    // Should still result in Offline status
    await waitFor(() => expect(screen.getAllByText('Offline').length).toBe(5))
  })

  it('polls for system status every 5 seconds', async () => {
    /**
     * WHY: The dashboard should reflect real-time changes in service availability. 
     * HOW: We use Vitest fake timers to simulate the passage of time and 
     * verify that fetch is called repeatedly.
     */
    // `useFakeTimers` replaces global time functions (setTimeout, setInterval) with mocks.
    vi.useFakeTimers({ shouldAdvanceTime: true })
    mockOnlineStatus() // Initial call on mount
    mockOnlineStatus() // Second call after 5s
    
    render(<App />)
    
    // The initial checkStatus is called in useEffect
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1))
    
    // Fast-forward 5 seconds in simulation time.
    // `act` ensures that all React state updates resulting from the timer are processed 
    // before we make assertions.
    act(() => {
      vi.advanceTimersByTime(5000)
    })
    
    // The second call should be triggered by the interval
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2))
  })

  it('handles fetch error in handleSubmit', async () => {
    /**
     * WHY: Users should be notified if their message couldn't be sent. 
     * HOW: We mock the chat fetch call to fail and check for the error message in the chat.
     */
    mockOnlineStatus() // For initial status check
    ;(fetch as any).mockRejectedValueOnce(new Error('Chat failed'))

    render(<App />)

    // Wait for status to be "Online"
    await waitFor(() => expect(screen.getAllByText('Online').length).toBe(3))

    const input = screen.getByPlaceholderText('Message orchestrator...')
    const button = screen.getByText('Send')

    fireEvent.change(input, { target: { value: 'hi' } })
    fireEvent.click(button)

    const errorMsg = await screen.findByText(/Sorry, I encountered an error connecting to the orchestrator/i)
    expect(errorMsg).toBeInTheDocument()
  })

  it('sets status to Offline if response is not ok', async () => {
    // Mock the status endpoint to return a 500
    ;(fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500
    })

    render(<App />)

    // Wait for the status to be evaluated and set to "Offline"
    await waitFor(() => expect(screen.getAllByText('Offline').length).toBe(5))
  })

  it('handles JSON parse error in SSE stream', async () => {
    mockOnlineStatus()

    // Send malformed JSON to trigger the catch block in the SSE parser
    const sseData = [
      'data: {malformed_json: true}\n\n',
      'data: {"partial": false, "author": "agent", "content": {"parts": [{"text": "Hello World"}]}}\n\n'
    ]

    const stream = new ReadableStream({
      start(controller) {
        sseData.forEach(chunk => controller.enqueue(new TextEncoder().encode(chunk)))
        controller.close()
      }
    })

    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      body: stream
    })

    // Capture console.error using a spy so it doesn't clutter our test output
    // and so we can verify it was called.
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(<App />)

    await waitFor(() => expect(screen.getAllByText('Online').length).toBe(3))

    const input = screen.getByPlaceholderText('Message orchestrator...')
    const button = screen.getByText('Send')

    fireEvent.change(input, { target: { value: 'hi' } })
    fireEvent.click(button)

    // Wait for the valid message to be rendered
    const messageElement = await screen.findByText('Hello World')
    expect(messageElement).toBeInTheDocument()

    // Verify console.error was called for the malformed JSON
    expect(consoleSpy).toHaveBeenCalledWith('Error parsing SSE line', expect.any(Error))

    // Restore the original console.error function
    consoleSpy.mockRestore()
  })

  it('does not send if input is empty or loading', async () => {
    mockOnlineStatus()
    render(<App />)

    await waitFor(() => expect(screen.getAllByText('Online').length).toBe(3))
    
    // Clear fetch mocks so we can count calls strictly from handleSubmit
    ;(fetch as any).mockClear()

    const button = screen.getByText('Send')
    fireEvent.click(button) // Input is empty

    expect(fetch).not.toHaveBeenCalled()
  })

  it('handles missing response body from orchestrator', async () => {
    mockOnlineStatus()

    // Mock response with no body
    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      body: null
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(<App />)

    await waitFor(() => expect(screen.getAllByText('Online').length).toBe(3))

    const input = screen.getByPlaceholderText('Message orchestrator...')
    const button = screen.getByText('Send')

    fireEvent.change(input, { target: { value: 'hi' } })
    fireEvent.click(button)

    const errorMsg = await screen.findByText(/Sorry, I encountered an error connecting to the orchestrator/i)
    expect(errorMsg).toBeInTheDocument()
    
    expect(consoleSpy).toHaveBeenCalledWith('Error:', expect.any(Error))
    consoleSpy.mockRestore()
  })

  it('starts a new message bubble if agent author changes', async () => {
    mockOnlineStatus()

    const sseData = [
      'data: {"partial": false, "author": "agent1", "content": {"parts": [{"text": "Hello from 1"}]}}\n\n',
      'data: {"partial": false, "author": "agent2", "content": {"parts": [{"text": "Hello from 2"}]}}\n\n'
    ]

    const stream = new ReadableStream({
      async start(controller) {
        for (const chunk of sseData) {
          controller.enqueue(new TextEncoder().encode(chunk))
          // `await new Promise` adds an artificial delay to the stream chunks
          // allowing React enough time to process state updates between events.
          await new Promise(r => setTimeout(r, 50)) 
        }
        controller.close()
      }
    })

    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      body: stream
    })

    render(<App />)
    await waitFor(() => expect(screen.getAllByText('Online').length).toBe(3))

    const input = screen.getByPlaceholderText('Message orchestrator...')
    const button = screen.getByText('Send')

    fireEvent.change(input, { target: { value: 'hi' } })
    fireEvent.click(button)

    const msg1 = await screen.findByText('Hello from 1')
    const msg2 = await screen.findByText('Hello from 2')
    expect(msg1).toBeInTheDocument()
    expect(msg2).toBeInTheDocument()
  })

  it('does not send if already loading', async () => {
    mockOnlineStatus()
    render(<App />)

    await waitFor(() => expect(screen.getAllByText('Online').length).toBe(3))

    // Make fetch hang indefinitely to keep isLoading = true
    let resolveFetch: any
    ;(fetch as any).mockImplementationOnce(() => new Promise(res => { resolveFetch = res }))

    const input = screen.getByPlaceholderText('Message orchestrator...')
    const button = screen.getByText('Send')

    fireEvent.change(input, { target: { value: 'first message' } })
    fireEvent.click(button) // Sets isLoading = true

    // Now try to send again while loading (button is disabled, so we submit the form directly to hit the early return)
    const form = document.querySelector('form')!
    fireEvent.submit(form)

    // Only the first message should be added to the UI
    const firstMsg = await screen.findByText('first message')
    expect(firstMsg).toBeInTheDocument()
    // `queryByText` is used to verify that an element does NOT exist.
    const secondMsg = screen.queryByText('second message')
    expect(secondMsg).toBeNull()

    // Resolve the promise to clean up and allow the test to finish
    resolveFetch({ ok: true, body: null })
  })

  it('updates agent message even if it has no author initially', async () => {
    mockOnlineStatus()

    const sseData = [
      'data: {"partial": false, "content": {"parts": [{"text": "Hello without author"}]}}\n\n',
      'data: {"partial": false, "author": "new_author", "content": {"parts": [{"text": "Hello with author"}]}}\n\n'
    ]

    const stream = new ReadableStream({
      async start(controller) {
        for (const chunk of sseData) {
          controller.enqueue(new TextEncoder().encode(chunk))
          await new Promise(r => setTimeout(r, 50)) 
        }
        controller.close()
      }
    })

    ;(fetch as any).mockResolvedValueOnce({
      ok: true,
      body: stream
    })

    render(<App />)
    await waitFor(() => expect(screen.getAllByText('Online').length).toBe(3))

    const input = screen.getByPlaceholderText('Message orchestrator...')
    const button = screen.getByText('Send')

    fireEvent.change(input, { target: { value: 'hi' } })
    fireEvent.click(button)

    const msg = await screen.findByText('Hello with author')
    expect(msg).toBeInTheDocument()
  })
})
