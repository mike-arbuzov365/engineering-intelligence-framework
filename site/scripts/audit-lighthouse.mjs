#!/usr/bin/env node
// Lighthouse audit against D-08 targets (performance >= 90; accessibility/
// best-practices/SEO >= 95).
//
// Deliberately does NOT use lighthouse's usual chrome-launcher dependency:
// on this host, chrome-launcher's own Chrome spawn intermittently and then
// consistently failed with EPERM creating/using its userDataDir (observed
// signature, reproduced 5x including with a pre-created dir and with the
// harness sandbox disabled - not fixed by either). Playwright's own
// chromium.launch() works reliably in the same state, so this connects
// Lighthouse to a Playwright-launched browser's CDP port instead - same
// audit, different (working) browser-launch path.
// Usage: node scripts/audit-lighthouse.mjs <url>
// Exit codes: 0 = PASS, 1 = a real score is below budget, 2 = the audit
// itself could not run - "verification-degraded", distinct from a real
// failing score.

import lighthouse from 'lighthouse';
import { chromium } from '@playwright/test';

const url = process.argv[2];
if (!url) {
  console.error('[audit-lighthouse] usage: node scripts/audit-lighthouse.mjs <url>');
  process.exit(2);
}

const BUDGETS = { performance: 90, accessibility: 95, 'best-practices': 95, seo: 95 };
const CDP_PORT = 9331;

let browser;
try {
  browser = await chromium.launch({
    args: [`--remote-debugging-port=${CDP_PORT}`, '--headless=new'],
  });
} catch (err) {
  console.error(`[audit-lighthouse] verification-degraded: could not launch Chromium: ${err.message}`);
  process.exit(2);
}

try {
  const result = await lighthouse(url, {
    port: CDP_PORT,
    output: 'json',
    onlyCategories: Object.keys(BUDGETS),
    logLevel: 'error',
  });

  if (!result) {
    console.error('[audit-lighthouse] verification-degraded: lighthouse returned no result');
    process.exit(2);
  }

  let failed = false;
  for (const [key, budget] of Object.entries(BUDGETS)) {
    const score = Math.round((result.lhr.categories[key]?.score ?? 0) * 100);
    const ok = score >= budget;
    if (!ok) failed = true;
    console.log(`  ${ok ? 'PASS' : 'FAIL'} :: ${key}: ${score} (budget >= ${budget})`);
  }

  console.log(failed ? '[audit-lighthouse] FAIL' : '[audit-lighthouse] PASS');
  process.exit(failed ? 1 : 0);
} catch (err) {
  console.error(`[audit-lighthouse] verification-degraded: ${err.message}`);
  process.exit(2);
} finally {
  await browser.close();
}
