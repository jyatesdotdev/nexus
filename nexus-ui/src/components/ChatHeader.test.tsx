import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatHeader } from './ChatHeader'
import '@testing-library/jest-dom'

describe('ChatHeader Component', () => {
  it('renders correctly with Online status', () => {
    render(<ChatHeader status="Online" sessionId="123-abc" />)
    expect(screen.getByText('Live Session')).toBeInTheDocument()
    expect(screen.getByText('123-abc')).toBeInTheDocument()

    // Test the specific status dot span which comes just before "Live Session"
    // Since it has no text, we query by its classes or we can find it structurally.
    // It's a span inside the h3.
    const h3 = screen.getByText('Live Session').closest('h3')
    const dot = h3?.querySelector('span')
    
    expect(dot).toHaveClass('bg-emerald-500')
    expect(dot).toHaveClass('animate-pulse')
  })

  it('renders correctly with Offline status', () => {
    render(<ChatHeader status="Offline" sessionId="456-def" />)
    expect(screen.getByText('Live Session')).toBeInTheDocument()
    expect(screen.getByText('456-def')).toBeInTheDocument()

    const h3 = screen.getByText('Live Session').closest('h3')
    const dot = h3?.querySelector('span')
    
    expect(dot).toHaveClass('bg-rose-500')
    expect(dot).not.toHaveClass('animate-pulse')
  })
})
