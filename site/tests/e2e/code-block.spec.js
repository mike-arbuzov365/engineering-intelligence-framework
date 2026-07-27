import { test, expect } from '@playwright/test';

// The real clipboard is permission-gated and differs per browser, so these
// stub navigator.clipboard and assert what the page does with it: what text
// it hands over, and that the confirmation only appears when the write
// succeeded.
async function stubClipboard(page, { fail = false } = {}) {
  await page.addInitScript((shouldFail) => {
    window.__copied = [];
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: (text) => {
          if (shouldFail) return Promise.reject(new Error('denied'));
          window.__copied.push(text);
          return Promise.resolve();
        },
      },
    });
    // The selection fallback is unavailable in this stub too, so a failed
    // write stays failed and the button must not confirm.
    if (shouldFail) document.execCommand = () => false;
  }, fail);
}

// The quickstart carries four command blocks now (three platform panels plus
// the shared init line), so every locator here names the one it means.
const UNIX_COPY = '#install-panel-unix .code-block__copy';
const INIT_COPY = '.install__step:last-child .code-block__copy';

test.describe('command block copy button', () => {
  test('copies the whole command and confirms on the button', async ({ page }) => {
    await stubClipboard(page);
    await page.goto('/#quickstart');

    const button = page.locator(UNIX_COPY);
    await expect(button).toBeVisible();
    await expect(button).toHaveAttribute('aria-label', 'Copy');

    await button.click();
    const copied = await page.evaluate(() => window.__copied);
    expect(copied).toHaveLength(1);
    expect(copied[0]).toContain('git clone');
    expect(copied[0]).toContain('pip install .');

    // The confirmation is the button changing, not a toast that covers the
    // thing you just copied.
    await expect(button).toHaveClass(/is-copied/);
    await expect(button).toHaveAttribute('aria-label', 'Copied');
    // And it resets, so the block does not sit in a stale success state.
    await expect(button).not.toHaveClass(/is-copied/, { timeout: 4000 });
  });

  test('the init block copies the init line, not the install one', async ({ page }) => {
    await stubClipboard(page);
    await page.goto('/#quickstart');

    await page.locator(INIT_COPY).click();
    const copied = await page.evaluate(() => window.__copied);
    expect(copied[0]).toContain('eifctl init');
    expect(copied[0]).not.toContain('git clone');
  });

  test('the tooltip names the button, and names what just happened', async ({ page }) => {
    await stubClipboard(page);
    await page.goto('/#quickstart');

    const button = page.locator(UNIX_COPY);
    const tip = page.locator('#figure-tip');

    // An icon-only control with no hover label is a control nobody can read.
    await button.hover();
    await expect(tip).toHaveClass(/is-visible/);
    await expect(tip).toHaveText('Copy');

    // And the same tooltip is where a pointer user is told the copy landed.
    await button.click();
    await expect(tip).toHaveText('Copied');
    await expect(tip).toHaveText('Copy', { timeout: 4000 });
  });

  test('a refused clipboard does not show a check mark', async ({ page }) => {
    await stubClipboard(page, { fail: true });
    await page.goto('/#quickstart');
    const button = page.locator(UNIX_COPY);
    await button.click();
    // A check mark over an empty clipboard is worse than no button at all.
    await expect(button).not.toHaveClass(/is-copied/);
    await expect(button).toHaveAttribute('aria-label', 'Copy');
  });

  test('the button and its labels translate', async ({ page }) => {
    await stubClipboard(page);
    await page.goto('/#quickstart');
    await page.locator('#lang-toggle').click();

    const button = page.locator(INIT_COPY);
    await expect(button).toHaveAttribute('aria-label', 'Копіювати');
    // Rebinding after a language swap is the part that breaks silently: the
    // markup is replaced, so the previous listener is on a detached node.
    await button.click();
    await expect(button).toHaveAttribute('aria-label', 'Скопійовано');
    const copied = await page.evaluate(() => window.__copied);
    expect(copied[0]).toContain('--locale uk');
  });
});

test.describe('install tabs', () => {
  test('shows one platform at a time and switches on click', async ({ page }) => {
    await page.goto('/#quickstart');

    const unix = page.locator('#install-panel-unix');
    const pwsh = page.locator('#install-panel-pwsh');
    const cmd = page.locator('#install-panel-cmd');

    await expect(unix).toBeVisible();
    await expect(pwsh).toBeHidden();
    await expect(cmd).toBeHidden();
    await expect(unix).toContainText('source .venv/bin/activate');

    await page.locator('#install-tab-pwsh').click();
    await expect(pwsh).toBeVisible();
    await expect(unix).toBeHidden();
    await expect(page.locator('#install-tab-pwsh')).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('#install-tab-unix')).toHaveAttribute('aria-selected', 'false');
    // The one shell difference a reader would otherwise hit as an error.
    await expect(pwsh).toContainText('Activate.ps1');
    await expect(pwsh).toContainText('PowerShell 5.1');

    await page.locator('#install-tab-cmd').click();
    await expect(cmd).toBeVisible();
    await expect(cmd).toContainText('activate.bat');
  });

  test('arrow keys move between tabs and only the selected one is a tab stop', async ({ page }) => {
    await page.goto('/#quickstart');

    await page.locator('#install-tab-unix').focus();
    await expect(page.locator('#install-tab-pwsh')).toHaveAttribute('tabindex', '-1');

    await page.keyboard.press('ArrowRight');
    await expect(page.locator('#install-tab-pwsh')).toBeFocused();
    await expect(page.locator('#install-panel-pwsh')).toBeVisible();

    await page.keyboard.press('End');
    await expect(page.locator('#install-tab-cmd')).toBeFocused();

    // Wraps, because a tablist that dead-ends at its last tab is a tablist
    // that behaves differently from every other one the reader has used.
    await page.keyboard.press('ArrowRight');
    await expect(page.locator('#install-tab-unix')).toBeFocused();
  });

  test('the step 01 platform choice does not change the init line', async ({ page }) => {
    await page.goto('/#quickstart');
    const init = page.locator('.install__init-command');
    await expect(init).toContainText('eifctl init');
    await page.locator('#install-tab-cmd').click();
    await expect(init).toContainText('eifctl init');
    await expect(init).toBeVisible();
  });
});

test.describe('command block no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('every platform is readable and no dead control is offered', async ({ page }) => {
    await page.goto('/#quickstart');

    // Without a script no tab can switch, so all three panels stay open and
    // each carries its own heading rather than a strip that does nothing.
    await expect(page.locator('#install-panel-unix')).toBeVisible();
    await expect(page.locator('#install-panel-pwsh')).toBeVisible();
    await expect(page.locator('#install-panel-cmd')).toBeVisible();
    await expect(page.locator('#quickstart .install__tablist')).toBeHidden();
    await expect(page.locator('#install-panel-pwsh .install__panel-title')).toBeVisible();

    await expect(page.locator('.install__init-command')).toContainText('eifctl init');
    // The button cannot copy anything, so it is not shown rather than
    // presented as a control that silently does nothing.
    await expect(page.locator(UNIX_COPY)).toBeHidden();
  });
});
