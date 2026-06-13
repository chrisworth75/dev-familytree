// @ts-check
// Playwright config for the React SPA (port 4202). Distinct from playwright.config.js,
// which targets the Thymeleaf app on 3200.
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './e2e-react',
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:4202',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
