import { useState, useRef, useEffect } from 'react'
import type { Message, ServiceStatus } from './types'
import { ChatHeader } from './components/ChatHeader'
import { MessageList } from './components/MessageList'
import { MessageInput } from './components/MessageInput'
import { SystemStatusGrid } from './components/SystemStatusGrid'
import { Card } from './components/ui'

/**
 * EDUCATIONAL NOTE: Root Frontend Orchestrator
 * WHY: Manages the global state of the chat session, connectivity, and real-time streaming logic.
 * HOW: Uses React hooks (useState, useEffect) to coordinate between the Orchestrator backend
 *      and the modular UI components.
 */
export default function App() {
  /**
   * EDUCATIONAL NOTE: State Management
   * WHY: React needs a way to "remember" data that changes over time. 
   * When state updates, React automatically re-renders the component to show the new data.
   */
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  /**
   * EDUCATIONAL NOTE: Session Initialization
   * This uses "lazy initialization" to generate a unique session ID once when the component mounts.
   */
  const [sessionId] = useState(() => `session_${Math.random().toString(36).substring(7)}`)
  
  const [status, setStatus] = useState<ServiceStatus>({
    orchestrator: 'Offline',
    mcp_server: 'Offline',
    mcp_db: 'Offline',
    a2a_agent: 'Offline',
    a2a_api: 'Offline'
  })
  
  /**
   * EDUCATIONAL NOTE: DOM References
   * WHY: Unlike useState, updating a Ref does NOT trigger a re-render.
   * It's perfect for holding direct references to DOM elements like the scroll anchor.
   */
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    // Optional Chaining (?.) safely checks if current exists before calling scrollIntoView
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  /**
   * EDUCATIONAL NOTE: Side Effects (Scrolling)
   * This effect runs every time the [messages] array changes to keep the chat scrolled to bottom.
   */
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  /**
   * EDUCATIONAL NOTE: Service Monitoring (Polling)
   * This effect runs once on mount to start a 5-second polling interval for system health.
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
      } catch {
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
   * EDUCATIONAL NOTE: Core Communication Logic
   * handleSend: Initiates a new chat turn.
   * handleApprove: Resumes a paused workflow after user confirmation (HITL).
   * sendRequest: Manages the SSE stream and delta accumulation.
   */
  const sendRequest = async (body: Record<string, unknown>) => {
    setIsLoading(true)
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'
      const response = await fetch(`${baseUrl}/run_sse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_name: 'containerized_agents',
          user_id: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock_user_123.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
          session_id: sessionId,
          streaming: true,
          ...body
        })
      })

      if (!response.body) throw new Error('No response body')

      /**
       * EDUCATIONAL NOTE: Web Streams API & SSE Parsing
       * HOW: response.body.getReader() allows us to process the stream chunk-by-chunk.
       * We parse each "data: " line as JSON to handle deltas and system actions.
       */
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulatedText = ''
      
      /**
       * EDUCATIONAL NOTE: Multi-Agent State Tracking
       * We monitor the stream for 'transferToAgent' actions to show delegation status
       * and 'requestedToolConfirmations' to trigger the HITL approval UI.
       */
      let announcedDelegation = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6))
              
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

              const confirmations = data.actions?.requestedToolConfirmations || data.actions?.requested_tool_confirmations
              if (confirmations) {
                const keys = Object.keys(confirmations)
                if (keys.length > 0) {
                  setMessages((prev) => [...prev, { 
                    role: 'system', 
                    text: `Action requires approval: ${confirmations[keys[0]].hint || 'Please confirm execution.'}`,
                    actionId: keys[0]
                  }])
                }
              }

              if (data.content?.parts) {
                const eventText = data.content.parts.map((p: { text?: string }) => p.text || '').join('')
                const author = data.author
                
                /**
                 * EDUCATIONAL NOTE: Delta Accumulation
                 * LLMs stream "deltas" (fragments). data.partial=true means append,
                 * data.partial=false means this is the final authoritative text.
                 */
                if (data.partial === true) {
                  accumulatedText += eventText
                } else {
                  accumulatedText = eventText
                }

                if (accumulatedText.trim()) {
                  const structuredData = data.metadata?.structured_data
                  setMessages((prev) => {
                    const last = prev[prev.length - 1]
                    if (last && last.role === 'agent' && (last.author === author || !last.author)) {
                      return [...prev.slice(0, -1), { 
                        ...last, 
                        text: accumulatedText, 
                        author: author,
                        data: structuredData || last.data
                      }]
                    } else {
                      return [...prev, { 
                        role: 'agent', 
                        text: accumulatedText, 
                        author: author,
                        data: structuredData
                      }]
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
      setMessages((prev) => [...prev, { role: 'agent', text: 'Sorry, I encountered an error connecting to Nexus.' }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: Message = { role: 'user', text: input }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    
    await sendRequest({
      new_message: { role: 'user', parts: [{ text: input }] }
    })
  }

  const handleApprove = async (actionId: string) => {
    if (isLoading) return
    setMessages((prev) => [...prev, { role: 'user', text: 'Approved' }])
    
    // Send the ToolConfirmation back as a function response
    await sendRequest({
      new_message: { 
        role: 'user', 
        parts: [{ 
          function_response: { 
            name: 'adk_request_confirmation', 
            id: actionId, 
            response: { confirmed: true } 
          } 
        }] 
      }
    })
  }


  /**
   * JSX: The HTML-like syntax used by React to define the UI.
   * Components like <ChatHeader />, <MessageList />, etc., are custom components
   * defined in other files.
   */
  return (
    <div className="min-h-screen [background:#0f172a] text-neutral-100 p-4 md:p-8 font-sans">
      <main className="max-w-4xl mx-auto space-y-12">
        {/* Profile Section */}
        <section className="flex flex-col items-center justify-center text-center border-b border-slate-700/50 pb-12 mt-8">
          <div className="w-24 h-24 md:w-32 md:h-32 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex-shrink-0 overflow-hidden relative shadow-xl mb-6 flex items-center justify-center transform transition hover:scale-105">
             <div className="text-5xl text-white">✨</div>
          </div>
          <div className="flex-grow">
            <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight mb-3 bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 to-purple-600">Nexus</h1>
            <h2 className="text-slate-400 mb-6 font-semibold uppercase tracking-widest text-sm">
              Powered by Google ADK & MCP
            </h2>
            <p className="text-slate-400 leading-relaxed max-w-2xl mx-auto text-lg md:text-xl">
              The central hub for your distributed multi-agent system.
              Nexus intelligently delegates tasks to specialized sub-agents in real-time.
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
            handleApprove={handleApprove}
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
