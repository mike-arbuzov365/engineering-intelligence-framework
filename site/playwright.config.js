import { defineConfig, devices } from '@playwright/test';

const PORT = 5183;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  // Capped rather than the CPU-core default. Engine-independent content
  // assertions run once on desktop Chromium; mobile and Firefox use bounded
  // behavioral smoke files. This preserves D-07 coverage without tripling
  // every static assertion or spending hosted/local browser time on copies.
  workers: 4,
  timeout: 45_000,
  reporter: [['list']],
  use: {
    baseURL: process.env.EIF_TEST_BASE_URL ?? `http://127.0.0.1:${PORT}`,
    trace: 'off',
    video: 'off',
    screenshot: 'off',
  },
  projects: [
    {
      name: 'desktop-1440',
      testIgnore: [/(mobile|firefox)-smoke\.spec\.js/],
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'mobile-390',
      testMatch: /mobile-smoke\.spec\.js/,
      use: { ...devices['Pixel 5'], viewport: { width: 390, height: 844 } },
    },
    {
      // Independent-engine coverage (D-07): targeted rendered/interactive
      // behavior rather than duplicate content assertions.
      name: 'firefox-1440',
      testMatch: /firefox-smoke\.spec\.js/,
      use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 900 } },
    },
  ],
});
