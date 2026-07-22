import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('axe: zero serious/critical violations on the full page', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
    .analyze();

  const blocking = results.violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical',
  );

  if (blocking.length > 0) {
    const summary = blocking
      .map((v) => `${v.id} (${v.impact}, ${v.nodes.length} node(s)): ${v.help}`)
      .join('\n');
    console.log(summary);
  }

  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});

test('axe: reduced-motion state has zero serious/critical violations', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  const blocking = results.violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical',
  );
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});
