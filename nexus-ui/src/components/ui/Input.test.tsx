import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Input } from './Input'
import '@testing-library/jest-dom'

describe('Input Component', () => {
  it('renders correctly', () => {
    render(<Input placeholder="Enter text" />)
    const input = screen.getByPlaceholderText('Enter text')
    expect(input).toBeInTheDocument()
    expect(input).toHaveClass('rounded-xl', 'flex-grow')
  })

  it('handles value changes', () => {
    const handleChange = vi.fn()
    render(<Input placeholder="Enter text" onChange={handleChange} />)
    const input = screen.getByPlaceholderText('Enter text')
    
    fireEvent.change(input, { target: { value: 'New text' } })
    expect(handleChange).toHaveBeenCalledTimes(1)
  })

  it('applies disabled state', () => {
    render(<Input placeholder="Enter text" disabled />)
    const input = screen.getByPlaceholderText('Enter text')
    expect(input).toBeDisabled()
  })

  it('merges custom classes', () => {
    render(<Input placeholder="Enter text" className="test-custom-class" />)
    const input = screen.getByPlaceholderText('Enter text')
    expect(input).toHaveClass('test-custom-class')
  })
})
