import React from 'react'
import { cn } from '../../lib/utils'

/**
 * CONCEPT: UI Primitive - Card
 * WHY: Provides a consistent container style for various sections (chat, status).
 * HOW: Wraps content in a styled div, allowing external class overrides via the `cn` utility.
 */
interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800 rounded-2xl shadow-sm",
        className
      )}
      {...props}
    />
  )
}
