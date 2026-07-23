import { defineConfig, devices } from '@playwright/test';

// Separate from playwright.config.js (testDir: tests/e2e) so `test:a11y` and
// `test:e2e` stay independently invocable, per SESSION-005's verification
// list. Both suites receive their explicit local server URL from the
// single-process runner in scripts/run-playwright.mjs.
const PORT = 5184;

export default defineConfig({
  testDir: './tests/a11y',
  // Run engine audits sequentially. Parallel Firefox + Chromium teardown on
  // this Windows host can race inside Firefox session-store cleanup and fail
  // browserContext.close after the axe result itself has completed.
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  reporter: [['list']],
  use: {
    baseURL: process.env.EIF_TEST_BASE_URL ?? `http://127.0.0.1:${PORT}`,
    trace: 'off',
    video: 'off',
    screenshot: 'off',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    {
      name: 'firefox',
      grep: /full page/,
      use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 900 } },
    },
  ],
});
