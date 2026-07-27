---
type: decision_register
status: validated
scope: framework
created: 2026-07-15
review_after: 2026-10-15
---

# Decision ledger

<!-- Knowledge source: owner decisions, private instance, 2026-07-14/15.
Sanitized for public release - no private repository names, machine paths,
or audit specifics that would identify the private instance. -->

<!-- Revised 2026-07-16 (review round 3, NEW-CORRECTION - not inherited
from the private instance, which uses a flat findings-ledger without this
distinction): `type: decision` + `status: draft` was internally
contradictory - this document isn't one decision, it's a register of many,
each with its own status (Ratified/Provisional/Open below), and the
register document itself is accurate and maintained (`status: validated`),
not a draft. Introduced `type: decision_register` for exactly this shape -
see knowledge-types.md#decision_register. This is a new taxonomy addition,
not a private-EI capability being ported; it exists to fix a defect found
in this document, not because the private instance has an equivalent. -->

**This register's own `status: validated` means the document accurately
reflects current decision statuses as of `created`/`review_after` below -
it does NOT mean every decision listed is ratified.** Each entry states
its own status explicitly.

Public, sanitized record of decisions behind this framework's naming,
licensing, and structure. **A decision is only marked `ratified` here if it
went through an explicit owner ratification step** - a decision that was
merely *implemented* because the evidence pointed one way is marked
`provisional`, not `ratified`, even if it's already in effect. This
distinction matters: a provisional choice can be revisited without
"reversing a ratified decision"; a ratified one needs an explicit
supersession to change.

## Ratified

