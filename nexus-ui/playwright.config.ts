import { defineConfig, devices } from '@playwright/test';

// EDUCATIONAL NOTE: End-to-End (E2E) Browser Testing
// [Why] We use Playwright to verify the actual user experience in a real browser.
// Unlike component tests (jsdom), Playwright actually interacts with the running
// Docker stack, verifying network requests, SSE streams, and CSS layouts.

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // We can enable Firefox and WebKit later if needed, but Chromium is sufficient
    // for foundational E2E verification in this lab environment.
  ],
});
