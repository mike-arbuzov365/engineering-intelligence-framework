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

  test('the hero mark is the orbit, unkeyed, and the circuit moved to section 03', async ({
    page,
  }) => {
    await page.goto('/');
    // A hero is a poster. The key that used to sit under it went with the
    // circuit diagram to section 03, where a diagram and its key belong.
    await expect(page.locator('.hero__legend')).toHaveCount(0);
    await expect(page.locator('.hero .hero__aside .figure-legend')).toHaveCount(0);
    await expect(page.locator('.hero .scale__map')).toHaveCount(1);
    await expect(page.locator('.hero .scale__core-label')).toHaveText('EIF');

    // The circuit is in the layers figure now, and it kept its five-line key.
    await expect(page.locator('#layers .scale .hero__shelf')).toHaveCount(3);
    await expect(page.locator('#layers .scale .figure-legend__item')).toHaveCount(5);
    await expect(page.locator('.hero .hero__shelf')).toHaveCount(0);
  });

  test('the hero mark translates its route notes with the page', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.hero .scale__note').first()).toHaveText('method + experience');
    await page.locator('#lang-toggle').click();
    await expect(page.locator('.hero .scale__note').first()).toHaveText('метод і досвід');
    // Proper nouns stay put in both languages.
    await expect(page.locator('.hero .scale__core-label')).toHaveText('EIF');
  });

  test('hero figure stops animating once the hero is scrolled away', async ({ page }) => {
    await page.goto('/');
    const mark = page.locator('.hero .scale__session--1');
    const circuit = page.locator('#layers .scale .hero__settled--1');
    const playState = (locator) =>
      locator.evaluate((el) => getComputedStyle(el).animationPlayState);

    expect(await playState(mark)).toBe('running');

    // Far enough that no part of the full-height hero is intersecting.
    await page.evaluate(() => window.scrollTo(0, 4000));
    await expect(page.locator('.hero .hero__figure')).toHaveClass(/is-paused/);
    expect(await playState(mark)).toBe('paused');
    // The circuit shares the class name but is a different figure in a
    // different section, and must not be paused by the hero leaving view.
    expect(await playState(circuit)).toBe('running');

    // Resumes rather than restarting, so returning to the top does not
    // replay the accumulation from empty.
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(page.locator('.hero .hero__figure')).not.toHaveClass(/is-paused/);
    expect(await playState(mark)).toBe('running');
  });

  test('the pause observer survives a language swap', async ({ page }) => {
    await page.goto('/');
    // The hero mark now lives inside an i18n block, so switching language
    // replaces the SVG node and leaves the previous observer holding a
    // detached element.
    await page.locator('#lang-toggle').click();
    await page.evaluate(() => window.scrollTo(0, 4000));
    await expect(page.locator('.hero .hero__figure')).toHaveClass(/is-paused/);
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(page.locator('.hero .hero__figure')).not.toHaveClass(/is-paused/);
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
