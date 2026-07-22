import { test, expect } from '@playwright/test';

test.describe('loop', () => {
  test('six phases are present with full text in the static list', async ({ page }) => {
    await page.goto('/#loop');
    const phases = page.locator('.loop__phase');
    await expect(phases).toHaveCount(6);
    await expect(phases.nth(0)).toContainText('Orient');
    await expect(phases.nth(5)).toContainText('Adapt');
  });

  test('exits show Pass, Blocked and Deferred with their exact conditions', async ({ page }) => {
    await page.goto('/#loop');
    const exits = page.locator('.loop__exits-row');
    await expect(exits).toHaveCount(3);
    await expect(exits.nth(0)).toContainText('Pass');
    await expect(exits.nth(0)).toContainText('Only when success evidence exists');
    await expect(exits.nth(1)).toContainText('Blocked');
    await expect(exits.nth(2)).toContainText('Deferred');
  });

  test('scrolling the phase list updates the sticky diagram active node', async ({ page }) => {
    await page.goto('/');
    await page.locator('.loop__phase[data-phase="adapt"]').scrollIntoViewIfNeeded();
    await expect(page.locator('.loop__node[data-phase="adapt"]')).toHaveClass(/is-active/);
  });

  test('clicking a diagram node activates it immediately and scrolls its phase into view', async ({
    page,
  }) => {
    await page.goto('/');
    // Click the invisible hit-target circle, not the parent <g> - the
    // group's own bounding box includes its offset text label, which skews
    // a bbox-center click away from the actual dot (real bug, found via a
    // failing test: on narrow viewports the computed center landed outside
    // the group entirely and hit the parent <svg> instead).
    await page.locator('.loop__node[data-phase="study"] .loop__node-hit').click();
    await expect(page.locator('.loop__node[data-phase="study"]')).toHaveClass(/is-active/);
    await expect(page.locator('.loop__phase[data-phase="study"]')).toBeInViewport();
  });
});

test.describe('loop no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('all six phases are readable without a script running', async ({ page }) => {
    await page.goto('/#loop');
    const text = await page.locator('.loop__phases').innerText();
    for (const word of ['Orient', 'Define', 'Act', 'Observe', 'Study', 'Adapt']) {
      expect(text).toContain(word);
    }
  });
});
