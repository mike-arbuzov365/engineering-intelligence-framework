import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  assertNoNestedComment,
  expandPartials,
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

test('an include marker is replaced in place, at the marker\'s own indentation', () => {
  const html = [
    '<div>',
    '  <!-- eif:include partials/thing.html -->',
    '</div>',
  ].join('\n');

  const out = expandPartials(html, () => '<svg>\n  <circle />\n</svg>\n');

  assert.equal(
    out,
    ['<div>', '  <svg>', '    <circle />', '  </svg>', '</div>'].join('\n'),
  );
});

test('every marker for the same partial expands, so two places cannot drift apart', () => {
  // The reason this plugin exists: the orbit mark is drawn in the hero and
  // again in section 03, in two languages.
  const html = [
    '<!-- eif:include partials/orbit.html -->',
    '<!-- eif:include partials/orbit.html -->',
  ].join('\n');

  let reads = 0;
  const out = expandPartials(html, () => {
    reads += 1;
    return '<svg />';
  });

  assert.equal(reads, 2);
  assert.equal(out, '<svg />\n<svg />');
});

test('a marker that is not alone on its line is left alone', () => {
  // Otherwise a partial documenting its own marker inside a comment would
  // recurse, and prose quoting one would be replaced by a drawing.
  const html = '<p>write <!-- eif:include partials/x.html --> to include it</p>';
  assert.equal(
    expandPartials(html, () => {
      throw new Error('should not read');
    }),
    html,
  );
});

test('an include path may not escape src/', () => {
  assert.throws(
    () => expandPartials('<!-- eif:include ../../secrets.html -->', () => ''),
    /must stay under src/,
  );
});

test('a partial that opens a comment inside a comment is refused', () => {
  // HTML comments do not nest: the first `-->` closes the outermost `<!--`
  // and the rest spills into the document as text, taking the <head> with
  // it. The only symptom is a parse warning, so it is caught here instead.
  const nested = ['<!-- header', '     see <!-- eif:include x.html --> above', '-->', '<svg />'].join(
    '\n',
  );
  assert.throws(() => assertNoNestedComment('partials/x.html', nested), /do not nest/);
  assert.throws(() => expandPartials('<!-- eif:include partials/x.html -->', () => nested), /do not nest/);

  // Sequential comments are fine; only nesting is the defect.
  assert.doesNotThrow(() =>
    assertNoNestedComment('partials/x.html', '<!-- one -->\n<svg />\n<!-- two -->'),
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
