import { defineConfig, devices } from '@playwright/test';

// Separate from playwright.config.js (testDir: tests/e2e) so `test:a11y` and
// `test:e2e` stay independently invocable, per SESSION-005's verification
// list. Duplicated webServer/use block is intentional - two ~10-line configs
// are simpler than a shared-config abstraction for just two files.
const PORT = 5184;

export default defineConfig({
  testDir: './tests/a11y',
  fullyParallel: true,
  workers: 4,
  timeout: 45_000,
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: 'off',
    video: 'off',
    screenshot: 'off',
  },
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 900 } } },
  ],
});
