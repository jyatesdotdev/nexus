/**
 * EDUCATIONAL: setupTests.ts
 * WHY: This file is automatically executed before any of your tests run. It's the perfect place 
 * to put global configurations, mock browser APIs that jsdom doesn't support, or import 
 * custom matchers.
 * HOW: Vitest is configured (usually in vite.config.ts) to run this file during its setup phase.
 */
import '@testing-library/jest-dom' // Adds custom DOM matchers like 'toBeInTheDocument'
import { vi } from 'vitest'

/**
 * WHY: jsdom (the simulated browser environment we use for testing) doesn't implement all 
 * native browser APIs. If a component calls `scrollIntoView`, the test will crash.
 * HOW: We use `vi.fn()` to create a mock function (a "spy" or "dummy" function) that replaces
 * the missing implementation, preventing errors without actually trying to scroll.
 */
// Mock scrollIntoView as it is not implemented in jsdom
window.HTMLElement.prototype.scrollIntoView = vi.fn()
