import React from 'react'
import { cn } from '../../lib/utils'

/**
 * CONCEPT: UI Primitive - Input
 * WHY: Standardizes input styling across the app.
 * HOW: Wraps a native input, providing a default neutral theme that matches the app's aesthetic.
 */
// EDUCATIONAL NOTE: A Zero-API Wrapper Is Still a Contract
// InputProps is a bare type alias for the native input props — this component
// adds no behavior at all, only a styling baseline. That is the point: by
// owning ONLY appearance, it can never drift out of sync with how <input>
// works (controlled value/onChange, disabled, focus) because it forwards all
// of it untouched via {...props}. Compare with Button, which does add behavior
// (isLoading) and therefore has to manage the interaction between its prop
// and the native `disabled`. Start wrappers at this altitude; earn complexity
// only when a real cross-cutting behavior demands it.
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
