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
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
