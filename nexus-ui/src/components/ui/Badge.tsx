import React from 'react'
import { cn } from '../../lib/utils'

/**
 * CONCEPT: UI Primitive - Badge
 * WHY: Standardizes status labels (Online, Offline, Connected, etc).
 * HOW: Uses a 'variant' pattern to switch between success (emerald) and error (rose) styles.
 */
interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'success' | 'error' | 'neutral'
}

export function Badge({ className, variant = 'neutral', ...props }: BadgeProps) {
  const variants = {
    success: "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-100 dark:border-emerald-900/30",
    error: "bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-400 border-rose-100 dark:border-rose-900/30",
    neutral: "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 border-neutral-200 dark:border-neutral-700"
  }

  return (
    <span
      className={cn(
        "text-xs px-3 py-1.5 rounded-lg font-bold transition-all border inline-flex items-center",
        variants[variant],
        className
      )}
      {...props}
    />
  )
}
