import { test, expect } from '@playwright/test';

test.describe('integrations', () => {
  test('three integration rows are present with summary always visible', async ({ page }) => {
    await page.goto('/#integrations');
    const rows = page.locator('.reveal');
    await expect(rows).toHaveCount(3);
    await expect(rows.nth(0)).toContainText('Graphify');
    await expect(rows.nth(1)).toContainText('RTK');
    await expect(rows.nth(2)).toContainText('Vendor docs');
  });

  test('detail reveals on focus via CSS, before any click/JS toggle', async ({ page }) => {
    await page.goto('/#integrations');
    const trigger = page.locator('.reveal__trigger').nth(0);
    const detail = page.locator('.reveal').nth(0).locator('.reveal__detail');
    await expect(detail).toHaveCSS('max-height', '0px');
    await trigger.focus();
    // Web-first assertion (auto-retrying) instead of a one-shot before/after
    // read, which raced the style recalculation on the mobile-390 project.
    await expect(detail).not.toHaveCSS('max-height', '0px');
  });

  test('tap/click toggles the row open and sets aria-expanded', async ({ page }) => {
    await page.goto('/#integrations');
    const trigger = page.locator('.reveal__trigger').nth(1);
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
    await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
  });

  test('core-safe fallback is stated for every integration, not just enabled ones', async ({
    page,
  }) => {
    await page.goto('/#integrations');
    await expect(page.locator('.section__lede').last()).toContainText('None of these are required');
  });
});

test.describe('integrations no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('degraded-mode text is present for all three integrations without a script', async ({
    page,
  }) => {
    await page.goto('/#integrations');
    const text = await page.locator('.integrations__list').innerText();
    expect(text).toContain('falls back to source search');
    expect(text).toContain('run unfiltered');
    expect(text).toContain('relies on local docs');
  });
});
