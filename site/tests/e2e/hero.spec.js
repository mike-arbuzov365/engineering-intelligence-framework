import { test, expect } from '@playwright/test';

test.describe('hero', () => {
  test('product name is the loudest element and three CTAs are present', async ({ page }) => {
    await page.goto('/');
    const h1Text = (await page.textContent('h1.hero__name'))?.replace(/\s+/g, ' ').trim();
    expect(h1Text).toContain('Engineering Intelligence Framework');
    await expect(page.locator('.hero__ctas a')).toHaveCount(3);
  });

  test('no horizontal overflow at the configured viewport', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(700);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflow).toBe(false);
  });

  test('reduced motion: hero content is final-state immediately, no animation applied', async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');
    const { opacity, animationName } = await page.evaluate(() => {
      const style = getComputedStyle(document.querySelector('.hero__name'));
      return { opacity: style.opacity, animationName: style.animationName };
    });
    expect(opacity).toBe('1');
    expect(animationName).toBe('none');
  });

  test('keyboard: skip link, then the language toggle, then the three hero CTAs are reachable in order', async ({
    page,
  }) => {
    await page.goto('/');
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveClass('skip-link');

    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveId('lang-toggle');

    for (const label of ['The control plane', 'The evidence loop', 'Current evidence']) {
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus')).toHaveText(label);
    }
  });

  test('no third-party network requests on hero load', async ({ page }) => {
    const external = [];
    page.on('request', (req) => {
      const url = new URL(req.url());
      if (url.hostname !== 'localhost' && url.hostname !== '127.0.0.1') {
        external.push(req.url());
      }
    });
    await page.goto('/');
    expect(external).toEqual([]);
  });
});

test.describe('hero no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('hero content and CTA hrefs are present without a script running', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#lang-toggle')).toBeHidden();
    const h1Text = (await page.textContent('h1.hero__name'))?.replace(/\s+/g, ' ').trim();
    expect(h1Text).toContain('Engineering Intelligence Framework');
    const hrefs = await page
      .locator('.hero__ctas a')
      .evaluateAll((els) => els.map((el) => el.getAttribute('href')));
    expect(hrefs).toEqual(['#control-plane', '#loop', '#evidence']);
  });
});
