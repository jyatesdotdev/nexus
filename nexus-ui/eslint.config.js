import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

// EDUCATIONAL NOTE: Each Plugin Here Guards a Different Failure Mode
// This is ESLint 9 "flat config": plain JS imports composed in an array, so
// what runs is exactly what you can read here — no hidden resolution of
// string names like the old .eslintrc had. The plugin picks are deliberate:
// react-hooks enforces the Rules of Hooks (call order/exhaustive deps), whose
// violations compile fine and fail only at runtime; react-refresh checks that
// component files export ONLY components, because one stray non-component
// export silently downgrades Vite's hot reload to a full page reload — a bug
// you'd never trace without the lint. tseslint here is the syntax-only preset:
// type-AWARE rules would need a full tsc program per lint run, a cost this
// project pays in `tsc --noEmit` instead.
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
])
