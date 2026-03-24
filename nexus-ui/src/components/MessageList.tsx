import type { RefObject } from 'react'
import type { Message } from '../types'
import ReactMarkdown from 'react-markdown'

/**
 * MessageList Component:
 * Responsible for displaying the conversation history.
 */
interface MessageListProps {
  messages: Message[]
  /**
   * RefObject: A TypeScript type for a React Ref. 
   * It helps us point to a specific DOM element (the bottom of the list) 
   * to enable auto-scrolling.
   */
  messagesEndRef: RefObject<HTMLDivElement | null>
  setInput: (value: string) => void
}

export function MessageList({ messages, messagesEndRef, setInput }: MessageListProps) {
  return (
    <div className="flex-grow overflow-y-auto p-6 space-y-6 scroll-smooth bg-neutral-50/30 dark:bg-transparent">
      {/* 
        Conditional Rendering (Short-circuit &&): 
        If the condition on the left is true, the JSX on the right is rendered.
        Perfect for showing "empty state" messages.
      */}
      {messages.length === 0 && (
        <div className="h-full flex flex-col items-center justify-center text-neutral-400 space-y-6">
          <div className="text-6xl opacity-20">💬</div>
          <div className="text-center">
            <p className="text-lg font-medium mb-4">No messages yet. Try asking:</p>
            <div className="flex flex-wrap justify-center gap-3">
              {/* 
                Mapping over an array:
                'map' is the standard way to transform data into JSX.
              */}
              {[
                { label: "HR Directory", query: "Who is in the engineering department?" },
                { label: "Weather Forecast", query: "What is the weather like in Paris?" },
                { label: "System Status", query: "Check system status" }
              ].map(q => (
                <button 
                  /**
                   * key Prop:
                   * React needs a unique 'key' for every item in a list to 
                   * efficiently track changes and updates.
                   */
                  key={q.query}
                  onClick={() => setInput(q.query)}
                  className="px-4 py-2 rounded-xl border border-neutral-200 dark:border-neutral-800 hover:border-neutral-400 dark:hover:border-neutral-600 hover:bg-white dark:hover:bg-neutral-800 text-sm font-medium transition-all shadow-sm"
                >
                  {q.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 
        Rendering the Message History:
        We check the 'role' of each message to decide how to style it.
      */}
      {messages.map((m, i) => {
        // System messages (like "Delegating to...") are shown as small text
        if (m.role === 'system') {
          return (
            <div key={i} className="flex items-center gap-2 text-neutral-400 dark:text-neutral-500 text-[10px] uppercase tracking-widest font-black ml-4 py-1 animate-in fade-in duration-500">
              <div className="w-1 h-1 rounded-full bg-neutral-300 dark:bg-neutral-700"></div>
              {m.text}
            </div>
          )
        }

        // User and Agent messages are shown in bubbles
        return (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
            <div className={`max-w-[85%] p-4 rounded-2xl shadow-sm ${
              m.role === 'user' 
                ? 'bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-950 rounded-tr-none' 
                : 'bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 rounded-tl-none border border-neutral-100 dark:border-neutral-700'
            }`}>
              {m.author && (
                <div className={`text-[10px] uppercase tracking-widest font-black mb-2 opacity-60 flex items-center gap-1.5 ${m.role === 'user' ? 'justify-end' : ''}`}>
                  {m.role === 'agent' && <span className="w-1 h-1 rounded-full bg-current"></span>}
                  {m.author}
                </div>
              )}
              {/* 
                ReactMarkdown:
                This component takes a string of Markdown and renders it as HTML.
                'prose' is a Tailwind Typography class that styles basic HTML elements.
              */}
              <div className={`prose dark:prose-invert max-w-none ${m.role === 'user' ? 'prose-p:text-white dark:prose-p:text-neutral-950' : ''}`}>
                <ReactMarkdown>{m.text}</ReactMarkdown>
              </div>
            </div>
          </div>
        )
      })}
      
      {/* 
        The Scroll Anchor:
        This empty div is what messagesEndRef points to.
        When we call scrollIntoView() on this ref, the page scrolls here.
      */}
      <div ref={messagesEndRef} />
    </div>
  )
}
