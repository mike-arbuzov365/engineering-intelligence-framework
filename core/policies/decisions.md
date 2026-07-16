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

## Provisional (strongly evidenced, not formally ratified)

### D-02: Descriptor
**Status: provisional.** "A quality-first control plane for governed
AI-agent software development." Adopted alongside D-01; not separately
ratified through an explicit decision step. Low risk to revisit.

**Re-affirmed 2026-07-16**: the owner's instruction for this round quoted
this exact descriptor verbatim as the intended wording. Kept at
`provisional` rather than moved to `ratified` because re-stating existing
wording is not the same as a fresh ratification step with alternatives
considered - the bar this ledger itself sets for `ratified` (see D-03's
same reasoning below). Low risk to revisit either way.

### D-03: Public repository strategy
**Status: provisional, strong evidence.** Clean-room extraction into a new
repository with fresh history, rather than migrating the private
instance's history or exporting its current tree as-is.
**Evidence:** a privacy audit of the private instance's tracked files and
git history found private-repository names and owner-identifying strings
spread across more than 100 tracked files and referenced in dozens of
commits. Sanitizing that history after the fact was judged less reliable
than starting clean. This repository's own history starts from this
decision - there is nothing to migrate.
**Why still provisional:** this was a judgment call under time pressure,
not a formal ratification round with alternatives considered. It should be
explicitly ratified (or revisited) before claiming it as settled in
external-facing material (website, articles).

**Re-affirmed 2026-07-16**: the owner's instruction for this round
confirmed this remains the final strategy. Kept at `provisional` for the
same reason as D-02 - confirmation of an existing choice is not the
alternatives-considered ratification step this ledger requires for
`ratified`, even though the choice itself is now doubly confirmed.

### D-05/D-08: CLI name and distribution model
**Status: provisional, strong evidence, not formally ratified - Ubuntu
verification pending.** Preferred decision: CLI command `eifctl`;
distribution as an installable Python package with a `console_scripts`
entry point; an optional GitHub template/demo for onboarding, never the
dependency mechanism itself; no git submodule as the v0.1 default; no
copy-pasted standalone scripts as the primary public UX.
**Evidence, 2026-07-16:** `eifctl` checked directly against PyPI's JSON API
(`https://pypi.org/pypi/eifctl/json` - HTTP 404, no such package) and the
npm registry (`https://registry.npmjs.org/eifctl` - HTTP 404) - no exact
package-name collision on either registry. A general web search for
"eifctl" as a command name found no existing tool using it (only
unrelated fuzzy matches - `ifctool`, EF Core CLI tools, etc.). A real
clean-venv packaging spike (`pyproject.toml` with `[project.scripts]
eifctl = ...`, built to a wheel, installed into a fresh venv whose own
path contained spaces) succeeded: the `eifctl` command resolved and ran
correctly. Python support: this entire session's testing ran on Python
3.11.15 (not just CI's pinned 3.12), so 3.11+ is empirically exercised,
not just claimed.
**Why still provisional, not ratified:** the pre-ratification checklist
this round's instruction specified included Windows **and** Ubuntu
verification. Windows is directly verified (above). Ubuntu was **not**
independently verified this round - no local Linux environment was used
for it (this repository's own CI already runs on Ubuntu 24.04 generally,
so Stage 4's actual CI wiring, if that stage proceeds, is where real
Ubuntu verification of the packaged CLI specifically would happen - not
substituted for here). Move to `ratified` once that's closed, or revisit
if it reveals a problem the Windows spike didn't.

## Open (not yet decided)

*(none currently - D-09 through D-12 ratified 2026-07-16; D-05/D-08
provisional above; see "Provisional" for what's still short of a full
ratification bar and why.)*

## How to ratify a decision

Move the entry from `Open`/`Provisional` to `Ratified` and record the
evidence. This file's own frontmatter `status: validated` describes
whether the register accurately reflects reality, not any individual
decision's status - it does not change when an entry moves. Do not
silently change a decision already marked `ratified` here - add a new
entry noting supersession, with rationale, per
[`core/ontology/status-lifecycle.md`](../ontology/status-lifecycle.md#superseded).
