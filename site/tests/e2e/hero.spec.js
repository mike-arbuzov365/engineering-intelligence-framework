import { test, expect } from '@playwright/test';

test.describe('hero', () => {
  test('product name is the loudest element and four CTAs are present', async ({ page }) => {
    await page.goto('/');
    const h1Text = (await page.textContent('h1.hero__name'))?.replace(/\s+/g, ' ').trim();
    expect(h1Text).toContain('Engineering Intelligence Framework');
    await expect(page.locator('.hero__ctas a')).toHaveCount(4);
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

  test('keyboard: skip link, then the language toggle, then the four hero CTAs are reachable in order', async ({
    page,
  }) => {
    await page.goto('/');
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveClass('skip-link');

    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveId('lang-toggle');

    for (const label of ['What EIF is', 'The three layers', 'How it learns', 'Current evidence']) {
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus')).toHaveText(label);
    }
  });

  test('the figure key is bound to the figure it explains', async ({ page }) => {
    await page.goto('/');
    const geometry = await page.evaluate(() => {
      const figure = document.querySelector('.hero__figure').getBoundingClientRect();
      const legend = document.querySelector('.hero__legend');
      const legendBox = legend.getBoundingClientRect();
      const firstItem = legend
        .querySelector('.figure-legend__item')
        .getBoundingClientRect();
      return {
        figureWidth: figure.width,
        legendWidth: legendBox.width,
        ruleToFirstLine: firstItem.top - legendBox.top,
      };
    });
    // main.js imports sections.css after hero.css, so at equal specificity
    // .figure-legend's own `padding: 0` and `max-width` used to win here: the
    // rule sat 1px above the first line and ran 48px wider than the figure.
    expect(Math.abs(geometry.legendWidth - geometry.figureWidth)).toBeLessThan(1);
    expect(geometry.ruleToFirstLine).toBeGreaterThanOrEqual(24);
  });

  test('hero figure stops animating once the hero is scrolled away', async ({ page }) => {
    await page.goto('/');
    const mark = page.locator('.hero__settled--1');
    const playState = () =>
      mark.evaluate((el) => getComputedStyle(el).animationPlayState);

    expect(await playState()).toBe('running');

    // Far enough that no part of the full-height hero is intersecting.
    await page.evaluate(() => window.scrollTo(0, 4000));
    await expect(page.locator('.hero__figure')).toHaveClass(/is-paused/);
    expect(await playState()).toBe('paused');

    // Resumes rather than restarting, so returning to the top does not
    // replay the accumulation from empty.
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(page.locator('.hero__figure')).not.toHaveClass(/is-paused/);
    expect(await playState()).toBe('running');
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
    expect(hrefs).toEqual(['#methodology', '#layers', '#learning', '#evidence']);
  });
});
