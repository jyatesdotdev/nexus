import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from './Badge'
import '@testing-library/jest-dom'

describe('Badge Component', () => {
  it('renders correctly with default neutral variant', () => {
    render(<Badge>Default Badge</Badge>)
    const badge = screen.getByText('Default Badge')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('bg-neutral-100')
  })

  it('renders the success variant', () => {
    render(<Badge variant="success">Success Badge</Badge>)
    const badge = screen.getByText('Success Badge')
    expect(badge).toHaveClass('bg-emerald-50')
  })

  it('renders the error variant', () => {
    render(<Badge variant="error">Error Badge</Badge>)
    const badge = screen.getByText('Error Badge')
    expect(badge).toHaveClass('bg-rose-50')
  })

  it('passes additional props to the span element', () => {
    render(<Badge data-testid="test-badge" id="custom-id">Props Badge</Badge>)
    const badge = screen.getByTestId('test-badge')
    expect(badge).toHaveAttribute('id', 'custom-id')
  })
})
