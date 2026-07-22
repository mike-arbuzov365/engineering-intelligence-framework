#!/usr/bin/env node
// One-time (maintainer-run) generator for static image assets: the 1200x630
// social preview card and PNG favicon fallbacks. Renders local HTML/SVG
// through Chromium (already a devDependency via @playwright/test) and
// screenshots it - no remote service, no paid asset, no new dependency.
// Run with: node scripts/generate-social-assets.mjs
// Output is committed to public/ like any other static site asset.

import { chromium } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, '..');
const publicDir = path.join(siteRoot, 'public');

const faviconSvg = readFileSync(path.join(publicDir, 'favicon.svg'), 'utf8');

const SOCIAL_CARD_HTML = `<!doctype html><html><head><meta charset="utf-8" />
<style>
  html,body{margin:0;padding:0;width:1200px;height:630px;background:#17181c;}
  .card{width:1200px;height:630px;display:flex;flex-direction:column;justify-content:center;
    padding:80px;box-sizing:border-box;font-family:-apple-system,"Segoe UI Variable","Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
  .eyebrow{font-family:"Cascadia Code","Cascadia Mono",ui-monospace,"SF Mono","JetBrains Mono",Consolas,monospace;
    font-size:22px;letter-spacing:0.08em;text-transform:uppercase;color:#2fd673;margin:0 0 24px;}
  h1{font-size:76px;font-weight:800;line-height:1.05;letter-spacing:-0.01em;color:#f6f1e6;margin:0 0 28px;}
  p{font-size:30px;line-height:1.4;color:#a89f8c;margin:0;max-width:920px;}
  .mark{position:absolute;top:80px;right:80px;width:64px;height:64px;}
</style></head>
<body>
  <div class="card">
    <div class="mark">${faviconSvg}</div>
    <p class="eyebrow">Engineering Intelligence Framework &middot; pre-release</p>
    <h1>A quality-first control plane<br />for governed AI-agent<br />software development.</h1>
    <p>Persistent engineering knowledge, explicit source identity, controlled execution and evidence &mdash; not chat history.</p>
  </div>
</body></html>`;

function faviconHtml(size) {
  return `<!doctype html><html><head><meta charset="utf-8" /><style>
    html,body{margin:0;padding:0;width:${size}px;height:${size}px;}
    svg{display:block;width:${size}px;height:${size}px;}
  </style></head><body>${faviconSvg}</body></html>`;
}

async function screenshot(browser, html, width, height, outPath) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.setContent(html);
  await page.screenshot({ path: outPath, clip: { x: 0, y: 0, width, height } });
  await page.close();
  console.log(`wrote ${path.relative(siteRoot, outPath)} (${width}x${height})`);
}

const browser = await chromium.launch();
await screenshot(browser, SOCIAL_CARD_HTML, 1200, 630, path.join(publicDir, 'social-card.png'));
await screenshot(browser, faviconHtml(48), 48, 48, path.join(publicDir, 'favicon.png'));
await screenshot(browser, faviconHtml(180), 180, 180, path.join(publicDir, 'apple-touch-icon.png'));
await browser.close();
