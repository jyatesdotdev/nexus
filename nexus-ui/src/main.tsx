import './telemetry'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

/**
 * React Entry Point: This file connects our React code to the HTML page.
 * 
 * 1. createRoot: This is the modern React 18+ way to initialize the app. 
 *    We find an element in our index.html with the ID 'root'.
 * 
 * 2. '!': The exclamation mark is a TypeScript "non-null assertion". 
 *    It tells TS: "I know this element exists, so don't worry about it being null."
 * 
 * 3. StrictMode: A built-in wrapper that helps developers find common bugs
 *    early during development. It may double-invoke some functions (like hooks)
 *    to ensure they are 'pure' and have no side effects.
 */
// EDUCATIONAL NOTE: Two Orderings Here Are Load-Bearing
// (1) `import './telemetry'` is FIRST on purpose: OpenTelemetry must patch
// fetch/XHR before any module captures a reference to them, so instrumentation
// has to load before App and its imports — moving this line breaks tracing
// silently. (2) StrictMode double-invokes renders and re-runs effects
// (mount -> unmount -> mount) in dev builds only. For this app that is a live
// constraint, not trivia: effects that open SSE connections or start the
// status poller will fire twice, so their cleanup functions are what keep dev
// from leaking duplicate streams. If you see doubled requests in the network
// tab in dev but not in the production build, this wrapper is why.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
