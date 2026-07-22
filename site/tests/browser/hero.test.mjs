import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { chromium } from 'playwright';
import { createServer } from 'vite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, '..', '..');

let viteServer;
let browser;
let baseUrl;

before(async () => {
  viteServer = await createServer({
    root: siteRoot,
    mode: 'preview',
    server: { port: 0 },
    logLevel: 'silent',
  });
  await viteServer.listen();
  const address = viteServer.httpServer.address();
  baseUrl = `http://localhost:${address.port}`;
  browser = await chromium.launch();
});

after(async () => {
  await browser?.close();
  await viteServer?.close();
});

function hasHorizontalOverflow(page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
}

test('desktop 1440x900: name is loudest, three CTAs present, no overflow', async () => {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(baseUrl);
  const h1Text = (await page.textContent('h1.hero__name')).replace(/\s+/g, ' ').trim();
  assert.match(h1Text, /Engineering Intelligence Framework/);
  assert.equal(await hasHorizontalOverflow(page), false);
  assert.equal(await page.locator('.hero__ctas a').count(), 3);
  await page.close();
});

test('mobile 390x844: content present, no overflow', async () => {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto(baseUrl);
  await page.waitForTimeout(700);
  assert.equal(await hasHorizontalOverflow(page), false);
  assert.equal(await page.locator('.hero__ctas a').count(), 3);
  const descriptorVisible = await page.locator('.hero__descriptor').isVisible();
  assert.equal(descriptorVisible, true);
  await page.close();
});

test('reduced motion: hero content is final-state immediately, no animation applied', async () => {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(baseUrl);
  const { opacity, animationName } = await page.evaluate(() => {
    const style = getComputedStyle(document.querySelector('.hero__name'));
    return { opacity: style.opacity, animationName: style.animationName };
  });
  assert.equal(opacity, '1');
  assert.equal(animationName, 'none');
  await context.close();
});

test('JS disabled: hero content and CTA hrefs are present without a script running', async () => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto(baseUrl);
  const h1Text = (await page.textContent('h1.hero__name')).replace(/\s+/g, ' ').trim();
  assert.match(h1Text, /Engineering Intelligence Framework/);
  const hrefs = await page
    .locator('.hero__ctas a')
    .evaluateAll((els) => els.map((el) => el.getAttribute('href')));
  assert.deepEqual(hrefs, ['#control-plane', '#loop', '#evidence']);
  await context.close();
});

test('keyboard: skip link then the three hero CTAs are reachable in order', async () => {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(baseUrl);
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.className), 'skip-link');

  for (const label of ['The control plane', 'The evidence loop', 'Current evidence']) {
    await page.keyboard.press('Tab');
    const text = await page.evaluate(() => document.activeElement.textContent.trim());
    assert.equal(text, label);
  }
  await context.close();
});

test('no third-party network requests on hero load', async () => {
  const context = await browser.newContext();
  const page = await context.newPage();
  const externalRequests = [];
  page.on('request', (req) => {
    const url = new URL(req.url());
    if (url.hostname !== 'localhost' && url.hostname !== '127.0.0.1') {
      externalRequests.push(req.url());
    }
  });
  await page.goto(baseUrl);
  assert.deepEqual(externalRequests, []);
  await context.close();
});
