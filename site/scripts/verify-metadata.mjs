#!/usr/bin/env node
// Metadata/social-asset verifier (D-09, Session 004). Checks source-level
// state: required meta tags exist, the build-time placeholder markers the
// eif-metadata Vite plugin substitutes are present, and the social card PNG
// is exactly 1200x630 - all without needing a build first.

import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, '..');

function pngDimensions(file) {
  const buf = readFileSync(file);
  const signature = buf.subarray(0, 8).toString('hex');
  if (signature !== '89504e470d0a1a0a') {
    throw new Error(`${file} is not a PNG file`);
  }
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

const failures = [];

const html = readFileSync(path.join(siteRoot, 'index.html'), 'utf8');

const REQUIRED_HTML_MARKERS = [
  '<title>',
  'name="description"',
  'property="og:title"',
  'property="og:description"',
  'property="og:image"',
  'name="twitter:card"',
  'rel="icon"',
  'rel="apple-touch-icon"',
  '__EIF_REPO_CTA_HREF__',
  '__EIF_REPO_CTA_LABEL__',
];

for (const marker of REQUIRED_HTML_MARKERS) {
  if (!html.includes(marker)) {
    failures.push(`index.html is missing required marker: ${marker}`);
  }
}

if (/property="og:image"\s+content="https?:\/\//.test(html)) {
  failures.push('source og:image must stay relative; the production build emits the owner URL as an absolute value');
}

const requiredAssets = ['favicon.svg', 'favicon.png', 'apple-touch-icon.png', 'social-card.png'];
for (const asset of requiredAssets) {
  const assetPath = path.join(siteRoot, 'public', asset);
  try {
    readFileSync(assetPath);
  } catch {
    failures.push(`missing required public asset: public/${asset}`);
  }
}

try {
  const { width, height } = pngDimensions(path.join(siteRoot, 'public', 'social-card.png'));
  if (width !== 1200 || height !== 630) {
    failures.push(`public/social-card.png must be exactly 1200x630, found ${width}x${height}`);
  }
} catch (err) {
  failures.push(`could not read public/social-card.png dimensions: ${err.message}`);
}

console.log(`[verify-metadata] checked index.html markers, public assets, social-card dimensions`);
for (const f of failures) console.log(`  FAIL :: ${f}`);

if (failures.length > 0) {
  console.log(`[verify-metadata] FAIL (${failures.length} finding(s))`);
  process.exit(1);
}

console.log('[verify-metadata] PASS');
