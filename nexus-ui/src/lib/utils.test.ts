/**
 * EDUCATIONAL: Utility Testing
 * WHY: We need to ensure that our class merging utility works correctly,
 * especially when combining conditional classes and resolving Tailwind conflicts.
 * HOW: We test different input types (strings, objects, arrays) and verify
 * the final resolved string.
 */
import { describe, it, expect } from 'vitest'
import { cn } from './utils'

describe('cn utility', () => {
  it('merges multiple class strings', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2')
  })

  it('handles conditional classes (objects)', () => {
    expect(cn('base-class', { 'conditional-true': true, 'conditional-false': false })).toBe('base-class conditional-true')
  })

  it('resolves Tailwind class conflicts', () => {
    // twMerge should prioritize the latter class when there's a conflict
    expect(cn('p-4', 'p-2')).toBe('p-2')
    expect(cn('bg-red-500', 'bg-blue-500')).toBe('bg-blue-500')
  })

  it('handles arrays of classes', () => {
    expect(cn(['classA', 'classB'], 'classC')).toBe('classA classB classC')
  })

  it('ignores falsy values', () => {
    expect(cn('class-1', null, undefined, false, '', 'class-2')).toBe('class-1 class-2')
  })
})