### D-01: Product name
**Status: ratified.** `Engineering Intelligence Framework`, short form
`EIF`.
**Evidence:** a preliminary GitHub exact-name search and a PyPI/npm web
search found no exact match for `engineering-intelligence-framework`. This
is a preliminary collision check, **not** trademark clearance - full legal
clearance is still open, tracked in the public-readiness checklist in
[`docs/architecture/HOW-EIF-WORKS.md`](../../docs/architecture/HOW-EIF-WORKS.md#definition-of-public-ready).

### D-02: Descriptor
**Status: ratified 2026-07-16 (owner decision).** "A quality-first control
plane for governed AI-agent software development."
**Evidence/rationale:** explicitly re-stated by the owner as the intended
wording twice in direct instructions to this repository (2026-07-16), the
second time as an explicit ratification instruction. This ledger's own
rule for `ratified` is "went through an explicit owner ratification
step" - it does not additionally require an alternatives-considered round;
a prior revision of this entry incorrectly held it at `provisional`
pending exactly such a round, a bar this document never actually stated.
Corrected here rather than perpetuated.
**Limitations:** none specific to the descriptor text itself; see D-01's
trademark-clearance caveat, which applies to the product identity as a
whole.

### D-03: Public repository strategy
**Status: ratified 2026-07-16 (owner decision).** Clean-room extraction
into a new repository with fresh history remains the final strategy,
rather than migrating the private instance's history or exporting its
current tree as-is.
**Evidence/rationale:** a privacy audit of the private instance's tracked
files and git history found private-repository names and owner-identifying
strings spread across more than 100 tracked files and referenced in dozens
of commits - sanitizing that history after the fact was judged less
reliable than starting clean. Explicitly re-confirmed by direct owner
instruction (2026-07-16) as the final strategy, which is this ledger's own
bar for `ratified` (see D-02's note above on the corrected reading of that
bar).
**Limitations (real, not resolved by this ratification):**
- Trademark/domain clearance work is separate and still open (D-01).
- **The clean-room strategy's own premise - that this repository's history
  is free of the private instance's identifying content - has since been
  found NOT fully true**: a privacy audit (Stage 5, prior round) found the
  private pilot-target repository name leaked into four tracked files via
  normal development (not migrated history - content added directly to
  this repository's own history). The *strategy* (start clean, don't
  migrate) is ratified; it does not by itself guarantee ongoing hygiene,
  which failed at least once. **This repository's current OSS-facing tree
  now requires renewed history/metadata sanitation** before any public
  visibility change - see `PACKET-EIF-PUBLIC-HISTORY-AND-METADATA-SANITATION`
  (private planning packet) for the full audit this finding triggered.

### D-04: License
**Status: ratified.** Apache-2.0 for v0.1, see [`LICENSE`](../../LICENSE).

### D-06: Canonical framework language
**Status: ratified 2026-07-16 (owner decision).** English is the canonical
public framework language - ontology, schemas, code, commands, and file
paths stay in English regardless of a project's `documentation_locale`.
This was already the de facto design default (`locales/README.md`); this
entry ratifies it explicitly rather than leaving it an assumption.

### D-07: Ukrainian as a first-class supported project locale
**Status: ratified 2026-07-16 (owner decision).** Ukrainian ships as a
first-class supported project locale in v0.1: status messages, Knowledge
Delta, closeout headings, and knowledge retrieval (`locales/uk/`,
`scripts/tests/test_locale.py`, `test_journey.py`, `test_cursor_adapter.py`
scenario 16). **Not yet closed, and explicitly flagged as a limitation
rather than silently left out**: full agent-response localization and
`locales/uk/terminology.yaml` are not populated - these remain open
partial-locale-surface gaps to close (or explicitly re-scope out of v0.1)
before release, tracked in `docs/architecture/HOW-EIF-WORKS.md`'s
Definition of Public-Ready.

### D-10: Graphify/RTK as optional-only v0.1 integrations
**Status: ratified 2026-07-16 (owner decision).** Graphify and RTK are
official v0.1 integrations, but strictly optional: core EIF, the
bootstrap (`eif_init.py`), both adapters, `eif_verify_runtime.py` (doctor),
and degraded-mode operation must not depend on either. Verified true today
- neither adapter's registry entry, transaction layer, or test suite
references Graphify or RTK anywhere.

### D-11: Website timing
**Status: ratified 2026-07-16 (owner decision).** Website work follows
technical-preview readiness and a first honest benchmark result, but
precedes broad community launch - it is not gated on the full v0.1.0
release. Not started this round, consistent with this decision (no
benchmark result exists yet either).

### D-12: v0.1 benchmark publication scope
**Status: ratified 2026-07-16 (owner decision).** Synthetic fixtures only
for v0.1 - no private repositories, no customer/internal artifacts; a
public-repository corpus track is explicitly deferred, not part of v0.1.
Raw transcripts are published only after a privacy scan. Failed attempts
and harness errors are retained, never deleted from the record. No
token-savings claim is published without an accompanying quality result.
See `docs/benchmarks/README.md` and the (currently out-of-PR-scope, per
Stage 1.9) benchmark corpus packet for the methodology this decision
governs.

### D-09: Required v0.1 adapters
**Status: ratified 2026-07-16 (owner decision).** Required tested adapters
for the current v0.1 scope: **Claude Code** and **Cursor**. Graphify and RTK
remain optional integrations - neither adapter depends on them. See
[`adapters/README.md`](../../adapters/README.md#recommended-v01-priority)
for the underlying evidence (hook-reliability testing done while building
this repository) that motivated Cursor as the second adapter; that evidence
is about a different Cursor mechanism (tool-call hooks) than the Rules
mechanism `adapters/cursor/README.md` documents and `eif_init.py` generates
for - the two should not be conflated. Codex and Hermes remain deferred, not
ratified as required. (Moved here from a misplaced position under "Open"
in the prior revision of this file - its own status text already said
ratified; only the section placement was wrong.)

### D-05/D-08: CLI name and distribution model
**Status: ratified 2026-07-16 (owner decision).** CLI command `eifctl`;
distribution as an installable Python package
(`engineering-intelligence-framework`) with a `console_scripts` entry
point; an optional GitHub template/demo for onboarding, never the
dependency mechanism itself; no git submodule as the v0.1 default; no
copy-pasted standalone scripts as the primary public UX.
**Evidence:** `eifctl` checked directly against PyPI's JSON API (HTTP 404)
and the npm registry (HTTP 404) - no exact package-name collision. A real
package (`pyproject.toml`, `src/engineering_intelligence_framework/`, 7
subcommands - `init`, `doctor`, `search`, `render`, `privacy-scan`,
`validate`, `version` - each a thin wrapper over the exact same tested
`scripts/eif_*.py` functions) was built to a wheel and installed into a
clean venv whose own path contained a space and non-ASCII text, then
exercised end to end against a project path also containing a space and
non-ASCII text: init (fresh, routine upgrade, `--force` reconfigure with
a locale switch), doctor, validate, render, privacy-scan, uninstall/
reinstall - `scripts/tests/test_package_build.py`, 23/23 checks.
**The specific condition that kept this provisional in the prior revision
of this entry - independent Windows AND Ubuntu verification - is now
closed**: the CI matrix added in this same PR
(`.github/workflows/ci.yml`'s `package-build` job) ran this exact suite
on Windows and Ubuntu, Python 3.11 and 3.12 (4 combinations), and all 4
passed, confirmed twice across two separate commits/runs on this PR.
**Limitations, real and not resolved by this ratification:** not published
to PyPI (out of scope this round by explicit instruction); this PR itself
is intentionally not merged this round (stops at a green,
independently-reviewable state); one unrelated, pre-existing CI job on
this PR (`Knowledge Delta completeness`) failed against an apparent
external GitHub API disruption during this round (a raw `gh api` call
returning GitHub's own HTML error page instead of JSON, reproduced
directly outside CI too, on an unrelated PR number as well) - flagged as
a separate, unrelated finding, not fixed here, and not a defect in the
package this decision ratifies.

### D-13: Fail-closed CI runner consolidation
**Status: superseded by D-14 (2026-07-19).** Policy checks that share one
Python environment ran as sequential steps in one fail-closed job. The
package contract continued to run on Ubuntu and Windows with Python 3.11
and 3.12 on every PR and push. A post-merge push could reuse PR evidence
only when the exact merge commit was associated with one merged PR to
`main` and every context in `merge-policy.json` was successful; every
lookup error, missing context, non-success result, or direct push fell
back to full CI. This changed runner topology, not validation coverage,
and kept `merge-policy.json` as the only source of required context
names. Superseded because the evidence-reuse mechanism still created a
workflow run on every push (76 workflow runs across 2026-07-14 through
2026-07-18: 55 `pull_request`, 21 `push`), and every PR still allocated
nine hosted-runner jobs (one policy job, a four-combination package-build
matrix, its aggregate gate, a two-combination license-check matrix, and
its aggregate gate) - contributing to the GitHub Actions quota exhaustion
XREPO-01 was opened to address.

### D-14: Single required PR job, no push-triggered workflow
**Status: ratified 2026-07-19 (XREPO-01 Session 002).** Routine PR
validation runs as exactly one hosted job (`.github/workflows/ci.yml`,
context `PR smoke checks (required by policy)`): the fast local smoke
suite (`scripts/tests/smoke.py`) plus privacy scan, frontmatter/config
validation, YAML/JSON-Schema validation, Markdown link check, and
Knowledge Delta classification. Push to `main` triggers no workflow at
all - a merged PR was already fully validated by this job, so D-13's
evidence-reuse mechanism (`scripts/eif_pr_ci_evidence.py`, the
`ci-evidence` job) is dead code once nothing runs on push, and both were
removed rather than kept unused. The cross-platform package-build matrix
(Ubuntu/Windows x Python 3.11/3.12), the license-check matrix
(Ubuntu/Windows), and the full `scripts/tests/run_all.py` suite inventory
(all adapter/package/benchmark/merge-gate suites) moved to
`.github/workflows/release-check.yml`, triggered only by
`workflow_dispatch` before a technical preview or release, or run locally
with no Actions minutes spent (see that workflow's header comment for the
exact local-equivalent commands). This is a routine-topology change only:
no test was deleted without this disposition, and `merge-policy.json`
remains the single source of required context names,
`allow_no_checks: false`.
**Evidence:** GitHub PR #24 (`feat/benchmark-corpus-expansion-2026-07-18`)
showed all seven substantive D-13-era jobs pass while the two aggregate
required jobs failed in ~2s with `runner_id: 0` (no runner allocated) -
capacity evidence, not a product failure, and the immediate trigger for
this consolidation.

### D-15: Publication is allowed to run on push; validation still is not
**Status: provisional, in effect 2026-07-27.** D-14 states that push to
`main` triggers no workflow at all. `.github/workflows/pages.yml` does, so
the boundary is recorded here rather than left as a contradiction a reader
would find on their own. D-14's subject is routine *validation* topology:
which tests run where, how many hosted jobs a change allocates, and which
contexts are required to merge. Publishing an already-merged tree to GitHub
Pages is a different act, and the Pages workflow runs no test at all: no
Playwright, no Lighthouse, no axe, no Python suite. It installs from the
committed lockfile, runs the three fail-closed verifiers
(`verify:claims:strict`, `verify:metadata`, `verify:bundle`), builds, and
deploys. Those three are pure Node scripts with no browser, and they are
what stops an unknown claim ID, forbidden wording, a leaked private path, a
third-party runtime request or an unsubstituted `__EIF_*__` build marker
from reaching a public page; serving a bundle that fails them would make
having them pointless. The full site gate stays local and unhosted, exactly
as D-14 and `site/README.md` describe. Triggered only by a change under
`site/`, so a documentation commit does not redeploy an identical bundle.
Provisional rather than ratified: it is in effect because the site needs to
be served, not because it went through an owner ratification step. Creating
the Pages site itself stayed an owner-credentialed act, not because that is
preferable but because it is the only thing that works: a workflow's
`GITHUB_TOKEN` may deploy to a Pages site and may not create one, so
`configure-pages`'s `enablement: true` fails with "Resource not accessible
by integration". Done once, 2026-07-27, with
`gh api --method POST repos/<owner>/<repo>/pages -f build_type=workflow`,
and recorded in the workflow so it is not rediscovered from a failing run.

## Open (not yet decided)

*(none currently - D-09 through D-12 ratified 2026-07-16; D-05/D-08
ratified 2026-07-16; D-14 ratified 2026-07-19, superseding D-13 - see
"Ratified" above for the evidence that closed each open condition.)*

## How to ratify a decision

Move the entry from `Open`/`Provisional` to `Ratified` and record the
evidence. This file's own frontmatter `status: validated` describes
whether the register accurately reflects reality, not any individual
decision's status - it does not change when an entry moves. Do not
silently change a decision already marked `ratified` here - add a new
entry noting supersession, with rationale, per
[`core/ontology/status-lifecycle.md`](../ontology/status-lifecycle.md#superseded).
