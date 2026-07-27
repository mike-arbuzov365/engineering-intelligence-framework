---
type: fact
status: validated
scope: framework
evidence: OBSERVED
source: code
created: 2026-07-27
review_after: 2026-08-27
---

<!-- Frontmatter corrected 2026-07-27: this carried `type: reference` and
`status: active`, neither of which exists in the ontology, so CI's own
frontmatter validation failed on it and on linkedin-series.md from the day
both were added. It states what is true of this repository right now (the
version in pyproject.toml, that no artifact is on a package index, what the
release script does and where it stops), which is empirical, so `fact` with
an OBSERVED label read from the code itself. -->


# Pre-release status

Everything the website used to say about its own release status, in one
place off the page.

The website is a description of the framework, not a status board for it.
Release notes, install boundaries and "not yet" statements were being
carried inline next to the copy they qualified, which is right while the
site is a working draft and wrong the day it is published: a reader who
came to find out what EIF is should not have to read around a maintainer's
build notes. Those notes are not dropped, they are here.

Two rules hold this file to the same discipline as the rest of the
repository. Nothing on the site may become false because a caveat moved
here. And every line below states what is actually true today, with the
bound, not what is intended.

## What was on the site and is not any more

### Quickstart, section 10

**Was:** a heading reading "A synthetic walkthrough, not a release", a lede
ending "not a stable release or a representative sample of real engineering
tasks", and a closing caveat titled "Installable, not yet published" that
named `scripts/eif_release.py`, the index validation it performs, and the
fact that the upload step needs owner credentials. It also carried an
explicit "no claim is made about how long any of this takes a human".

**Now:** two numbered steps - install from a clone, then initialize an
instance - and the walkthrough they run. Step one carries a command block
per platform (macOS/Linux/WSL, Windows PowerShell, Windows CMD) behind a
tab strip, because "where do I paste this, and what happens on my OS" was
the first question the screen actually got asked.

**Why nothing on the page became false.** Every command on that screen was
run before it was published: a clean 3.11 virtual environment, `pip
install .` from the clone, then `eifctl init` into a fresh directory, which
initialized an instance and reported in the locale its config declared. The
page never printed `pip install engineering-intelligence-framework`, which
is the one form that would fail for a reader today, and an end-to-end test
asserts it never appears. The removed duration sentence disclaimed a claim
the page does not make: no timing figure appears anywhere on it.

## Where the release actually stands

- **Version.** `0.1.0.dev0` in [`pyproject.toml`](../../pyproject.toml).
- **Installable from a clone.** `pip install .` builds and installs a real
  wheel. Verified by the installed-wheel synthetic journey, which runs
  `eifctl` from a built wheel in a clean virtual environment.
- **Not on a package index.** No artifact has been uploaded to PyPI or any
  other index. `pip install engineering-intelligence-framework` does not
  resolve.
- **Release tooling is complete up to the upload.**
  [`scripts/eif_release.py`](../../scripts/eif_release.py) builds the sdist
  and wheel, validates both the way an index will (`twine check --strict`,
  run from a throwaway environment rather than required on the host),
  installs the built wheel into a clean virtualenv and runs `eifctl
  version` from it. It then prints the publish commands and stops. Passes
  end to end on `0.1.0.dev0`.
- **The upload is a person's decision.** It takes owner credentials, and
  nothing in this repository performs it. That is the same boundary
  everything else here observes: EIF generates what a person then chooses
  to run.
- **Adapter scope is frozen** at four adapters, two required for v0.1
  (Claude Code, Cursor) and two experimental-supported (Codex, Hermes).
  See [`ROADMAP.md`](../../ROADMAP.md).

## What no claim is made about

These are not modest phrasings of positive results. They are gaps.

- **Human time.** No measurement exists of how long any part of this takes
  a person, on this repository or another one. Nothing on the site, in this
  file, or in the benchmark results states one.
- **Governed against ungoverned work.** No study compares the two end to
  end. The token cost of governance is stated on the site; the net balance
  is left open, because it is open.
- **Task quality.** The benchmark reports a contract, not an outcome. No
  baseline, no control group.
- **Real-repository breadth.** The reproducible slice is one synthetic demo
  project plus one real private pilot target. It is not a representative
  sample of engineering work.

## Where the bounded claims live

This file is a release-status summary, not the claims register. Every
capability statement on the website carries a `data-claim-id` that resolves
to [`site/src/content/claims.json`](../../site/src/content/claims.json),
whose entries in turn cite rows in
[`claims-evidence.md`](claims-evidence.md). A site build fails if a claim
ID is unknown, if forbidden wording appears, or if a count appears without
a nearby claim reference. That gate is unchanged by anything in this file.

## Release-day checklist

Ordered, with the manual steps marked. Nothing here runs itself.

1. `python -m pytest` and the site gate (`npm --prefix site run gate:site`)
   both green on the release commit.
2. Version set in [`pyproject.toml`](../../pyproject.toml) and the
   matching entry moved out of `[Unreleased]` in
   [`CHANGELOG.md`](../../CHANGELOG.md).
3. `python scripts/eif_release.py` clean, including the clean-environment
   install.
4. **Manual, owner credentials:** upload the artifacts.
5. **Done 2026-07-27:** the repository is public, and
   [`.github/workflows/pages.yml`](../../.github/workflows/pages.yml)
   publishes `site/` to GitHub Pages on any change under `site/`. The
   deploy runs `verify:claims:strict`, `verify:metadata` and
   `verify:bundle` before it serves anything, so a claim violation or an
   unsubstituted `__EIF_*__` marker stops it. `EIF_SITE_URL` lives in
   [`site/.env.production`](../../site/.env.production); the repository URL
   is a constant in `site/vite.config.js` and resolves in every mode.
6. **Done 2026-07-27, owner credentials, once:** the Pages site created with
   `gh api --method POST repos/<owner>/<repo>/pages -f build_type=workflow`.
   The workflow cannot do this for itself: its `GITHUB_TOKEN` may deploy to
   a Pages site but may not create one, so `configure-pages`'s
   `enablement: true` fails with "Resource not accessible by integration".
7. **Done 2026-07-27:** the site serves at
   <https://mike-arbuzov365.github.io/engineering-intelligence-framework/>.
   Checked against the real URL rather than against the workflow's green
   tick: the served page reports `eif:deploy-status: deployable`, its
   canonical and `og:image` are absolute under that origin, its `git clone`
   line and closing Source row carry the real repository, no `__EIF_*__`
   marker survives, and the console is clean.
8. **Manual, once, still open:** upload
   [`.github/social-preview.png`](../../.github/social-preview.png) at
   Settings -> General -> Social preview. It is generated from the same
   brand source as the site's own card by
   `npm --prefix site run generate:social-assets`, at the 1280x640 GitHub
   asks for. Without it, every link to this repository renders as GitHub's
   generic auto-card. There is no API for this one, so it stays a click.
9. Re-read this file. Any line that stopped being true is a line to change,
   not a line to leave.
