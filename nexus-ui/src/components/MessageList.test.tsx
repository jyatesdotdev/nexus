/**
 * EDUCATIONAL: Interactive Component Testing
 * WHY: This file demonstrates how to test components that involve user interactions 
 * (like clicking buttons) and verify that they trigger the correct callback functions.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MessageList } from './MessageList'
import { buildTraceUrl } from '../lib/trace'
import type { Message } from '../types'
import '@testing-library/jest-dom'
import { createRef } from 'react'

describe('MessageList', () => {
  it('calls setInput when clicking suggestion buttons', () => {
    /**
     * WHY: Suggestions help users know what to ask. We need to verify 
     * that clicking a suggestion updates the input field via the setInput prop.
     * HOW: We use `vi.fn()` to create a mock function for `setInput`. This allows us
     * to spy on whether it was called, and with what arguments, after we simulate a click.
     */
    const setInputMock = vi.fn()
    const messagesEndRef = createRef<HTMLDivElement>()
    
    // `render` draws the component in our simulated browser (jsdom).
    render(
      <MessageList 
        messages={[]} 
        messagesEndRef={messagesEndRef} 
        setInput={setInputMock} 
      />
    )

    // Find a suggestion button
    const suggestionBtn = screen.getByText('HR Directory')
    
    // `fireEvent` simulates DOM events (like clicks, typing, etc.)
    fireEvent.click(suggestionBtn)

    // Verify setInput was called with the correct query
    expect(setInputMock).toHaveBeenCalledWith('Who is in the engineering department?')
  })

  it('renders messages correctly', () => {
    const messages = [
      { role: 'user', text: 'hello' },
      { role: 'agent', text: 'hi there', author: 'test_agent' },
      { role: 'system', text: 'delegating...' }
    ]
    const setInputMock = vi.fn()
    const messagesEndRef = createRef<HTMLDivElement>()

    render(
      <MessageList 
        messages={messages as Message[]} 
        messagesEndRef={messagesEndRef} 
        setInput={setInputMock} 
      />
    )

    expect(screen.getByText('hello')).toBeInTheDocument()
    expect(screen.getByText('hi there')).toBeInTheDocument()
    expect(screen.getByText(/test_agent/i)).toBeInTheDocument()
    expect(screen.getByText('delegating...')).toBeInTheDocument()
  })

  it('renders a user message with an author correctly', () => {
    /**
     * WHY: We need to cover the edge case where a user message has an author assigned,
     * ensuring the styling logic (justify-end) handles it properly.
     * HOW: By rendering a specific message shape and asserting its contents are visible.
     */
    const messages = [
      { role: 'user', text: 'hello from user', author: 'User123' },
    ]
    const setInputMock = vi.fn()
    const messagesEndRef = createRef<HTMLDivElement>()

    render(
      <MessageList 
        messages={messages as Message[]} 
        messagesEndRef={messagesEndRef} 
        setInput={setInputMock} 
      />
    )

    expect(screen.getByText('hello from user')).toBeInTheDocument()
    expect(screen.getByText(/User123/i)).toBeInTheDocument()
  })

  it('renders a trace chip on agent messages that carry a traceId', () => {
    /**
     * WHY: Trace visibility is the point of Nexus — an agent message that
     * arrived with an X-Trace-Id header must expose a deep link to its
     * distributed trace in Grafana Tempo.
     */
    const traceId = 'abcdef0123456789abcdef0123456789'
    const messages: Message[] = [
      { role: 'agent', text: 'traced reply', author: 'nexus_orchestrator', traceId }
    ]

    render(
      <MessageList
        messages={messages}
        messagesEndRef={createRef<HTMLDivElement>()}
        setInput={vi.fn()}
      />
    )

    const link = screen.getByRole('link', { name: /trace abcdef0/i })
    expect(link).toHaveAttribute('href', buildTraceUrl(traceId))
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('renders no trace chip when a message has no traceId', () => {
    const messages: Message[] = [
      { role: 'agent', text: 'untraced reply', author: 'nexus_orchestrator' }
    ]

    render(
      <MessageList
        messages={messages}
        messagesEndRef={createRef<HTMLDivElement>()}
        setInput={vi.fn()}
      />
    )

    expect(screen.getByText('untraced reply')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /trace/i })).not.toBeInTheDocument()
  })
})
