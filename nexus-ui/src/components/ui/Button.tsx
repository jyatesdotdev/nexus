import React from 'react'
import { cn } from '../../lib/utils'

/**
 * CONCEPT: UI Primitive - Button
 * WHY: Centralizes button logic, including loading states and hover effects.
 * HOW: Extends native button props and adds a `variant` and `isLoading` prop.
 */
// EDUCATIONAL NOTE: Extend the Platform, Don't Re-Invent It
// Extending React.ButtonHTMLAttributes<HTMLButtonElement> means this component
// accepts every native button prop (type, onClick, aria-*, form...) without
// declaring any of them — `{...props}` forwards the remainder after our custom
// props are destructured out. Because our additions are typed alongside the
// native set, misuse is caught at compile time. Note the line
// `disabled={isLoading || disabled}`: loading IMPLIES disabled here, which is
// a policy decision — a button that shows a spinner but still accepts clicks
// invites double-submits, so the primitive forbids that state by construction
// rather than trusting every call site to remember.
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost'
  isLoading?: boolean
}

export function Button({ 
  className, 
  variant = 'primary', 
  isLoading, 
  children, 
  disabled, 
  ...props 
}: ButtonProps) {
  const variants = {
    primary: "bg-gradient-to-r from-indigo-500 to-violet-500 text-white hover:scale-[1.02] active:scale-[0.98] shadow-md shadow-indigo-500/30 border-none",
    ghost: "bg-transparent hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-600 dark:text-neutral-400 border border-neutral-200 dark:border-neutral-800 shadow-sm"
  }

  return (
    <button
      className={cn(
        "px-6 py-2 rounded-xl font-bold transition-all disabled:opacity-50 disabled:scale-100 flex items-center justify-center gap-2",
        variants[variant],
        className
      )}
      disabled={isLoading || disabled}
      {...props}
    >
      {isLoading ? (
        <>
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
          <span>Thinking</span>
        </>
      ) : children}
    </button>
  )
}
