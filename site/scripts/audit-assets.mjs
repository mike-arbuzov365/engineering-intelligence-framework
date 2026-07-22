#!/usr/bin/env node
// Byte-budget audit against D-08 (private planning repo, ratified). Reads an
// already-built dist/ (run `npm run build:preview` first) and gzips each
// file with Node's built-in zlib - no new dependency.
// Usage: node scripts/audit-assets.mjs [dist-dir]

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, '..');
const distDir = path.resolve(siteRoot, process.argv[2] ?? 'dist');

const KIB = 1024;
const BUDGETS_KIB = { js: 40, css: 50, html: 45, initialPayload: 350 };

function gzipKiB(file) {
  return gzipSync(readFileSync(file)).length / KIB;
}

function walk(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

if (!statSync(distDir, { throwIfNoEntry: false })?.isDirectory()) {
  console.error(`[audit-assets] dist dir not found: ${distDir} - run a build first`);
  process.exit(1);
}

const files = walk(distDir);
const htmlFiles = files.filter((f) => f.endsWith('.html'));
const jsFiles = files.filter((f) => f.endsWith('.js'));
const cssFiles = files.filter((f) => f.endsWith('.css'));
const excludedFromInitial = new Set(
  ['social-card.png'].map((n) => path.join(distDir, n)),
);

const jsKiB = jsFiles.reduce((sum, f) => sum + gzipKiB(f), 0);
const cssKiB = cssFiles.reduce((sum, f) => sum + gzipKiB(f), 0);
const htmlKiB = htmlFiles.reduce((sum, f) => sum + gzipKiB(f), 0);

const initialPayloadKiB = files
  .filter((f) => !excludedFromInitial.has(f))
  .reduce((sum, f) => sum + gzipKiB(f), 0);

const results = [
  ['js', jsKiB, BUDGETS_KIB.js],
  ['css', cssKiB, BUDGETS_KIB.css],
  ['html', htmlKiB, BUDGETS_KIB.html],
  ['initialPayload (excl. social-card.png)', initialPayloadKiB, BUDGETS_KIB.initialPayload],
];

let failed = false;
for (const [label, actual, budget] of results) {
  const ok = actual <= budget;
  if (!ok) failed = true;
  console.log(
    `  ${ok ? 'PASS' : 'FAIL'} :: ${label}: ${actual.toFixed(2)} KiB (budget ${budget} KiB)`,
  );
}

console.log(failed ? '[audit-assets] FAIL' : '[audit-assets] PASS');
process.exit(failed ? 1 : 0);
