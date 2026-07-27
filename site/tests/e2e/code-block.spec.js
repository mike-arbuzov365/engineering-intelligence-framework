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

test.describe('command block copy button', () => {
  test('copies the whole command and confirms on the button', async ({ page }) => {
    await stubClipboard(page);
    await page.goto('/#quickstart');

    const button = page.locator('#quickstart .code-block__copy');
    await expect(button).toBeVisible();
    await expect(button).toHaveAttribute('aria-label', 'Copy');

    await button.click();
    const copied = await page.evaluate(() => window.__copied);
    expect(copied).toHaveLength(1);
    expect(copied[0]).toContain('pip install .');
    expect(copied[0]).toContain('eifctl init');

    // The confirmation is the button changing, not a toast that covers the
    // thing you just copied.
    await expect(button).toHaveClass(/is-copied/);
    await expect(button).toHaveAttribute('aria-label', 'Copied');
    // And it resets, so the block does not sit in a stale success state.
    await expect(button).not.toHaveClass(/is-copied/, { timeout: 4000 });
  });

  test('a refused clipboard does not show a check mark', async ({ page }) => {
    await stubClipboard(page, { fail: true });
    await page.goto('/#quickstart');
    const button = page.locator('#quickstart .code-block__copy');
    await button.click();
    // A check mark over an empty clipboard is worse than no button at all.
    await expect(button).not.toHaveClass(/is-copied/);
    await expect(button).toHaveAttribute('aria-label', 'Copy');
  });

  test('the button and its labels translate', async ({ page }) => {
    await stubClipboard(page);
    await page.goto('/#quickstart');
    await page.locator('#lang-toggle').click();

    const button = page.locator('#quickstart .code-block__copy');
    await expect(button).toHaveAttribute('aria-label', 'Копіювати');
    // Rebinding after a language swap is the part that breaks silently: the
    // markup is replaced, so the previous listener is on a detached node.
    await button.click();
    await expect(button).toHaveAttribute('aria-label', 'Скопійовано');
    const copied = await page.evaluate(() => window.__copied);
    expect(copied[0]).toContain('--locale uk');
  });
});

test.describe('command block no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('the command is readable and no dead button is offered', async ({ page }) => {
    await page.goto('/#quickstart');
    await expect(page.locator('#quickstart .quickstart__command')).toContainText('pip install .');
    // Without a script the button cannot copy anything, so it is not shown
    // rather than presented as a control that silently does nothing.
    await expect(page.locator('#quickstart .code-block__copy')).toBeHidden();
  });
});
