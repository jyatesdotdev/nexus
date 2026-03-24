import { useState, useRef, useEffect } from 'react'
import type { Message, ServiceStatus } from './types'
import { ChatHeader } from './components/ChatHeader'
import { MessageList } from './components/MessageList'
import { MessageInput } from './components/MessageInput'
import { SystemStatusGrid } from './components/SystemStatusGrid'
import { Card } from './components/ui'

/**
 * CONCEPT: Root Frontend Orchestrator
 * WHY: Manages the global state of the chat session, connectivity, and real-time streaming logic.
 * HOW: Uses React hooks (useState, useEffect) to coordinate between the Orchestrator backend
 *      and the modular UI components.
 */
export default function App() {
  /**
   * useState Hook:
   * WHY: React needs a way to "remember" data that changes over time. 
   * When state updates, React automatically re-renders the component to show the new data.
   * 
   * messages: An array of Message objects.
   * input: The text currently typed in the input box.
   * isLoading: A boolean to disable buttons/show spinners while waiting for the AI.
   */
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  /**
   * Initializing state with a function:
   * This is called "lazy initialization". It only runs once when the component mounts.
   */
  const [sessionId] = useState(() => `session_${Math.random().toString(36).substring(7)}`)
  
  const [status, setStatus] = useState<ServiceStatus>({
    orchestrator: 'Offline',
    mcp_server: 'Offline',
    mcp_db: 'Offline',
    a2a_agent: 'Online',
    a2a_api: 'Offline'
  })
  
  /**
   * useRef Hook:
   * WHY: Unlike useState, updating a Ref does NOT trigger a re-render.
   * It's perfect for holding direct references to DOM elements or values that 
   * don't affect the UI layout directly.
   */
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    // Optional Chaining (?.) safely checks if current exists before calling scrollIntoView
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  /**
   * useEffect Hook:
   * WHY: Used for "side effects" - things that happen outside the normal render flow.
   * This effect runs every time the [messages] array changes.
   */
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  /**
   * Polling for system status:
   * This effect runs once on mount (empty dependency array []).
   */
  useEffect(() => {
    const checkStatus = async () => {
      try {
        // import.meta.env: How Vite accesses environment variables.
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
        const response = await fetch(`${baseUrl}/system-status`)
        if (response.ok) {
          const data = await response.json()
          setStatus(data)
        } else {
          throw new Error('Failed to fetch status')
        }
      } catch (error) {
        setStatus({
          orchestrator: 'Offline',
          mcp_server: 'Offline',
          mcp_db: 'Offline',
          a2a_agent: 'Offline',
          a2a_api: 'Offline'
        })
      }
    }

    checkStatus()
    // setInterval: Run the check every 5 seconds.
    const interval = setInterval(checkStatus, 5000)
    
    // Cleanup function: React calls this when the component unmounts to prevent memory leaks.
    return () => clearInterval(interval)
  }, [])

  /**
   * handleSend: The core logic for communicating with the AI.
   * Uses async/await because network requests take time and shouldn't "block" the UI.
   */
  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault() // Prevents the browser from reloading the page on form submit
    if (!input.trim() || isLoading) return

    const userMessage: Message = { role: 'user', text: input }
    
    // Functional update: (prev) => ... ensures we are working with the latest state
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
      const response = await fetch(`${baseUrl}/run_sse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_name: 'containerized_agents',
          user_id: 'default_user',
          session_id: sessionId,
          new_message: { role: 'user', parts: [{ text: input }] },
          streaming: true
        })
      })

      if (!response.body) throw new Error('No response body')

      /**
       * Web Streams API & TextDecoder:
       * HOW: response.body.getReader() allows us to read the response as it arrives.
       * TextDecoder converts the raw binary "chunks" into readable strings.
       */
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulatedText = ''
      
      /**
       * Delegation Tracking:
       * In a multi-agent system, the "orchestrator" might hand off the task.
       * We track this to show "System" messages in the UI.
       */
      let announcedDelegation = ''

      // The loop continues until the stream is finished (done === true)
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        // Server-Sent Events (SSE) format: Each event starts with "data: " and ends with newlines.
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              // substring(6) removes the "data: " prefix so we can parse the JSON
              const data = JSON.parse(line.substring(6))
              
              // 1. Handle Delegation/Transfer
              if (data.actions?.transferToAgent) {
                const target = data.actions.transferToAgent
                if (target !== announcedDelegation) {
                  announcedDelegation = target
                  setMessages((prev) => [...prev, { 
                    role: 'system', 
                    text: `Delegating to ${target}...` 
                  }])
                  accumulatedText = ''
                }
              }

              // 2. Handle Content Streaming
              if (data.content?.parts) {
                const eventText = data.content.parts.map((p: any) => p.text).join('')
                const author = data.author
                
                /**
                 * Delta Accumulation Logic:
                 * HOW: LLMs often stream "deltas" (small bits of text).
                 * WHY: data.partial tells us if this is a fragment (true) or the full final text (false).
                 * If it's a fragment, we append it. If it's the final version, we use it as the source of truth.
                 */
                if (data.partial === true) {
                  accumulatedText += eventText
                } else {
                  accumulatedText = eventText // Final message or replacement
                }

                if (accumulatedText.trim()) {
                  setMessages((prev) => {
                    const last = prev[prev.length - 1]
                    // If the last message was from the same agent, update its text
                    // instead of adding a whole new message bubble.
                    if (last && last.role === 'agent' && (last.author === author || !last.author)) {
                      return [...prev.slice(0, -1), { ...last, text: accumulatedText, author: author }]
                    } else {
                      // Otherwise, start a new message bubble
                      return [...prev, { role: 'agent', text: accumulatedText, author: author }]
                    }
                  })
                }
              }
            } catch (e) {
              console.error('Error parsing SSE line', e)
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error)
      setMessages((prev) => [...prev, { role: 'agent', text: 'Sorry, I encountered an error connecting to the orchestrator.' }])
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * JSX: The HTML-like syntax used by React to define the UI.
   * Components like <ChatHeader />, <MessageList />, etc., are custom components
   * defined in other files.
   */
  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 p-4 md:p-8 font-sans">
      <main className="max-w-4xl mx-auto space-y-12">
        {/* Profile Section */}
        <section className="flex flex-col md:flex-row items-center md:items-start gap-8 border-b border-neutral-200 dark:border-neutral-800 pb-12">
          <div className="w-32 h-32 md:w-48 md:h-48 rounded-full bg-neutral-200 dark:bg-neutral-800 flex-shrink-0 overflow-hidden relative border border-neutral-200 dark:border-neutral-700 shadow-sm">
             <div className="absolute inset-0 flex items-center justify-center text-4xl">🤖</div>
          </div>
          <div className="flex-grow text-center md:text-left">
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight mb-2">Multi-Agent Orchestrator</h1>
            <h2 className="text-neutral-500 dark:text-neutral-400 mb-4 font-medium italic">
              Powered by Google ADK & MCP
            </h2>
            <p className="text-neutral-600 dark:text-neutral-400 leading-relaxed max-w-2xl text-lg">
              This interactive dashboard connects to a distributed multi-agent system. 
              The root orchestrator delegates tasks to specialized sub-agents running in separate containers.
            </p>
          </div>
        </section>

        {/* Chat Interface */}
        <Card className="overflow-hidden flex flex-col h-[650px] shadow-xl border-neutral-200 dark:border-neutral-800">
          <ChatHeader status={status.orchestrator} sessionId={sessionId} />
          
          {/* Passing state down as "props" (properties) */}
          <MessageList 
            messages={messages} 
            messagesEndRef={messagesEndRef} 
            setInput={setInput} 
          />

          <MessageInput 
            input={input} 
            setInput={setInput} 
            isLoading={isLoading} 
            isOffline={status.orchestrator === 'Offline'} 
            handleSend={handleSend} 
          />
        </Card>

        {/* System Status Grid */}
        <SystemStatusGrid status={status} />
      </main>
    </div>
  )
}
