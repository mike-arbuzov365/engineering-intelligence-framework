import { test, expect } from '@playwright/test';

// The tips are pointer-driven, so these dispatch pointerenter directly rather
// than relying on synthetic mouse movement landing inside a 4px SVG circle.
async function hover(page, selector) {
  await page.locator(selector).dispatchEvent('pointerenter');
}

test.describe('figure tooltips', () => {
  test('a drawn object names itself on hover', async ({ page }) => {
    await page.goto('/');
    const tip = page.locator('#figure-tip');
    await expect(tip).not.toHaveClass(/is-visible/);

    await hover(page, '.hero .scale__core');
    await expect(tip).toHaveClass(/is-visible/);
    await expect(tip).toContainText('the framework layer');

    await page.locator('.hero .scale__core').dispatchEvent('pointerleave');
    await expect(tip).not.toHaveClass(/is-visible/);
  });

  test('tips are in the language the page is showing', async ({ page }) => {
    await page.goto('/');
    const tip = page.locator('#figure-tip');
    await hover(page, '.hero .scale__core');
    await expect(tip).toContainText('One shared operating layer');

    await page.locator('#lang-toggle').click();
    // The hero mark lives in an i18n block, so the swap replaces the SVG and
    // the handlers have to be rebound against the new nodes.
    await hover(page, '.hero .scale__core');
    await expect(tip).toContainText('Спільна операційна основа');
  });

  test('every figure that carries a key also carries tips', async ({ page }) => {
    await page.goto('/');
    for (const scope of ['.hero', '#layers .scale', '#integrations', '#learning']) {
      const count = await page.locator(`${scope} [data-tip]`).count();
      expect(count, `${scope} has no hoverable objects`).toBeGreaterThan(0);
    }
  });

  test('the tip never renders off the left or right edge', async ({ page }) => {
    await page.goto('/');
    // The Graphify lane starts at the far left of its viewBox, which is the
    // case that would push a centred tip past x=0.
    await page
      .locator('#integrations .cap-flow__route[data-tip]')
      .first()
      .dispatchEvent('pointerenter');
    const box = await page.locator('#figure-tip').boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(
      (await page.viewportSize()).width,
    );
  });

  test('figures stay out of the tab order and keep their written keys', async ({ page }) => {
    await page.goto('/');
    // Tips are a shortcut for people who can see the drawing. The content
    // they carry also exists in prose beside every figure, so the shapes are
    // not focus targets and the SVGs stay decorative.
    await expect(page.locator('svg[data-tip], [data-tip][tabindex]')).toHaveCount(0);
    await expect(page.locator('#layers .scale .figure-legend__item')).toHaveCount(5);
    await expect(page.locator('#integrations .capabilities > .figure-legend')).toBeVisible();
  });
});
