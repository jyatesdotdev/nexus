import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MessageInput } from './MessageInput'
import '@testing-library/jest-dom'

describe('MessageInput Component', () => {
  const defaultProps = {
    input: '',
    setInput: vi.fn(),
    isLoading: false,
    isOffline: false,
    handleSend: vi.fn((e) => e.preventDefault())
  }

  it('renders correctly', () => {
    render(<MessageInput {...defaultProps} />)
    expect(screen.getByPlaceholderText('Message orchestrator...')).toBeInTheDocument()
    const button = screen.getByRole('button', { name: /send/i })
    expect(button).toBeInTheDocument()
    // Button is disabled because input is empty
    expect(button).toBeDisabled()
  })

  it('updates input value on typing', () => {
    render(<MessageInput {...defaultProps} />)
    const inputEl = screen.getByPlaceholderText('Message orchestrator...')
    fireEvent.change(inputEl, { target: { value: 'Hello' } })
    expect(defaultProps.setInput).toHaveBeenCalledWith('Hello')
  })

  it('calls handleSend on form submission when input is not empty', () => {
    render(<MessageInput {...defaultProps} input="Hello" />)
    const button = screen.getByRole('button', { name: /send/i })
    
    // Button should be enabled now
    expect(button).not.toBeDisabled()
    
    // Using fireEvent.submit on the form, or clicking the button
    fireEvent.click(button)
    expect(defaultProps.handleSend).toHaveBeenCalledTimes(1)
  })

  it('disables input and button when isLoading is true', () => {
    render(<MessageInput {...defaultProps} input="Hello" isLoading={true} />)
    const inputEl = screen.getByPlaceholderText('Message orchestrator...')
    const button = screen.getByRole('button')
    
    expect(inputEl).toBeDisabled()
    expect(button).toBeDisabled()
  })

  it('shows offline state and disables inputs when isOffline is true', () => {
    render(<MessageInput {...defaultProps} isOffline={true} />)
    const inputEl = screen.getByPlaceholderText('Orchestrator is offline')
    const button = screen.getByRole('button', { name: /send/i })
    
    expect(inputEl).toBeInTheDocument()
    expect(inputEl).toBeDisabled()
    expect(button).toBeDisabled()
  })
})
