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

  test('the contract block leads with headings that outrank the terms below them', async ({
    page,
  }) => {
    await page.goto('/#loop');
    const titles = page.locator('.loop__control-title');
    await expect(titles).toHaveCount(2);
    await expect(titles.nth(0)).toHaveText('Preconditions');
    await expect(titles.nth(1)).toHaveText('Exits');
    await expect(page.locator('.loop__control-note')).toHaveCount(2);

    // Both headings used to be .label - the same uppercase mono as the terms
    // under them, only muted while the terms were accent green - so each
    // column was led by its quietest element.
    const sizes = await page.evaluate(() => {
      const px = (selector) =>
        parseFloat(getComputedStyle(document.querySelector(selector)).fontSize);
      return {
        title: px('.loop__control-title'),
        term: px('.loop__precondition-list dt'),
      };
    });
    expect(sizes.title).toBeGreaterThan(sizes.term);
  });

  test('the loop figure annotates itself at the same rendered size as the traced map', async ({
    page,
  }) => {
    await page.goto('/');
    const rendered = await page.evaluate(() => {
      const scaledPx = (svgSelector, textSelector) => {
        const svg = document.querySelector(svgSelector);
        const fontSize = parseFloat(
          getComputedStyle(document.querySelector(textSelector)).fontSize,
        );
        return (fontSize * svg.getBoundingClientRect().width) / svg.viewBox.baseVal.width;
      };
      return {
        loop: scaledPx('.loop__diagram', '.loop__node text'),
        ledger: scaledPx('.ledger__map', '.ledger__lane-label'),
      };
    });
    // 18px inside a 300-unit box drawn at 320px put this figure's labels at
    // ~19 CSS px while every other figure annotated itself between 10 and 13.
    expect(Math.abs(rendered.loop - rendered.ledger)).toBeLessThan(2.5);
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

  test('diagram nodes expose phase navigation to keyboard users only after enhancement', async ({
    page,
  }) => {
    await page.goto('/');
    const diagram = page.locator('.loop__diagram');
    const node = page.locator('.loop__node[data-phase="define"]');

    await expect(diagram).not.toHaveAttribute('aria-hidden', 'true');
    await expect(diagram).toHaveAttribute('role', 'group');
    await expect(node).toHaveAttribute('role', 'button');
    await expect(node).toHaveAttribute('tabindex', '0');

    await node.focus();
    await page.keyboard.press(' ');
    await expect(node).toHaveAttribute('aria-current', 'step');
    await expect(page.locator('.loop__phase[data-phase="define"]')).toBeInViewport();
  });
});

test.describe('loop no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('all six phases are readable without a script running', async ({ page }) => {
    await page.goto('/#loop');
    const text = await page.locator('.loop__phases').innerText();
    for (const word of ['Orient', 'Define', 'Act', 'Observe', 'Study', 'Adapt']) {
      expect(text.toLowerCase()).toContain(word.toLowerCase());
    }
    await expect(page.locator('.loop__diagram')).toHaveAttribute('aria-hidden', 'true');
    await expect(page.locator('.loop__node').first()).not.toHaveAttribute('tabindex', '0');
  });
});
