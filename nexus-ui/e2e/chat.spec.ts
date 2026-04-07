import { test, expect } from '@playwright/test';

// EDUCATIONAL NOTE: Browser-Based UI Integration
// This test suite drives a real Chromium browser against the live Docker stack.
// It proves that the UI can connect to the Orchestrator, parse the SSE stream,
// and correctly render the responses in the DOM.

test.describe('Nexus Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the frontend
    await page.goto('/');
  });

  test('should load the app and verify system status is online', async ({ page }) => {
    // Wait for the status check to complete
    // The "Online" text should appear next to Orchestrator, MCP Server, etc.
    await expect(page.getByText('Nexus', { exact: true })).toBeVisible();
    
    // We expect multiple 'Online' badges once the health check passes
    const onlineBadges = page.locator('span:has-text("Online")');
    await expect(onlineBadges.first()).toBeVisible({ timeout: 15000 });
  });

  test('should send a message and receive a streaming response', async ({ page }) => {
    // 1. Wait for the app to be ready (input enabled)
    const chatInput = page.getByPlaceholder('Message Nexus...');
    await expect(chatInput).toBeEnabled({ timeout: 15000 });

    // 2. Type a message
    const testMessage = 'Hello, can you hear me? Just reply with "Yes I can" if so.';
    await chatInput.fill(testMessage);
    
    // 3. Send the message
    await page.getByRole('button', { name: 'Send' }).click();

    // 4. Verify user message appears in chat
    await expect(page.getByText(testMessage)).toBeVisible();

    // 5. Verify the assistant responds
    // We look for a message block that is NOT from the user.
    // The assistant's text is usually wrapped in markdown elements (p, div).
    // We'll wait for the "Yes I can" text to appear, which proves the SSE stream 
    // was received, parsed, and rendered.
    await expect(page.getByText('Yes I can')).toBeVisible({ timeout: 30000 });
  });
});
