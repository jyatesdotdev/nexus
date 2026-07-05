import React from 'react'
import { cn } from '../../lib/utils'

/**
 * CONCEPT: UI Primitive - Card
 * WHY: Provides a consistent container style for various sections (chat, status).
 * HOW: Wraps content in a styled div, allowing external class overrides via the `cn` utility.
 */
// EDUCATIONAL NOTE: Why Some Styles Use [background:...] Arbitrary Values
// Tailwind's bracket syntax injects raw CSS when no theme token fits — here an
// exact rgba() glass tint that pairs with backdrop-blur-xl. The trade-off is
// real: arbitrary values are invisible to the design system (no dark: token
// swap, no theme retuning), so they belong in exactly one place — a primitive
// like this — where every Card inherits the decision and a redesign edits one
// line. Sprinkled through call sites instead, the same trick becomes untracked
// style drift. Callers still get the last word: cn() puts their className
// after the base string, so overrides win via tailwind-merge, not !important.
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
