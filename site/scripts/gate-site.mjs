#!/usr/bin/env node
// The one final site gate (SESSION-005): runs every verification step once
// and reports a single pass/fail summary. Not meant to be run repeatedly
// unchanged - see 04-ROADMAP-001's verification cadence (private planning
// repo).
//
// The build step uses test-production (reserved .invalid URLs), not
// preview: D-08's Lighthouse/SEO targets are evaluated against "the final
// build" - a preview build's robots.txt intentionally disallows crawling
// (correct for a non-indexed preview), which fails Lighthouse's is-crawlable
// SEO check for a reason that has nothing to do with real site quality.
// test-production exercises the same URL-gated code paths as a real
// production build without inventing an owner value (D-09).

import { spawnSync, spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, '..');
const frameworkRoot = path.resolve(siteRoot, '..');

const results = [];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function run(label, command, args, opts = {}) {
  const result = spawnSync(command, args, { stdio: 'inherit', ...opts });
  const ok = result.status === 0;
  results.push({ label, ok, status: result.status });
  return ok;
}

function runNpm(label, script) {
  return run(label, 'npm', ['run', script], { cwd: siteRoot, shell: true });
}

runNpm('verify:claims:strict', 'verify:claims:strict');
runNpm('verify:metadata', 'verify:metadata');
runNpm('test:unit', 'test:unit');
runNpm('test:e2e', 'test:e2e');
await sleep(3000); // let browser processes from test:e2e fully exit
runNpm('test:a11y', 'test:a11y');
await sleep(3000); // same, before the lighthouse step's own Chromium launch
runNpm('build:test-production', 'build:test-production');
runNpm('audit:assets', 'audit:assets');

// The CLI `vite preview` (spawned here, same as a maintainer would run it)
// instead of Vite's programmatic preview() JS API: isolated testing showed
// the JS-API server reproducibly triggers a lighthouse "Target closed"
// navigation error that the CLI-invoked server never did, across several
// runs.
const PREVIEW_PORT = 5185;
const previewUrl = `http://localhost:${PREVIEW_PORT}`;
const previewProcess = spawn(
  'npm',
  ['run', 'preview', '--', '--mode', 'test-production', '--port', String(PREVIEW_PORT), '--strictPort'],
  { cwd: siteRoot, shell: true, stdio: 'inherit' },
);

async function waitForServer(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url);
      if (res.ok) return true;
    } catch {
      // not up yet
    }
    await sleep(300);
  }
  return false;
}

try {
  const ready = await waitForServer(previewUrl, 15_000);
  if (!ready) {
    console.error('[audit:lighthouse] verification-degraded: preview server did not become ready');
    results.push({ label: 'audit:lighthouse', ok: false, degraded: true });
  } else {
    const lhOk = run('audit:lighthouse', 'node', ['scripts/audit-lighthouse.mjs', previewUrl], {
      cwd: siteRoot,
    });
    if (!lhOk) results[results.length - 1].degraded = results[results.length - 1].status === 2;
  }
} finally {
  // `shell: true` on Windows spawns npm inside cmd.exe, which spawns vite in
  // turn - plain .kill() only signals the shell, leaving vite preview
  // running. taskkill /t kills the whole tree.
  if (process.platform === 'win32' && previewProcess.pid) {
    spawnSync('taskkill', ['/pid', String(previewProcess.pid), '/t', '/f']);
  } else {
    previewProcess.kill();
  }
}

run('eif_check_links.py', 'python', [path.join(frameworkRoot, 'scripts', 'eif_check_links.py')], {
  cwd: frameworkRoot,
});
run('git diff --check', 'git', ['diff', '--check'], { cwd: frameworkRoot });

console.log('\n[gate:site] summary');
let anyFailed = false;
let anyDegraded = false;
for (const r of results) {
  if (!r.ok) anyFailed = true;
  if (r.degraded) anyDegraded = true;
  console.log(`  ${r.ok ? 'PASS' : 'FAIL'} :: ${r.label}`);
}

if (anyDegraded) {
  console.log('[gate:site] DEGRADED - lighthouse could not run; deployment stays blocked');
}
console.log(anyFailed ? '[gate:site] FAIL' : '[gate:site] PASS');
process.exit(anyFailed ? 1 : 0);
