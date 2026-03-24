import React from 'react'
import { cn } from '../../lib/utils'

/**
 * CONCEPT: UI Primitive - Button
 * WHY: Centralizes button logic, including loading states and hover effects.
 * HOW: Extends native button props and adds a `variant` and `isLoading` prop.
 */
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
    primary: "bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-950 hover:scale-[1.02] active:scale-[0.98] shadow-md",
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
