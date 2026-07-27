import { test, expect } from '@playwright/test';

test('mobile poster, navigation and touch targets fit at 390x844', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1.hero__name')).toContainText('Engineering');

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(overflow).toBe(false);

  for (const selector of ['#lang-toggle', '.hero__ctas a:first-child', '.hero__ctas-repo']) {
    const box = await page.locator(selector).boundingBox();
    expect(box, `${selector} has no rendered box`).not.toBeNull();
    expect(box.height, `${selector} is shorter than 44px`).toBeGreaterThanOrEqual(44);
    expect(box.width, `${selector} is narrower than 44px`).toBeGreaterThanOrEqual(44);
  }

  const repoAlignment = await page.locator('.hero__ctas-repo').evaluate((repo) => {
    const repoRect = repo.getBoundingClientRect();
    const labelRect = repo.querySelector('.hero__ctas-label').getBoundingClientRect();
    const arrow = getComputedStyle(repo, '::after');
    return {
      labelCenter: labelRect.left + labelRect.width / 2,
      controlCenter: repoRect.left + repoRect.width / 2,
      arrowBorder: arrow.borderTopWidth,
    };
  });
  expect(repoAlignment.labelCenter).toBeLessThan(repoAlignment.controlCenter);
  expect(repoAlignment.arrowBorder).not.toBe('0px');
});

test('mobile touch switches language and toggles a disclosure both ways', async ({ page }) => {
  await page.goto('/');
  await page.locator('#lang-toggle').tap();
  await expect(page.locator('html')).toHaveAttribute('lang', 'uk');
  await expect(page.locator('.skip-link')).toHaveText('Перейти до вмісту');

  const trigger = page.locator('#integrations .reveal__trigger').first();
  const detail = page.locator('#integrations .reveal__detail').first();
  await trigger.tap();
  await expect(trigger).toHaveAttribute('aria-expanded', 'true');
  await expect(detail).not.toHaveCSS('max-height', '0px');
  await trigger.tap();
  await expect(trigger).toHaveAttribute('aria-expanded', 'false');
  await expect(detail).toHaveCSS('max-height', '0px');
});

test('mobile touch activates a loop phase', async ({ page }) => {
  await page.goto('/#loop');
  const node = page.locator('.loop__node[data-phase="study"]');
  await node.locator('.loop__node-hit').tap();
  await expect(node).toHaveAttribute('aria-current', 'step');
  await expect(page.locator('.loop__phase[data-phase="study"]')).toBeInViewport();
});

test.describe('mobile no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('methodology and evidence remain readable without enhancement', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#lang-toggle')).toBeHidden();
    await expect(page.locator('#layers .layers__layer')).toHaveCount(3);
    await expect(page.locator('#evidence .reveal__detail')).toHaveCount(8);
    await expect(page.locator('#evidence .reveal__detail').first()).toBeVisible();
    await expect(page.locator('.loop__diagram')).toHaveAttribute('aria-hidden', 'true');
  });
});
