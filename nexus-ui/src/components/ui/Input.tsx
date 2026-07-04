import React from 'react'
import { cn } from '../../lib/utils'

/**
 * CONCEPT: UI Primitive - Input
 * WHY: Standardizes input styling across the app.
 * HOW: Wraps a native input, providing a default neutral theme that matches the app's aesthetic.
 */
type InputProps = React.InputHTMLAttributes<HTMLInputElement>

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "flex-grow [background:rgb(30,41,59)] border-2 border-transparent focus:border-indigo-500/50 rounded-xl px-5 py-3 focus:ring-0 outline-none transition-all placeholder:text-slate-500 text-slate-100 font-medium disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}
