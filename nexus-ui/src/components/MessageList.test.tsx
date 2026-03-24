/**
 * EDUCATIONAL: Interactive Component Testing
 * WHY: This file demonstrates how to test components that involve user interactions 
 * (like clicking buttons) and verify that they trigger the correct callback functions.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MessageList } from './MessageList'
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
        messages={messages as any} 
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
        messages={messages as any} 
        messagesEndRef={messagesEndRef} 
        setInput={setInputMock} 
      />
    )

    expect(screen.getByText('hello from user')).toBeInTheDocument()
    expect(screen.getByText(/User123/i)).toBeInTheDocument()
  })
})
