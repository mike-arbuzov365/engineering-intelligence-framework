# site/

Local, deploy-ready presentation site for the Engineering Intelligence
Framework. Vite + vanilla HTML/CSS/JS, no framework/CMS/backend dependency
and no third-party runtime requests.

The narrative follows the canonical framework architecture:

1. why chat history is not engineering memory;
2. what Engineering Intelligence and the methodology mean;
3. the three intelligence layers;
4. the control plane and session lifecycle;
5. bounded execution and governed learning;
6. optional integrations, current evidence, quickstart, and where to read on
   or reach the author.

Boundaries are not a section of their own. Every limit is stated where the
claim it limits is made: each evidence row carries its own `Limitation:`
line, the bounded-proof list carries the no-quality/no-rework claim, and the
quickstart carries the no-package-index and no-human-duration caveats.

The quickstart is two numbered steps, and only the first differs per
platform: macOS/Linux/WSL, Windows PowerShell and Windows CMD each get their
own command block behind a tab strip. All three panels ship in the static
markup and stay open without JavaScript, each under its own heading, so the
no-script path is the complete one rather than a strip that cannot switch.
Every command there is run before it is published - none of them is the
package-index form, which is the one command on that screen that would fail
for a reader.

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
npm run verify:bundle        # manifest, digest, deploy-status and emitted
                              # metadata/CTA contract for the current dist/
npm run test:unit            # node:test - claims and URL-boundary tests
npm run test:e2e             # full Chromium assertions + bounded real-mobile
                              # and independent Firefox behavioral smoke;
                              # one-process dist server avoids slow Windows
                              # cleanup of nested npm/Vite process trees
npm run test:e2e -- --grep <name>   # filter by describe/test title
npm run gate:site            # one bounded local final gate; no hosted CI
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

## Language and terminology

English is the static default. The Ukrainian templates are an adaptive
localization, not a line-by-line translation: explanatory prose and UI labels
use natural Ukrainian engineering language, while canonical artifact types
such as `Knowledge Delta`, command names and status values keep their precise
technical spelling. Terms such as `playbook`, `skill` and `layer` are expressed
as natural Ukrainian descriptions in reader-facing prose. The Ukrainian E2E
assertion guards against reintroducing avoidable mixed-language phrases in
rendered page copy.

## Metadata / URLs

`EIF_SITE_URL` is the one owner-supplied production input, and it lives in
the committed `.env.production`, which Vite loads for `build:production`
only. It is public by definition - it is emitted into the shipped HTML as
the canonical URL, the sitemap and the absolute social-card URLs - so the
file is committed and a production build is reproducible from a clean
checkout instead of from one machine's shell. Moving the site to another
host is a one-line change to it. Preview and dev builds never require it:
canonical, sitemap and `og:url` are simply not emitted, and `robots.txt`
degrades to `Disallow: /`.

The repository URL is *not* an input. It is a constant of the project, so
it lives in `vite.config.js` and resolves in every mode including dev, which
is what makes the closing screen's Source row and the quickstart's
`git clone` line real links in a local read. `EIF_REPOSITORY_URL` overrides
it for one build and is validated the same way, so a mistyped override fails
the build rather than shipping as the first command a reader pastes. It used
to be production-gated, which was right while publication was undecided and
wrong the moment the repository went public: every non-production build
pointed the one outbound CTA at an on-page anchor.

Production inputs must be credential-free HTTPS URLs with no query or
fragment. `EIF_SITE_URL` may include a deployment sub-path; Vite's base,
canonical URL, sitemap, robots and absolute Open Graph/Twitter image URLs
are derived from the same normalized value. Because Vite rebases
root-relative asset paths against that base before the metadata plugin
runs, the social-image substitution matches on filename rather than on the
source string - a literal match silently did nothing on a sub-path host and
shipped a relative `og:image` no crawler could resolve.

Run `build:production` and then `verify:bundle` before deployment.
`verify:bundle` fails on any `__EIF_*__` marker that survived into
`dist/index.html`, so an unsubstituted clone URL cannot ship as a first
command a reader would paste.

## Deployment

`.github/workflows/pages.yml` publishes this directory to GitHub Pages on
any change under `site/`, and on manual dispatch. It runs
`verify:claims:strict`, `verify:metadata`, `build:production` and
`verify:bundle`, in that order, and nothing else - no Playwright, no
Lighthouse, no axe. Those three verifiers are pure Node scripts with no
browser, and they are what stops an unknown claim ID, forbidden wording, a
leaked private path, a third-party runtime request or a surviving build
marker from reaching a public page. The full gate stays local and unhosted:
`npm run gate:site`. See D-15 in `core/policies/decisions.md` for why a
push-triggered deploy is a boundary rather than a contradiction of D-14.

`generate:social-assets` also emits `.github/social-preview.png` at
1280x640, from the same brand source as the site's own card, for the
repository's Social preview setting. It is written outside `public/` because
the site never serves it and copying it into every `dist/` would be dead
weight.

## Structure

- `index.html` - the whole single-page site (Vite convention: page shell at
  the project root, not under `src/`).
- `src/styles/` - one file per concern (tokens, base, hero, sections, loop,
  integrations, content, reveal, motion, figure-tip, code-block, install,
  lang-toggle), imported in cascade order from `src/main.js`.
- `src/content/claims.json` - the public claim manifest.
- `public/` - favicon, social-card and apple-touch-icon assets, copied
  verbatim into `dist/` by Vite.
- `scripts/` - `verify-claims.mjs`, `verify-metadata.mjs`,
  `generate-social-assets.mjs`.
- `tests/unit/` - node:test, no browser.
- `tests/e2e/` - `@playwright/test` specs.
- `tests/fixtures/claims/` - positive/negative fixtures the claims-verifier
  unit tests assert against.
