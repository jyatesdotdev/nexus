import React from 'react'
import { cn } from '../../lib/utils'

/**
 * CONCEPT: UI Primitive - Card
 * WHY: Provides a consistent container style for various sections (chat, status).
 * HOW: Wraps content in a styled div, allowing external class overrides via the `cn` utility.
 */
type CardProps = React.HTMLAttributes<HTMLDivElement>

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "[background:rgba(30,41,59,0.85)] [border:1px_solid_rgba(255,255,255,0.06)] shadow-2xl shadow-black/40 rounded-2xl backdrop-blur-xl",
        className
      )}
      {...props}
    />
  )
}
