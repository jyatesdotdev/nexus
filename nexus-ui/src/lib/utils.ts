import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Utility Function: cn (short for ClassName)
 * 
 * WHY:
 * 1. clsx: Allows us to conditionally apply CSS classes (e.g., if isOnline, add 'text-green').
 * 2. twMerge (Tailwind Merge): Resolves conflicts between Tailwind classes. 
 *    Example: If a component has 'p-4' but you pass 'p-2' as a prop, twMerge ensures 
 *    that 'p-2' wins and we don't end up with both padding classes applied.
 * 
 * HOW:
 * It takes any number of inputs (strings, objects, arrays) and returns a single,
 * cleaned-up string of CSS classes that React can use in 'className={...}'.
 */
// EDUCATIONAL NOTE: Why Plain String Concatenation Fails for Tailwind
// In `className="p-4 p-2"` the winner is NOT the last class in the string —
// it's whichever rule appears later in the generated stylesheet, an ordering
// you don't control. So a Card defaulting `p-4` could silently beat a caller's
// `p-2` (or not, depending on build output). twMerge fixes this by
// understanding Tailwind's conflict groups and dropping the earlier of two
// competing utilities, which is what lets every UI primitive here promise
// "caller's className wins" — clsx handles the conditional/array inputs,
// twMerge arbitrates the conflicts. The pipeline order (clsx THEN twMerge) is
// mandatory: merging before flattening would miss conflicts hidden inside
// conditional objects.
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
