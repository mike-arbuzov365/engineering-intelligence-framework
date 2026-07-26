#!/usr/bin/env node
// Claims / privacy / placeholder verifier for the EIF website (D-04, D-08).
// Usage: node scripts/verify-claims.mjs [target...] [--strict]
// With no target, scans index.html + src/ (real site content). A target may
// be a single file or a directory (used by tests/unit against one fixture
// dir at a time).
//
// Always fails on: unknown claim IDs, forbidden wording, private/absolute
// paths, placeholder markers, hardcoded non-HTTPS or third-party runtime
// requests (script/link/img/iframe src|href, fetch(), XMLHttpRequest).
// --strict additionally fails when a manifest claim ID is never referenced
// (used for the Session 004+ full-coverage gate; earlier sessions still ship
// partial content, so unused-claim is a warning there, not a hard failure).

import { readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const siteRoot = path.resolve(__dirname, '..');

const args = process.argv.slice(2);
const strict = args.includes('--strict');
const targetArgs = args.filter((a) => !a.startsWith('--'));
const targets = (targetArgs.length > 0 ? targetArgs : ['index.html', 'src']).map((t) =>
  path.resolve(siteRoot, t),
);

const SCANNED_EXTENSIONS = new Set(['.html', '.js', '.mjs', '.css', '.json']);
const MANIFEST_RELATIVE_PATH = path.join('src', 'content', 'claims.json');

const POSIX_USER_ROOT = '/' + 'Users/';
// A drive letter is one character and nothing alphanumeric precedes it.
// Without that lookbehind the POSIX-separator variant reads the "s" in
// "https://" as a drive and reports every absolute URL on the page as a
// leaked machine path - which is exactly what it did to the first outbound
// link the site ever carried.
const PRIVATE_PATH_PATTERNS = [
  /(?<![A-Za-z0-9])[A-Za-z]:\\[^\s"'<>]+/, // Windows absolute path shape.
  /(?<![A-Za-z0-9])[A-Za-z]:\/[^\s"'<>]+/, // Windows drive path written with POSIX separators.
  /\\\\[^\\\s"'<>]+\\[^\s"'<>]+/, // UNC share path.
  new RegExp(`${POSIX_USER_ROOT}[^\\s"'<>]+`),
  /\/home\/[^\s"'<>]+/,
];

const PLACEHOLDER_PATTERNS = [
  /\bTODO\b/,
  /\bFIXME\b/,
  /lorem ipsum/i,
  /\bchangeme\b/i,
  /example\.(com|org|net)/i,
];

// Global forbidden phrases that are never allowed regardless of which claim
// is nearby (aggregated from docs/product/claims-evidence.md; see claims.json
// per-claim forbiddenWording for the sourced, claim-scoped subset).
const GLOBAL_FORBIDDEN_PHRASES = [
  'production-ready',
  'proven at scale',
  'published package',
  'official release',
  'automatically merges with any existing setup',
  'zero-config adoption',
  'benchmark proves eif is more efficient',
  'improves quality',
  'reduces rework',
  'fewer bugs',
  'autonomous until complete',
  'self-correcting without limits',
  'faster codebase understanding',
  'semantic analysis is verified',
  'rtk improves quality',
  'rtk is healthy on every platform',
  'fully runtime validated',
  'fully verified adapter',
  'required v0.1 adapter',
  'every property independently proven for every pair',
  'full localization',
  'works in any language',
  'saves developer hours',
  'faster than a human',
  'requires graphify',
  'requires rtk',
];

const RUNTIME_RESOURCE_TAG_RE =
  /<(script|img|iframe|link|source|video|audio|object|embed)\b[^>]*>/gi;
const RUNTIME_RESOURCE_ATTR_RE =
  /\b(src|href|poster|data)=["'](https?:)?\/\/[^"']+["']/i;
const JS_RUNTIME_REQUEST_RES = [
  /\bfetch\s*\(\s*["'`](https?:)?\/\/[^"'`]+/g,
  /\b(WebSocket|EventSource)\s*\(\s*["'`](https?:)?\/\/[^"'`]+/g,
  /\b(sendBeacon)\s*\(\s*["'`](https?:)?\/\/[^"'`]+/g,
  /\.open\s*\(\s*["'`](GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)["'`]\s*,\s*["'`](https?:)?\/\/[^"'`]+/gi,
];
const CSS_REMOTE_URL_RE = /url\(\s*["']?(https?:)?\/\/[^)'"]+/gi;

const VANITY_COUNT_RE =
  /\b\d[\d,]*\+?\s*(users?|customers?|installs?|downloads?|stars?|companies|teams)\b/gi;

const SKIPPED_DIR_NAMES = new Set(['node_modules', 'dist', 'tests', '.vite-temp']);

function walk(dir) {
  const entries = readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (SKIPPED_DIR_NAMES.has(entry.name)) continue;
      files.push(...walk(full));
    } else if (SCANNED_EXTENSIONS.has(path.extname(entry.name))) {
      files.push(full);
    }
  }
  return files;
}

// A target may be a single file (used by tests/unit fixtures and by the
// index.html root shell) or a directory (walked recursively).
function collectFiles(target) {
  const stat = statSync(target);
  if (stat.isDirectory()) {
    return walk(target);
  }
  return SCANNED_EXTENSIONS.has(path.extname(target)) ? [target] : [];
}

function loadManifest() {
  const manifestPath = path.join(siteRoot, 'src', 'content', 'claims.json');
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  const ids = new Set(manifest.claims.map((c) => c.id));
  if (ids.size !== manifest.claims.length) {
    throw new Error('[verify-claims] duplicate claim IDs in manifest');
  }
  return { manifest, ids };
}

function findLineNumber(content, index) {
  return content.slice(0, index).split('\n').length;
}

function scanFile(file, content, ids, violations, usedIds) {
  const rel = path.relative(siteRoot, file);

  for (const m of content.matchAll(/data-claim-id=["']([^"']+)["']/g)) {
    const id = m[1];
    if (ids.has(id)) {
      usedIds.add(id);
    } else {
      violations.push({
        rule: 'unknown-claim-id',
        file: rel,
        line: findLineNumber(content, m.index),
        detail: `data-claim-id="${id}" is not in claims.json`,
      });
    }
  }

  const lower = content.toLowerCase();
  for (const phrase of GLOBAL_FORBIDDEN_PHRASES) {
    const idx = lower.indexOf(phrase);
    if (idx !== -1) {
      violations.push({
        rule: 'forbidden-wording',
        file: rel,
        line: findLineNumber(content, idx),
        detail: `forbidden phrase "${phrase}"`,
      });
    }
  }

  for (const re of PRIVATE_PATH_PATTERNS) {
    const m = re.exec(content);
    if (m) {
      violations.push({
        rule: 'private-path',
        file: rel,
        line: findLineNumber(content, m.index),
        detail: `matched ${re}`,
      });
    }
  }

  // Fixtures intentionally exercise placeholder/runtime-request violations;
  // they are asserted against directly by tests/unit and must not also be
  // flagged when this verifier is pointed at the real site content dir.
  for (const re of PLACEHOLDER_PATTERNS) {
    const m = re.exec(content);
    if (m) {
      violations.push({
        rule: 'placeholder-marker',
        file: rel,
        line: findLineNumber(content, m.index),
        detail: `matched ${re}`,
      });
    }
  }

  RUNTIME_RESOURCE_TAG_RE.lastIndex = 0;
  for (const match of content.matchAll(RUNTIME_RESOURCE_TAG_RE)) {
    if (!RUNTIME_RESOURCE_ATTR_RE.test(match[0])) continue;
    violations.push({
      rule: 'runtime-external-request',
      file: rel,
      line: findLineNumber(content, match.index),
      detail: match[0].slice(0, 80),
    });
  }

  for (const re of [...JS_RUNTIME_REQUEST_RES, CSS_REMOTE_URL_RE]) {
    re.lastIndex = 0;
    let m;
    while ((m = re.exec(content))) {
      violations.push({
        rule: 'runtime-external-request',
        file: rel,
        line: findLineNumber(content, m.index),
        detail: m[0].slice(0, 80),
      });
    }
  }

  VANITY_COUNT_RE.lastIndex = 0;
  let vanityMatch;
  while ((vanityMatch = VANITY_COUNT_RE.exec(content))) {
    const nearby = content.slice(Math.max(0, vanityMatch.index - 120), vanityMatch.index);
    if (!nearby.includes('data-claim-id=')) {
      violations.push({
        rule: 'uncited-count',
        file: rel,
        line: findLineNumber(content, vanityMatch.index),
        detail: `"${vanityMatch[0]}" has no nearby data-claim-id`,
      });
    }
  }
}

function main() {
  const { manifest, ids } = loadManifest();

  for (const claim of manifest.claims) {
    for (const field of ['id', 'summary', 'status', 'allowedWording', 'limitations', 'source']) {
      if (!claim[field]) {
        throw new Error(`[verify-claims] claim ${claim.id ?? '?'} missing required field "${field}"`);
      }
    }
  }

  const fileSet = new Set();
  for (const target of targets) {
    try {
      for (const f of collectFiles(target)) fileSet.add(f);
    } catch (err) {
      if (err.code === 'ENOENT') {
        console.error(`[verify-claims] target not found: ${target}`);
        process.exit(1);
      }
      throw err;
    }
  }

  // The manifest itself legitimately catalogs forbidden phrases as reference
  // data (claims.json's own forbiddenWording arrays); it is validated by
  // loadManifest() above, not by the copy-scanning rules below.
  const files = [...fileSet].filter(
    (f) => path.relative(siteRoot, f) !== MANIFEST_RELATIVE_PATH,
  );

  const violations = [];
  const usedIds = new Set();

  for (const file of files) {
    const content = readFileSync(file, 'utf8');
    scanFile(file, content, ids, violations, usedIds);
  }

  const targetLabel = targets.map((t) => path.relative(siteRoot, t) || '.').join(', ');

  const unused = [...ids].filter((id) => !usedIds.has(id));
  if (unused.length > 0) {
    for (const id of unused) {
      violations.push({
        rule: strict ? 'unused-claim-id' : 'unused-claim-id-warning',
        file: '(manifest)',
        line: 0,
        detail: `${id} is never referenced under ${targetLabel}`,
      });
    }
  }

  const hardFailures = violations.filter(
    (v) => strict || v.rule !== 'unused-claim-id-warning',
  );

  console.log(`[verify-claims] target=${targetLabel} strict=${strict}`);
  console.log(`[verify-claims] manifest claims: ${manifest.claims.length}, referenced: ${usedIds.size}`);
  for (const v of violations) {
    console.log(`  ${v.rule} :: ${v.file}:${v.line} :: ${v.detail}`);
  }

  if (hardFailures.length > 0) {
    console.log(`[verify-claims] FAIL (${hardFailures.length} finding(s))`);
    process.exit(1);
  }

  console.log('[verify-claims] PASS');
}

main();
