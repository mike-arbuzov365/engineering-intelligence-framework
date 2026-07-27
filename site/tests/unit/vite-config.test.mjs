import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  normalizePublicUrl,
  resolveProductionUrls,
  resolveRepositoryUrl,
} from '../../vite.config.js';

test('production URL normalization preserves a deploy sub-path', () => {
  const result = resolveProductionUrls('production', {
    EIF_SITE_URL: 'https://docs.invalid-host.test/eif',
    EIF_REPOSITORY_URL: 'https://code.invalid-host.test/org/eif',
  });

  assert.equal(result.siteUrl, 'https://docs.invalid-host.test/eif/');
  assert.equal(result.repositoryUrl, 'https://code.invalid-host.test/org/eif');
});

test('public URLs reject credentials, queries, fragments and malformed input', () => {
  for (const value of [
    'https://user:secret@docs.invalid-host.test/eif',
    'https://docs.invalid-host.test/eif?preview=1',
    'https://docs.invalid-host.test/eif#preview',
    'https://[',
  ]) {
    assert.throws(
      () => normalizePublicUrl('EIF_SITE_URL', value, 'production', { directory: true }),
      /eif-site/,
    );
  }
});

test('reserved .invalid URLs are accepted only by the test-production profile', () => {
  assert.throws(
    () =>
      resolveProductionUrls('production', {
        EIF_SITE_URL: 'https://eif-site.invalid/',
        EIF_REPOSITORY_URL: 'https://github.invalid/eif',
      }),
    /reserved \.invalid/,
  );

  const result = resolveProductionUrls('test-production', {});
  assert.equal(result.siteUrl, 'https://eif-site.invalid/');
  assert.equal(result.repositoryUrl, 'https://github.invalid/eif-website-test-profile');
});

test('the repository URL resolves in every mode, not only production', () => {
  // It was production-only, which left dev and preview builds pointing the
  // closing screen's Source row at an on-page anchor.
  for (const mode of ['development', 'preview', 'production']) {
    assert.equal(
      resolveRepositoryUrl(mode, {}),
      'https://github.com/mike-arbuzov365/engineering-intelligence-framework',
    );
  }

  // The reserved test profile keeps its own value rather than inheriting the
  // real one, or build:test-production would stop being a canary.
  assert.equal(
    resolveRepositoryUrl('test-production', {}),
    'https://github.invalid/eif-website-test-profile',
  );
});

test('an overridden repository URL is validated like any other public URL', () => {
  assert.equal(
    resolveRepositoryUrl('preview', { EIF_REPOSITORY_URL: 'https://code.invalid-host.test/org/eif' }),
    'https://code.invalid-host.test/org/eif',
  );

  // A mistyped override must fail the build rather than ship as the first
  // command a reader pastes into a shell.
  for (const value of ['http://code.invalid-host.test/org/eif', 'not-a-url', 'https://user:secret@code.invalid-host.test/eif']) {
    assert.throws(() => resolveRepositoryUrl('preview', { EIF_REPOSITORY_URL: value }), /eif-site/);
  }
});
