/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
// EDUCATIONAL NOTE: One Config, Two Tools — and a Security Property
// defineConfig is imported from 'vitest/config', not 'vite': Vitest extends
// Vite's config type with the `test` block, so build and test share one file
// and one plugin pipeline instead of drifting apart. Two non-obvious facts
// live here. First, `environment: 'jsdom'` is what lets component tests run
// in Node — there is no browser; DOM APIs are simulated. Second, an invisible
// contract: Vite statically inlines ONLY env vars prefixed VITE_ into the
// client bundle at build time. That prefix is the security boundary — an
// unprefixed secret in .env never reaches the browser, and a VITE_-prefixed
// one ALWAYS does, baked into the shipped JavaScript for anyone to read.
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.ts',
    exclude: ['node_modules', 'e2e/**'],
  },
})
