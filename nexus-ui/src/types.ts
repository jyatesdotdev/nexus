/**
 * TypeScript Interfaces define the 'shape' of an object.
 * They act as a contract, ensuring that any object of this type
 * has the required properties with the correct types.
 */

/**
 * Represents a single message in the chat session.
 */
export interface Message {
  /**
   * 'role' uses a Union Type ('user' | 'agent' | 'system').
   * This restricts the value to exactly one of these three strings,
   * providing excellent autocompletion and preventing typos.
   */
  role: 'user' | 'agent' | 'system'

  /**
   * The actual content of the message.
   */
  text: string

  /**
   * Optional structured data for Generative UI components.
   * This allows the UI to render bespoke components (e.g., a WeatherWidget)
   * instead of plain text if a payload is provided.
   */
  data?: any

  /**
   * The '?' makes this property optional.
   * Not every message needs an explicit author (e.g., system messages).
   */
  author?: string
  
  /**
   * Optional ID for pending actions requiring user confirmation.
   */
  actionId?: string
}

/**
 * Represents the health status of various backend services.
 * Using specific string literals instead of just 'string' makes the
 * state management much more predictable.
 */
export interface ServiceStatus {
  orchestrator: 'Online' | 'Offline'
  mcp_server: 'Online' | 'Offline'
  mcp_db: 'Connected' | 'Offline'
  a2a_agent: 'Online' | 'Offline'
  a2a_api: 'Reachable' | 'Offline'
}
