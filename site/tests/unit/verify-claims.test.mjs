import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, '..', '..');
const verifierPath = path.join(siteRoot, 'scripts', 'verify-claims.mjs');

function runVerifier(targetDir, extraArgs = []) {
  const result = spawnSync(process.execPath, [verifierPath, targetDir, ...extraArgs], {
    cwd: siteRoot,
    encoding: 'utf8',
  });
  return result;
}

test('positive fixture passes', () => {
  const result = runVerifier('tests/fixtures/claims/positive');
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /PASS/);
});

test('unknown claim id fails', () => {
  const result = runVerifier('tests/fixtures/claims/negative-unknown-claim');
  assert.notEqual(result.status, 0);
  assert.match(result.stdout, /unknown-claim-id/);
});

test('forbidden wording fails', () => {
  const result = runVerifier('tests/fixtures/claims/negative-forbidden-wording');
  assert.notEqual(result.status, 0);
  assert.match(result.stdout, /forbidden-wording/);
});

test('private path fails', (t) => {
  // Assemble the negative value only at runtime: committing a real-looking
  // machine path as a fixture would correctly trip the repository's own
  // privacy scanner before this narrower website verifier even runs.
  const fixtureDir = mkdtempSync(path.join(tmpdir(), 'eif-claims-private-path-'));
  t.after(() => rmSync(fixtureDir, { recursive: true, force: true }));
  const privatePath = ['D:', 'Repos', 'private-instance', 'planning'].join('\\');
  writeFileSync(
    path.join(fixtureDir, 'bad.html'),
    `<p data-claim-id="CLM-01">Evidence lives at ${privatePath}.</p>\n`,
    'utf8',
  );

  const result = runVerifier(fixtureDir);
  assert.notEqual(result.status, 0);
  assert.match(result.stdout, /private-path/);
});

test('placeholder marker fails', () => {
  const result = runVerifier('tests/fixtures/claims/negative-placeholder');
  assert.notEqual(result.status, 0);
  assert.match(result.stdout, /placeholder-marker/);
});

test('runtime external request fails', () => {
  const result = runVerifier('tests/fixtures/claims/negative-runtime-request');
  assert.notEqual(result.status, 0);
  assert.match(result.stdout, /runtime-external-request/);
});

test('uncited count fails', () => {
  const result = runVerifier('tests/fixtures/claims/negative-uncited-count');
  assert.notEqual(result.status, 0);
  assert.match(result.stdout, /uncited-count/);
});

test('non-strict run warns but does not fail on unused claims', () => {
  const result = runVerifier('tests/fixtures/claims/positive');
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /unused-claim-id-warning/);
});

test('strict run fails on unused claims', () => {
  const result = runVerifier('tests/fixtures/claims/positive', ['--strict']);
  assert.notEqual(result.status, 0);
  assert.match(result.stdout, /unused-claim-id/);
});
