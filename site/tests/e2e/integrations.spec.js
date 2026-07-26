import { test, expect } from '@playwright/test';

// Scoped to #integrations throughout: .reveal / .integrations__list /
// .section__lede are shared component classes reused by later sections
// (Session 004's evidence/tasks ledger), so a bare selector here would also
// match rows/ledes that do not belong to this section.
test.describe('optional capabilities', () => {
  test('three capability bridges and rows name their fallback paths', async ({ page }) => {
    await page.goto('/#integrations');
    const rows = page.locator('#integrations .reveal');
    await expect(rows).toHaveCount(3);
    await expect(rows.nth(0)).toContainText('Graphify');
    await expect(rows.nth(1)).toContainText('RTK');
    await expect(rows.nth(2)).toContainText('Context7');
    // The install boundary is the load-bearing claim for this row: EIF ships
    // guidance and a template, it does not configure the MCP server.
    await expect(rows.nth(2)).toContainText('EIF does not install it');
    // The bridge table was a third restatement of the flow figure and these
    // rows; it is gone, and the core path is named in the figure's legend.
    await expect(page.locator('#integrations .capability-map')).toHaveCount(0);
    await expect(page.locator('#integrations .cap-flow .figure-legend')).toContainText(
      'core path',
    );
  });

  test('each row answers the boundary question while still collapsed', async ({ page }) => {
    await page.goto('/#integrations');
    const tags = page.locator('#integrations .cap-tag');
    await expect(tags).toHaveCount(3);
    await expect(tags.nth(0)).toHaveText('Local');
    await expect(tags.nth(1)).toHaveText('Local');
    await expect(tags.nth(2)).toHaveText('Network');
    // Only the Context7 row leaves the machine, and only it carries the
    // amber modifier the figure above uses for the same boundary.
    await expect(page.locator('#integrations .cap-tag--network')).toHaveCount(1);
    await expect(page.locator('#integrations .reveal').nth(2).locator('.cap-tag--network')).toHaveCount(
      1,
    );
  });

  test('boundary tags translate with the rest of the section', async ({ page }) => {
    await page.goto('/#integrations');
    await page.locator('#lang-toggle').click();
    const tags = page.locator('#integrations .cap-tag');
    await expect(tags.nth(0)).toHaveText('Локально');
    await expect(tags.nth(2)).toHaveText('Мережа');
  });

  test('the figure legend is four one-line keys, not a second body of text', async ({ page }) => {
    await page.goto('/#integrations');
    const keys = page.locator('#integrations .cap-flow .figure-legend__item');
    await expect(keys).toHaveCount(4);
    // The context box on the right went unexplained for as long as the legend
    // had only three keys.
    await expect(keys.nth(3)).toContainText('context');
  });

  test('the cost statement names the price without claiming the balance', async ({ page }) => {
    await page.goto('/#integrations');
    const cost = page.locator('.token-economics__body');
    await expect(cost).toContainText('not free in tokens');
    await expect(cost).toContainText('leaves the balance open');
    // Two labelled paragraphs of measured/not-measured accounting were the
    // bulk of this screen's overload. Their content survives as one clause.
    await expect(cost.locator('p')).toHaveCount(2);
  });

  test('the network boundary is stated the same way in both languages', async ({ page }) => {
    await page.goto('/#integrations');
    await expect(page.locator('#integrations')).toContainText('goes to the network');
    await expect(page.locator('#integrations')).not.toContainText('leaves the machine');
    await page.locator('#lang-toggle').click();
    await expect(page.locator('#integrations')).toContainText('іде в мережу');
    await expect(page.locator('#integrations')).not.toContainText('залишає машину');
  });

  test('detail reveals on focus via CSS, before any click/JS toggle', async ({ page }) => {
    await page.goto('/#integrations');
    const trigger = page.locator('#integrations .reveal__trigger').nth(0);
    const detail = page.locator('#integrations .reveal').nth(0).locator('.reveal__detail');
    await expect(detail).toHaveCSS('max-height', '0px');
    await trigger.focus();
    // Web-first assertion (auto-retrying) instead of a one-shot before/after
    // read, which raced the style recalculation on the mobile-390 project.
    await expect(detail).not.toHaveCSS('max-height', '0px');
  });

  test('tap/click toggles the row open and sets aria-expanded', async ({ page }) => {
    await page.goto('/#integrations');
    const trigger = page.locator('#integrations .reveal__trigger').nth(1);
    await expect(trigger).toHaveAttribute('aria-expanded', 'false');
    await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
  });

  test('core-safe fallback is stated for every integration, not just enabled ones', async ({
    page,
  }) => {
    await page.goto('/#integrations');
    await expect(page.locator('#integrations .section__lede')).toContainText(
      'None is the methodology itself',
    );
  });
});

test.describe('optional capabilities no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('degraded-mode text is present for all three integrations without a script', async ({
    page,
  }) => {
    await page.goto('/#integrations');
    const details = page.locator('#integrations .reveal__detail');
    await expect(details).toHaveCount(3);
    for (let index = 0; index < 3; index += 1) {
      await expect(details.nth(index)).toBeVisible();
    }
    await expect(page.locator('#integrations .reveal__trigger').first()).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    await expect(page.locator('#integrations .reveal__trigger').first()).toBeDisabled();
    const text = await page.locator('#integrations .integrations__list').innerText();
    expect(text).toContain('falls back to source search');
    expect(text).toContain('run unfiltered');
    expect(text).toContain('relies on local docs');
  });
});
