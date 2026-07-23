import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

function formatViolations(violations) {
  return violations
    .map((v) => `${v.id} (${v.impact ?? 'unknown'}, ${v.nodes.length} node(s)): ${v.help}`)
    .join('\n');
}

test('axe: zero WCAG A/AA violations on the full page', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
    .analyze();

  if (results.violations.length > 0) console.log(formatViolations(results.violations));
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
});

test('axe: reduced-motion state has zero WCAG A/AA violations', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  if (results.violations.length > 0) console.log(formatViolations(results.violations));
  expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
});
