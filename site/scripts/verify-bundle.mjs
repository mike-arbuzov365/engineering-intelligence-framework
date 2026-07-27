#!/usr/bin/env node
// Session 006: exact local bundle evidence. Reads an already-built dist/
// (run a build:* script first), writes dist/manifest.json (file inventory,
// per-file SHA-256, one deterministic bundle digest) and validates metadata
// against the bundle's explicit deploy status.
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

function attributesOf(tag) {
  return Object.fromEntries(
    [...tag.matchAll(/([\w:-]+)="([^"]*)"/g)].map((match) => [match[1], match[2]]),
  );
}

function findTag(name, predicate) {
  for (const match of indexHtml.matchAll(new RegExp(`<${name}\\b[^>]*>`, 'gi'))) {
    const attributes = attributesOf(match[0]);
    if (predicate(attributes)) return attributes;
  }
  return null;
}

const canonical = findTag('link', (attrs) => attrs.rel === 'canonical')?.href;
const ogUrl = findTag('meta', (attrs) => attrs.property === 'og:url')?.content;
const ogImage = findTag('meta', (attrs) => attrs.property === 'og:image')?.content;
const twitterImage = findTag('meta', (attrs) => attrs.name === 'twitter:image')?.content;
const repositoryHref = findTag(
  'a',
  (attrs) => attrs.class?.split(/\s+/).includes('final-cta__repo'),
)?.href;
// The hero's primary action points at the same repository. It is the loudest
// control on the page, so a marker that failed to substitute there is worse
// than one in the closing screen, not better.
const heroRepositoryHref = findTag(
  'a',
  (attrs) => attrs.class?.split(/\s+/).includes('hero__ctas-repo'),
)?.href;

function assertHttps(label, value, { allowInvalid = false } = {}) {
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    failures.push(`${label} is not a valid absolute URL: ${value ?? '(missing)'}`);
    return null;
  }
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password) {
    failures.push(`${label} must be a credential-free https:// URL`);
  }
  if (!allowInvalid && (/\.invalid(\/|$)/i.test(value) || /example\.(com|org|net)/i.test(value))) {
    failures.push(`${label} contains a reserved or placeholder host`);
  }
  return parsed;
}

if (!files.some((f) => f.path === 'index.html')) {
  failures.push('dist/index.html missing from bundle');
}
if (deployStatus === 'unknown') {
  failures.push('could not read eif:deploy-status from dist/index.html');
}

// No build-time marker may survive into a shipped page in any mode. The
// clone URL is the one a reader would actually paste into a shell, so an
// unsubstituted marker there is a broken first command, not a cosmetic slip.
for (const marker of indexHtml.match(/__EIF_[A-Z_]+__/g) ?? []) {
  failures.push(`unsubstituted build marker left in dist/index.html: ${marker}`);
}
if (deployStatus === 'deployable' && !indexHtml.includes('git clone https://')) {
  failures.push('production quickstart must carry an https clone URL');
}

// The repository URL is a project constant now, not a per-deployment input,
// so every mode carries a real one. Only the reserved test profile differs,
// and it is asserted exactly below.
if (deployStatus !== 'no-deploy-test-profile') {
  assertHttps('repository CTA', repositoryHref);
  assertHttps('hero repository CTA', heroRepositoryHref);
}

// Both links go to the same place in every mode, including the reserved test
// profile. Two destinations for one repository is a defect either way round.
if (heroRepositoryHref !== repositoryHref) {
  failures.push(
    `hero repository CTA (${heroRepositoryHref ?? '(missing)'}) does not match the closing-screen one (${repositoryHref ?? '(missing)'})`,
  );
}

if (deployStatus === 'no-deploy') {
  if (canonical || ogUrl) failures.push('preview bundle must not publish canonical/og:url metadata');
  if (ogImage !== '/social-card.png' || twitterImage !== '/social-card.png') {
    failures.push('preview social image metadata must remain root-relative');
  }
} else if (deployStatus === 'no-deploy-test-profile') {
  const expectedSite = 'https://eif-site.invalid/';
  const expectedImage = `${expectedSite}social-card.png`;
  if (canonical !== expectedSite || ogUrl !== expectedSite) {
    failures.push('test-production canonical and og:url must use the reserved test site URL');
  }
  if (ogImage !== expectedImage || twitterImage !== expectedImage) {
    failures.push('test-production social images must be absolute reserved test URLs');
  }
  if (repositoryHref !== 'https://github.invalid/eif-website-test-profile') {
    failures.push('test-production repository CTA did not receive the reserved test URL');
  }
  assertHttps('test-production canonical', canonical, { allowInvalid: true });
} else if (deployStatus === 'deployable') {
  const site = assertHttps('production canonical', canonical);
  if (ogUrl !== canonical) failures.push('production og:url must equal canonical');
  const og = assertHttps('production og:image', ogImage);
  const twitter = assertHttps('production twitter:image', twitterImage);
  assertHttps('production repository CTA', repositoryHref);
  const expectedSocialImage = site ? new URL('social-card.png', site).href : null;
  if (og && expectedSocialImage && og.href !== expectedSocialImage) {
    failures.push('production og:image must resolve to social-card.png under the canonical site URL');
  }
  if (twitter && twitter.href !== og?.href) {
    failures.push('production twitter:image must equal og:image');
  }
} else if (deployStatus !== 'unknown') {
  failures.push(`unsupported eif:deploy-status "${deployStatus}"`);
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
