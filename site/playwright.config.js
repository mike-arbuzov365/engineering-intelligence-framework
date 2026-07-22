import { defineConfig, devices } from '@playwright/test';

const PORT = 5183;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  // Capped rather than the CPU-core default: full parallelism across three
  // projects (two Chromium + Firefox) produced real Firefox timeouts under
  // load when chained after other browser-heavy steps in gate-site.mjs -
  // Firefox measured consistently slower per-test on this host even
  // uncontended (5-15s vs 1-3s for Chromium), so it has the least headroom.
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
    {
      name: 'desktop-1440',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'mobile-390',
      use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 } },
    },
    {
      // Independent-engine coverage (D-07): same full flow set, Firefox
      // instead of Chromium.
      name: 'firefox-1440',
      use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 900 } },
    },
  ],
});
