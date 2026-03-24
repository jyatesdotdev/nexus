import React from 'react'
import { cn } from '../../lib/utils'

/**
 * CONCEPT: UI Primitive - Input
 * WHY: Standardizes input styling across the app.
 * HOW: Wraps a native input, providing a default neutral theme that matches the app's aesthetic.
 */
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "flex-grow bg-neutral-100 dark:bg-neutral-800 border-2 border-transparent focus:border-neutral-200 dark:focus:border-neutral-700 rounded-xl px-5 py-3 focus:ring-0 outline-none transition-all placeholder:text-neutral-400 font-medium disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}
