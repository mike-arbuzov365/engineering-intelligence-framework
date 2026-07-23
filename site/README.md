# site/

Local, deploy-ready presentation site for the Engineering Intelligence
Framework. Vite + vanilla HTML/CSS/JS, no framework/CMS/backend dependency
and no third-party runtime requests.

The narrative follows the canonical framework architecture:

1. why chat history is not engineering memory;
2. what Engineering Intelligence and the methodology mean;
3. the three intelligence tiers;
4. the control plane and session lifecycle;
5. bounded execution and governed learning;
6. optional integrations, current evidence, quickstart and limitations.

## Commands

```
npm ci                       # clean install from the committed lockfile
npm run dev                  # local dev server
npm run build:preview        # build with no production URL requirement
npm run build:production     # requires EIF_SITE_URL + EIF_REPOSITORY_URL
                              # (https, non-placeholder); fails closed otherwise
npm run build:test-production  # same gate, but accepts the reserved
                                # .invalid canary domain; output is marked
                                # eif:deploy-status=no-deploy-test-profile
                                # and must never be treated as a deployable
                                # artifact
npm run preview              # serve a built dist/
npm run verify:claims        # claim ID / forbidden-wording / private-path /
                              # placeholder / runtime-external-request scan
npm run verify:claims:strict # + fails on any unreferenced claim ID
npm run verify:metadata      # required meta tags, favicon/social assets,
                              # 1200x630 social-card.png dimensions
npm run test:unit            # node:test - the claims verifier's own tests
npm run test:e2e             # Playwright (desktop-1440 + mobile-390 projects)
npm run test:e2e -- --grep <name>   # filter by describe/test title
npm run generate:social-assets      # regenerate public/social-card.png,
                                     # favicon.png, apple-touch-icon.png from
                                     # public/favicon.svg via a headless
                                     # Chromium screenshot (maintainer-run,
                                     # output is committed like any other
                                     # static asset - not part of the build)
```

## Claims

Every material on-page claim carries a `data-claim-id="CLM-NN"` attribute
matching an entry in `src/content/claims.json`. That manifest is the source
of truth for allowed/forbidden wording and links each claim back to its
evidence in the framework repo's `docs/product/claims-evidence.md`. Do not
add a claim-shaped sentence without a `data-claim-id`, and do not strengthen
wording beyond what the manifest's `allowedWording` states.

## Metadata / URLs

`EIF_SITE_URL` and `EIF_REPOSITORY_URL` are the only two owner-supplied
production inputs this site needs. Preview and dev builds never require
them: the final-CTA repository link and canonical/sitemap/robots output all
degrade to an on-page or `Disallow: /` default when unset (see the
`eif-metadata` Vite plugin in `vite.config.js`).

## Structure

- `index.html` - the whole single-page site (Vite convention: page shell at
  the project root, not under `src/`).
- `src/styles/` - one file per concern (tokens, base, hero, sections, loop,
  integrations, content, reveal, motion), imported in cascade order from
  `src/main.js`.
- `src/content/claims.json` - the public claim manifest.
- `public/` - favicon, social-card and apple-touch-icon assets, copied
  verbatim into `dist/` by Vite.
- `scripts/` - `verify-claims.mjs`, `verify-metadata.mjs`,
  `generate-social-assets.mjs`.
- `tests/unit/` - node:test, no browser.
- `tests/e2e/` - `@playwright/test` specs.
- `tests/fixtures/claims/` - positive/negative fixtures the claims-verifier
  unit tests assert against.
