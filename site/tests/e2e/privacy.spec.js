import { test, expect } from '@playwright/test';

// D-08: no third-party request, cookie, analytics or storage side effect.
test('no cookies, localStorage or sessionStorage after a normal page load', async ({
  page,
  context,
}) => {
  await page.goto('/');
  await page.waitForTimeout(700);

  const cookies = await context.cookies();
  expect(cookies).toEqual([]);

  const storage = await page.evaluate(() => ({
    documentCookie: document.cookie,
    localStorageLength: localStorage.length,
    sessionStorageLength: sessionStorage.length,
  }));
  expect(storage).toEqual({
    documentCookie: '',
    localStorageLength: 0,
    sessionStorageLength: 0,
  });
});
