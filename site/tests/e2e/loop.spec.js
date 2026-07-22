import { test, expect } from '@playwright/test';

test.describe('loop', () => {
  test('six phases are present with full text in the static list', async ({ page }) => {
    await page.goto('/#loop');
    const phases = page.locator('.loop__phase');
    await expect(phases).toHaveCount(6);
    await expect(phases.nth(0)).toContainText('Orient');
    await expect(phases.nth(5)).toContainText('Adapt');
  });

  test('exits show PASS, BLOCKED and DEFERRED with their exact conditions', async ({ page }) => {
    await page.goto('/#loop');
    const exits = page.locator('.loop__exits li');
    await expect(exits).toHaveCount(3);
    await expect(exits.nth(0)).toContainText('PASS');
    await expect(exits.nth(0)).toContainText('only when success_evidence exists');
    await expect(exits.nth(1)).toContainText('BLOCKED');
    await expect(exits.nth(2)).toContainText('DEFERRED');
  });

  test('scrolling the phase list updates the sticky diagram active node', async ({ page }) => {
    await page.goto('/');
    await page.locator('.loop__phase[data-phase="adapt"]').scrollIntoViewIfNeeded();
    await expect(page.locator('.loop__node[data-phase="adapt"]')).toHaveClass(/is-active/);
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
