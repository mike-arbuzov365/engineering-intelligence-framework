#!/usr/bin/env node
// Own the test server outside Playwright's webServer plugin. Playwright
// 1.61 cannot use gracefulShutdown on Windows, and its shell-owned server
// process can add roughly a minute of teardown per suite on this host.

import { spawn, spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildAndServeTestBundle } from './serve-test-bundle.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, '..');
const suite = process.argv[2];
const port = Number.parseInt(process.argv[3] ?? '', 10);
const forwardedArgs = process.argv.slice(4);

if (!['e2e', 'a11y'].includes(suite) || !Number.isInteger(port)) {
  console.error('[run-playwright] usage: node scripts/run-playwright.mjs <e2e|a11y> <port>');
  process.exit(1);
}

const { server, url } = await buildAndServeTestBundle(port);
const cliPath = path.join(siteRoot, 'node_modules', '@playwright', 'test', 'cli.js');
const testArgs =
  suite === 'a11y'
    ? [cliPath, 'test', '--config=playwright.a11y.config.js', ...forwardedArgs]
    : [cliPath, 'test', ...forwardedArgs];

const child = spawn(process.execPath, testArgs, {
  cwd: siteRoot,
  env: { ...process.env, EIF_TEST_BASE_URL: url },
  stdio: 'inherit',
});

function terminateChild() {
  if (!child.pid) return;
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/pid', String(child.pid), '/t', '/f'], { stdio: 'ignore' });
  } else {
    child.kill('SIGTERM');
  }
}

let interrupted = false;
function interrupt(signal) {
  if (interrupted) return;
  interrupted = true;
  terminateChild();
  server.close(() => process.exit(signal === 'SIGINT' ? 130 : 143));
}
process.once('SIGINT', () => interrupt('SIGINT'));
process.once('SIGTERM', () => interrupt('SIGTERM'));

const exitCode = await new Promise((resolve) => {
  child.once('error', (error) => {
    console.error(`[run-playwright] could not start Playwright: ${error.message}`);
    resolve(1);
  });
  child.once('exit', (code) => resolve(code ?? 1));
});

await new Promise((resolve) => server.close(resolve));
process.exitCode = exitCode;
