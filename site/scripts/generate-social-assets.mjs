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
const frameworkRoot = path.resolve(siteRoot, '..');

const faviconSvg = readFileSync(path.join(publicDir, 'favicon.svg'), 'utf8');
const orbitSvg = readFileSync(
  path.join(siteRoot, 'src', 'partials', 'orbit-figure.en.html'),
  'utf8',
);

const ORBIT_STYLES = `
  .orbit{display:block;height:auto;}
  .orbit .svg-hit{display:none;}
  .orbit .scale__orbit{stroke:#55565c;stroke-width:1;stroke-dasharray:2 6;fill:none;}
  .orbit .scale__spoke,.orbit .scale__stem{stroke:#35363b;stroke-width:1;}
  .orbit .scale__packet-rule{stroke:#1f9a53;stroke-width:1.5;}
  .orbit .scale__core{fill:#17181c;stroke:#2fd673;stroke-width:2;}
  .orbit .scale__core-label{font-family:"Cascadia Code","Cascadia Mono",ui-monospace,
    "SF Mono","JetBrains Mono",Consolas,monospace;font-size:17px;letter-spacing:.08em;fill:#f6f1e6;}
  .orbit .scale__project circle{fill:#17181c;stroke:#a89f8c;stroke-width:1.5;}
  .orbit .scale__project--active circle{stroke:#2fd673;stroke-width:2;}
  .orbit .scale__project--receiving circle{stroke:#1f9a53;stroke-dasharray:4 3;}
  .orbit .scale__node-label,.orbit .scale__section-label{font-family:"Cascadia Code",
    "Cascadia Mono",ui-monospace,"SF Mono","JetBrains Mono",Consolas,monospace;
    font-size:13px;letter-spacing:.05em;fill:#a89f8c;}
  .orbit .scale__note{font-family:"Cascadia Code","Cascadia Mono",ui-monospace,
    "SF Mono","JetBrains Mono",Consolas,monospace;font-size:12px;letter-spacing:.04em;fill:#a89f8c;}
  .orbit .scale__note--up{fill:#1f9a53;}
  .orbit .scale__note--relay{fill:#c77d2e;opacity:.9;}
  .orbit .scale__session circle{fill:#17181c;stroke:#2fd673;stroke-width:1.5;}
  .orbit .scale__session .scale__node-label{font-size:11px;}
  .orbit .scale__lift{stroke:#2fd673;stroke-width:1.5;}
  .orbit .scale__descend{stroke:#a89f8c;stroke-width:1;stroke-dasharray:2 6;}
  .orbit .scale__lift--relay{stroke:#1f9a53;stroke-dasharray:5 4;}
  .orbit .scale__ripple{stroke:#2fd673;stroke-width:2;fill:none;opacity:.45;}
  .orbit .scale__ripple--p3{stroke:#1f9a53;}
  .orbit .scale__curator-ring{stroke:#c77d2e;stroke-width:1;stroke-dasharray:1 5;
    fill:none;opacity:.65;}
  .orbit .scale__curator-halo{fill:#c77d2e;opacity:.15;}
  .orbit .scale__curator-dot{fill:#c77d2e;}
  .orbit .scale__pulse{display:none;}
`;

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
    <p class="eyebrow">Engineering Intelligence Framework &middot; v0.1.1</p>
    <h1>A quality-first control plane<br />for governed AI-agent<br />software development.</h1>
    <p>Persistent engineering knowledge, explicit source identity, controlled execution and evidence, not chat history.</p>
  </div>
