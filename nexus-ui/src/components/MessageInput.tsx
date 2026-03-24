import React from 'react'
import { Button, Input } from './ui'

/**
 * MessageInputProps Interface:
 * WHY: In TypeScript, we define an interface for our component "props" (properties).
 * This ensures that the parent component (App.tsx) passes the correct data types.
 * 
 * - input: The current string value of the input.
 * - setInput: A function to update that string.
 * - isLoading: Boolean to show a loading state.
 * - isOffline: Boolean to disable the input if the server is down.
 * - handleSend: The function to call when the form is submitted.
 */
interface MessageInputProps {
  input: string
  setInput: (value: string) => void
  isLoading: boolean
  isOffline: boolean
  handleSend: (e: React.FormEvent) => void
}

/**
 * MessageInput Component:
 * HOW: This is a "Functional Component". It receives 'props' as an object,
 * and we use "destructuring" { input, setInput... } to pull out the individual values.
 */
export function MessageInput({ input, setInput, isLoading, isOffline, handleSend }: MessageInputProps) {
  return (
    /**
     * onSubmit: Using a form with an onSubmit handler is better than just a button click.
     * It allows the user to press 'Enter' to send the message.
     */
    <form onSubmit={handleSend} className="p-5 border-t border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
      <div className="flex gap-3">
        {/* 
          Controlled Component: 
          The 'value' is tied to React state (input), and 'onChange' updates that state.
          This makes the React state the "single source of truth".
        */}
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={!isOffline ? "Message orchestrator..." : "Orchestrator is offline"}
          disabled={isLoading || isOffline}
        />
        <Button
          type="submit"
          disabled={!input.trim() || isOffline}
          isLoading={isLoading}
          className="px-8 py-3"
        >
          Send
        </Button>
      </div>
    </form>
  )
}
