import { test, expect } from '@playwright/test';

// D-07 layout smoke: no horizontal overflow at any of the five required
// widths. Runs once per project (desktop-1440 / mobile-390 / firefox-1440),
// independent of each project's own configured viewport.
const WIDTHS = [360, 390, 768, 1280, 1440];

test.describe('responsive layout', () => {
  for (const width of WIDTHS) {
    test(`no horizontal overflow at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto('/');
      await page.waitForTimeout(700); // let entrance animation settle
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      );
      expect(overflow, `horizontal overflow at ${width}px`).toBe(false);
    });
  }
});