</body></html>`;

// GitHub's repository social preview, 1280x640 (its own recommended size,
// and a clean 2:1 rather than the 1.905:1 Open Graph card). Same design
// language, different job: the site's card leads with the tagline because a
// post already carries the title, while a repository card is the
// repository's identity, so the name leads and the tagline supports it.
//
// Written to .github/ rather than site/public/: the site never serves this
// file, and putting it under public/ would copy a six-figure PNG into every
// dist/ for nothing. Generated here anyway because it shares one brand
// source with the rest, and a second script would be a second place for the
// design to drift.
const GITHUB_PREVIEW_HTML = `<!doctype html><html><head><meta charset="utf-8" />
<style>
  html,body{margin:0;padding:0;width:1280px;height:640px;background:#17181c;}
  .card{position:relative;width:1280px;height:640px;overflow:hidden;padding:70px 64px;
    box-sizing:border-box;font-family:-apple-system,"Segoe UI Variable","Segoe UI",Roboto,
    "Helvetica Neue",Arial,sans-serif;}
  .card::after{content:"";position:absolute;left:-80px;right:-80px;bottom:-118px;height:230px;
    border-top:2px solid #212226;transform:rotate(4deg);}
  .copy{position:relative;z-index:2;width:760px;}
  .eyebrow{font-family:"Cascadia Code","Cascadia Mono",ui-monospace,"SF Mono",
    "JetBrains Mono",Consolas,monospace;font-size:20px;letter-spacing:.07em;color:#2fd673;
    margin:0 0 22px;}
  h1{font-size:68px;font-weight:800;line-height:1.02;letter-spacing:-.015em;
    color:#f6f1e6;margin:0 0 28px;}
  p{font-size:27px;line-height:1.38;color:#a89f8c;margin:0;max-width:720px;}
  .rule{width:104px;height:3px;background:#2fd673;margin:0 0 28px;}
  .foot{font-family:"Cascadia Code","Cascadia Mono",ui-monospace,"SF Mono","JetBrains Mono",Consolas,monospace;
    font-size:18px;letter-spacing:.04em;color:#6f7078;margin:34px 0 0;}
  .orbit{position:absolute;z-index:1;right:16px;top:46px;width:390px;opacity:.96;}
  ${ORBIT_STYLES}
</style></head>
<body>
  <div class="card">
    <div class="copy">
      <p class="eyebrow">mike-arbuzov365 / engineering-intelligence-framework</p>
      <div class="rule"></div>
      <h1>Engineering<br />Intelligence Framework</h1>
      <p>A quality-first control plane for governed AI-agent software development.</p>
      <p class="foot">v0.1.1 &nbsp;&middot;&nbsp; Apache-2.0 &nbsp;&middot;&nbsp; Python 3.11+</p>
    </div>
    <div class="orbit">${orbitSvg}</div>
  </div>
</body></html>`;

// LinkedIn's background image is a much wider 4:1 canvas. The lower-left
// stays intentionally quiet because the profile photo overlaps that area
// on desktop and mobile. The same orbit source is used here so the website,
// repository preview and profile banner cannot drift into three brands.
const LINKEDIN_BANNER_HTML = `<!doctype html><html><head><meta charset="utf-8" />
<style>
  html,body{margin:0;padding:0;width:1584px;height:396px;background:#17181c;}
  .card{position:relative;width:1584px;height:396px;overflow:hidden;
    font-family:-apple-system,"Segoe UI Variable","Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
  .card::before{content:"";position:absolute;left:-80px;right:-80px;bottom:-112px;height:190px;
    border-top:2px solid #212226;transform:rotate(3deg);}
  .copy{position:absolute;z-index:2;left:340px;top:48px;width:820px;}
  .eyebrow{font-family:"Cascadia Code","Cascadia Mono",ui-monospace,"SF Mono",
    "JetBrains Mono",Consolas,monospace;font-size:17px;letter-spacing:.09em;
    text-transform:uppercase;color:#2fd673;margin:0 0 18px;}
  .rule{width:92px;height:3px;background:#2fd673;margin:0 0 21px;}
  h1{font-size:48px;font-weight:800;line-height:1.03;letter-spacing:-.015em;
    color:#f6f1e6;margin:0 0 14px;}
  .tagline{font-size:26px;line-height:1.3;color:#a89f8c;margin:0;}
  .site{font-family:"Cascadia Code","Cascadia Mono",ui-monospace,"SF Mono",
    "JetBrains Mono",Consolas,monospace;font-size:18px;letter-spacing:.025em;
    color:#6f7078;margin:24px 0 0;}
  ${ORBIT_STYLES}
  .orbit{position:absolute;z-index:1;right:96px;top:14px;width:286px;opacity:.98;}
  .orbit .scale__orbit{stroke-width:1.6;}
  .orbit .scale__spoke,.orbit .scale__stem{stroke-width:1.4;}
  .orbit .scale__packet-rule,.orbit .scale__lift{stroke-width:2;}
  .orbit .scale__core{stroke-width:2.6;}
  .orbit .scale__project circle{stroke-width:2;}
  .orbit .scale__project--active circle{stroke-width:2.6;}
  .orbit .scale__project--receiving circle{stroke-width:2.4;}
  .orbit .scale__core-label{font-size:20px;}
  .orbit .scale__node-label,.orbit .scale__section-label{font-size:15px;}
  .orbit .scale__note{font-size:14px;}
  .orbit .scale__session .scale__node-label{font-size:13px;}
  .orbit .scale__descend{stroke-width:1.4;}
  .orbit .scale__ripple{stroke-width:2.6;}
  .orbit .scale__curator-ring{stroke-width:1.4;}
</style></head>
<body>
  <div class="card">
    <div class="copy">
      <p class="eyebrow">Engineering Intelligence Framework</p>
      <div class="rule"></div>
      <h1>A quality-first control plane</h1>
      <p class="tagline">for governed AI-agent software development.</p>
      <p class="site">mike-arbuzov365.github.io/engineering-intelligence-framework/</p>
    </div>
    <div class="orbit">${orbitSvg}</div>
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
  console.log(`wrote ${path.relative(frameworkRoot, outPath)} (${width}x${height})`);
}

const browser = await chromium.launch();
await screenshot(browser, SOCIAL_CARD_HTML, 1200, 630, path.join(publicDir, 'social-card.png'));
await screenshot(
  browser,
  GITHUB_PREVIEW_HTML,
  1280,
  640,
  path.join(frameworkRoot, '.github', 'social-preview.png'),
);
await screenshot(
  browser,
  LINKEDIN_BANNER_HTML,
  1584,
  396,
  path.join(frameworkRoot, '.github', 'linkedin-banner.png'),
);
await screenshot(browser, faviconHtml(48), 48, 48, path.join(publicDir, 'favicon.png'));
await screenshot(browser, faviconHtml(180), 180, 180, path.join(publicDir, 'apple-touch-icon.png'));
await browser.close();
