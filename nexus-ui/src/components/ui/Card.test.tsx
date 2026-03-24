import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Card } from './Card'
import '@testing-library/jest-dom'

describe('Card Component', () => {
  it('renders children and applies base styles', () => {
    const { container } = render(<Card>Card Content</Card>)
    const card = container.firstChild as HTMLElement
    expect(card).toHaveTextContent('Card Content')
    expect(card).toHaveClass('bg-white', 'rounded-2xl', 'shadow-sm')
  })

  it('applies custom class names', () => {
    const { container } = render(<Card className="custom-test-class">Card Content</Card>)
    const card = container.firstChild as HTMLElement
    expect(card).toHaveClass('custom-test-class')
  })
})
