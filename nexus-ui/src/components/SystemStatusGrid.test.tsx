/**
 * EDUCATIONAL: Component Testing with React Testing Library
 * WHY: We want to test our React components from the perspective of a user. 
 * React Testing Library encourages testing behavior (what the user sees and does) 
 * rather than implementation details (internal state or component methods).
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SystemStatusGrid } from './SystemStatusGrid'
import '@testing-library/jest-dom'

describe('SystemStatusGrid', () => {
  // Mock data representing the props we'll pass to our component.
  const mockStatus = {
    orchestrator: 'Online' as const,
    mcp_server: 'Online' as const,
    mcp_db: 'Connected' as const,
    a2a_agent: 'Online' as const,
    a2a_api: 'Reachable' as const
  }

  it('renders all services and their subStatus', () => {
    /**
     * WHY: We need to ensure that the subStatus section (e.g., Database for MCP) 
     * is visible when provided.
     * HOW: We render the component with a mock status and check for the presence 
     * of the subStatus labels and values using `screen` queries.
     */
    // `render` draws the component in our simulated browser (jsdom).
    render(<SystemStatusGrid status={mockStatus} />)

    // `screen.getByText` searches the virtual DOM for an element containing exact text.
    // If it doesn't find it, the test will fail immediately.
    // Main services
    expect(screen.getByText('Nexus Core')).toBeInTheDocument()
    expect(screen.getByText('MCP Server')).toBeInTheDocument()
    expect(screen.getByText('A2A Agent')).toBeInTheDocument()

    // Sub-statuses
    // Passing a regular expression (like /database/i) allows for case-insensitive matching.
    expect(screen.getByText(/database/i)).toBeInTheDocument()
    expect(screen.getByText(/weather api/i)).toBeInTheDocument()
    
    // Check if the subStatus values are correct
    // `getAllByText` returns an array of all matching elements.
    const onlineValues = screen.getAllByText('Online')
    expect(onlineValues.length).toBe(3)
    expect(screen.getByText('Connected')).toBeInTheDocument()
    expect(screen.getByText('Reachable')).toBeInTheDocument()
  })

  it('renders correctly when offline', () => {
    const offlineStatus = {
      orchestrator: 'Offline' as const,
      mcp_server: 'Offline' as const,
      mcp_db: 'Offline' as const,
      a2a_agent: 'Offline' as const,
      a2a_api: 'Offline' as const
    }
    render(<SystemStatusGrid status={offlineStatus} />)
    
    const statusValues = screen.getAllByText('Offline')
    expect(statusValues.length).toBe(5)
  })
})
