import { test, expect } from '@playwright/test';

test('Firefox renders the full methodology without overflow', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#layers .layers__layer')).toHaveCount(3);
  await expect(page.locator('#session .session__timeline li')).toHaveCount(4);
  await expect(page.locator('#learning .learning__flow li')).toHaveCount(6);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(overflow).toBe(false);
});

test('Firefox supports language, disclosure and keyboard loop navigation', async ({ page }) => {
  await page.goto('/');
  await page.locator('#lang-toggle').click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'uk');

  const trigger = page.locator('#integrations .reveal__trigger').first();
  await trigger.click();
  await expect(trigger).toHaveAttribute('aria-expanded', 'true');

  const node = page.locator('.loop__node[data-phase="adapt"]');
  await node.focus();
  await page.keyboard.press('Enter');
  await expect(node).toHaveAttribute('aria-current', 'step');
});

test('Firefox reduced-motion path has no hero animation', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.locator('.hero__name')).toHaveCSS('animation-name', 'none');
});

test.describe('Firefox no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('static reading path stays complete', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#lang-toggle')).toBeHidden();
    await expect(page.locator('#evidence .reveal__detail')).toHaveCount(8);
    await expect(page.locator('#evidence .reveal__detail').last()).toBeVisible();
  });
});
