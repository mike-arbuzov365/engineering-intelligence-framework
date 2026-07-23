import { test } from 'node:test';
import assert from 'node:assert/strict';

import { normalizePublicUrl, resolveProductionUrls } from '../../vite.config.js';

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
