/**
 * EDUCATIONAL: Component Index Tests
 * WHY: When using barrel files (index.ts) to export multiple components, it's good practice 
 * to verify that everything is exported correctly. This prevents accidental breakage if an 
 * import/export statement gets mangled.
 * HOW: We use `describe` to group related tests, and `it` to define a specific test case.
 */
import { expect, it, describe } from 'vitest'
import { render } from '@testing-library/react'
import * as UI from './index'

// `describe` creates a block that groups together several related tests.
describe('UI components index', () => {
  // `it` (or `test`) defines an individual test case.
  it('should export all UI components', () => {
    // `expect` lets you assert that a value meets certain conditions.
    // `toBeDefined` ensures the variable isn't undefined (which it would be if the export failed).
    expect(UI.Badge).toBeDefined()
    expect(UI.Button).toBeDefined()
    expect(UI.Card).toBeDefined()
    expect(UI.Input).toBeDefined()

    // Render them to ensure the index file exports are actually evaluated by coverage
    // `render` creates a simulated DOM representation of the React component.
    render(<UI.Badge>Test</UI.Badge>)
    render(<UI.Button>Test</UI.Button>)
    render(<UI.Card>Test</UI.Card>)
    render(<UI.Input />)
  })
})
