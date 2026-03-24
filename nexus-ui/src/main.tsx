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
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
