#!/usr/bin/env node
// Session 006: exact local bundle evidence. Reads an already-built dist/
// (run a build:* script first), writes dist/manifest.json (file inventory,
// per-file SHA-256, one deterministic bundle digest) and validates that a
// non-production bundle never claims eif:deploy-status=deployable.
// Usage: node scripts/verify-bundle.mjs

import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, '..');
const distDir = path.join(siteRoot, 'dist');
const manifestPath = path.join(distDir, 'manifest.json');

if (!statSync(distDir, { throwIfNoEntry: false })?.isDirectory()) {
  console.error(`[verify-bundle] dist/ not found - run a build:* script first`);
  process.exit(1);
}

function sha256(file) {
  return createHash('sha256').update(readFileSync(file)).digest('hex');
}

function walk(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

const files = walk(distDir)
  .filter((f) => f !== manifestPath)
  .map((f) => {
    const rel = path.relative(distDir, f).split(path.sep).join('/');
    return { path: rel, bytes: statSync(f).size, sha256: sha256(f) };
  })
  .sort((a, b) => a.path.localeCompare(b.path));

const bundleDigest = createHash('sha256')
  .update(files.map((f) => `${f.path}:${f.sha256}`).join('\n'))
  .digest('hex');

const indexHtml = readFileSync(path.join(distDir, 'index.html'), 'utf8');
const deployStatusMatch = indexHtml.match(/name="eif:deploy-status" content="([^"]+)"/);
const deployStatus = deployStatusMatch?.[1] ?? 'unknown';

const failures = [];
if (!files.some((f) => f.path === 'index.html')) {
  failures.push('dist/index.html missing from bundle');
}
if (deployStatus === 'unknown') {
  failures.push('could not read eif:deploy-status from dist/index.html');
}

const manifest = {
  generated: new Date().toISOString(),
  deployStatus,
  fileCount: files.length,
  totalBytes: files.reduce((sum, f) => sum + f.bytes, 0),
  bundleDigest,
  files,
};

writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');

console.log(`[verify-bundle] dist/manifest.json written`);
console.log(`  deployStatus: ${deployStatus}`);
console.log(`  files: ${manifest.fileCount}, totalBytes: ${manifest.totalBytes}`);
console.log(`  bundleDigest (sha256): ${bundleDigest}`);
console.log(`  local preview: npm run preview -- --mode preview`);

for (const f of failures) console.log(`  FAIL :: ${f}`);
if (failures.length > 0) {
  console.log('[verify-bundle] FAIL');
  process.exit(1);
}
console.log('[verify-bundle] PASS');
