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
frontmatter validation failed on it from the day it was added. It states what is true of this repository right now (the
version in pyproject.toml, that no artifact is on a package index, what the
release script does and where it stops), which is empirical, so `fact` with
an OBSERVED label read from the code itself. -->


# Release status

Where the current 0.x line actually stands, and everything the website used to say
about its own release status, in one place off the page.

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

- **Version.** `0.2.6` in [`pyproject.toml`](../../pyproject.toml) is dated
  2026-08-02 in [`CHANGELOG.md`](../../CHANGELOG.md) and distributed through
  GitHub Releases.
- **Installable from a clone or GitHub release artifact.** `pip install .`
  builds and installs a real wheel. The
  [GitHub release](https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases/tag/v0.2.6)
  also carries the validated wheel and source distribution. The
  installed-wheel synthetic journey runs `eifctl` from that build in a
  clean virtual environment.
- **0.2.6 makes the graphic-design profile usable for everyday work.** The
  generated instruction now routes light, structured and packet work; bounded
  edits and exports no longer require a full brief or closeout. `doctor`
  reports the active instruction, profile, profile skills and honest project-
  memory status. A new one-wheel package smoke covers the exact Codex +
  `graphic-design` installation path without running the exhaustive release
  package suite during ordinary work. The profile and automatic skill
  discovery introduced in 0.2.5 remain the base of this path.
- **0.2.1 through 0.2.4 came from real walkthroughs, not synthetic ones.** The
  0.2.0 path was run end to end on two private repositories on Windows. It
  found that the published `eifctl init <path>` command did not exist, that a
  fresh Windows clone failed `doctor` on line endings alone, and that a
  fleet pass with nothing to do still dirtied every repository. Those are
  fixed and covered by `scripts/tests/test_line_endings.py`. Synthetic
  coverage did not catch them because it never cloned a project or ran the
  documented command text. 0.2.2 exists because the same method was applied
  again to 0.2.1 itself: installing the published wheel and cloning a real
  connected project showed the line-ending fix was incomplete, so that suite
  now asserts the property end to end (clone, upgrade, tree still clean)
  rather than the mechanism. 0.2.4 came from the same place again: upgrading a
  real connected project showed that `upgrade` refused to run because of drift
  the upgrade itself repairs, and that it told the operator to revert changes
  a clean tree did not contain.
- **The one suite that never ran automatically now passes.** The three
  installed-wheel integration-status checks in
  `scripts/tests/test_package_build.py` had failed on 0.2.0 through 0.2.3.
  They are fixed in 0.2.4, and the product defect they were masking - a
  version probe that could not start being reported as a configuration error -
  is fixed with them. The exhaustive suite is deliberately excluded from
  `run_all.py`; it runs directly at the local release gate or from the
  `workflow_dispatch`-only `release-check.yml` fallback. Ordinary
  package-relevant changes now have a separate one-wheel smoke path, so the
  exhaustive suite is no longer the first packaging check an agent reaches.
- **Not on a package index.** No artifact has been uploaded to PyPI or any
  other index. `pip install engineering-intelligence-framework` does not
  resolve.
- **Release tooling is complete up to the upload.**
  [`scripts/eif_release.py`](../../scripts/eif_release.py) builds the sdist
  and wheel, validates both the way an index will (`twine check --strict`,
  run from a throwaway environment rather than required on the host),
  installs the built wheel into a clean virtualenv and runs `eifctl
  version` from it. It then prints the publish commands and stops. Passes
  end to end.
- **The upload is a person's decision.** It takes owner credentials, and
  nothing in this repository performs it. That is the same boundary
  everything else here observes: EIF generates what a person then chooses
  to run.
- **Private-workspace and project lifecycle commands are included.**
  `eifctl workspace new` creates a local user-owned workspace inside L2;
  `eifctl workspace profile list/install` explicitly installs a professional
  starter; `eifctl new --profile` creates a local project repository with a
  validated profile assignment; `eifctl projects add` connects an existing
  EIF instance; and the upgrade commands plan before applying separate
  framework and workspace provenance axes. Detach removes only
  workspace-managed state. See the
  [`project lifecycle guide`](../guides/project-lifecycle.md).
- **Adapter scope is frozen** at four adapters - Claude Code, Cursor, Codex
  and Hermes - and all four are supported (D-16, 2026-07-27, retiring the
  two-tier split D-09 recorded). See [`ROADMAP.md`](../../ROADMAP.md).

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
- **Real-repository breadth.** The reproducible public slice is one synthetic
  demo project. Owner-operated adoption findings now span three private
  repositories, but their contents and runs are not public fixtures and no
  independent operator has reproduced them. This is not a representative
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
2. Set the release version in [`pyproject.toml`](../../pyproject.toml), move
   the completed entries from `[Unreleased]` into a dated version in
   [`CHANGELOG.md`](../../CHANGELOG.md), and update current-version wording in
   README, the claims register and the site claim manifest.
3. `python scripts/eif_release.py` clean, including the clean-environment
   install.
4. **Owner credentials:** push the annotated tag matching the version and
   publish the GitHub Release with the wheel and source distribution produced
   and validated by `scripts/eif_release.py`. Uploading the same artifacts to
   a package index is a separate owner decision and is not part of a GitHub
   release.
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
8. **Done 2026-07-27, owner, once:**
   [`.github/social-preview.png`](../../.github/social-preview.png) uploaded
   at Settings -> General -> Social preview. It is generated from the same
   brand source as the site's own card by
   `npm --prefix site run generate:social-assets`, at the 1280x640 GitHub
   asks for. Confirmed against the API rather than against the settings
   page: `gh repo view --json usesCustomOpenGraphImage,openGraphImageUrl`
   reports `true` and a `repository-images.githubusercontent.com` URL, so
   links to this repository render the real card instead of GitHub's
   generic auto-card. There is no API to *set* it, so it stayed a click.
   The repository description, homepage URL and topics are set the same
   way, and the homepage points at the live site.
9. Re-read this file. Any line that stopped being true is a line to change,
   not a line to leave.

## What the website says about status now, and why

As of 2026-07-27 (SB-027) nothing on the site describes itself as
unreleased, and no capability row calls its evidence a pilot. The three
meta descriptions say "Open source, Apache-2.0" where they used to say
"Pre-release", and section 09 states each capability with the scope of the
check behind it rather than with a `Limitation:` line under it.

None of that changed a claim. The claims register is untouched, every row
still carries its `data-claim-id`, and the two things the benchmark does
not establish - efficiency and task quality - are still stated in the row
that would otherwise imply them. What changed is that the page stopped
narrating its own release process to a reader who came to find out what EIF
is. The release process is this file's job.

**Still open, as a separate owner decision:** no artifact is on a package
index, so `pip install engineering-intelligence-framework` does not resolve.
The GitHub release and source installation are the supported 0.2.6
distribution paths.
