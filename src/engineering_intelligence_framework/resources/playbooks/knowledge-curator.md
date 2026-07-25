---
type: knowledge_operation
status: validated
scope: framework
confidence: medium
created: 2026-07-25
related:
  - knowledge-lint.md
  - knowledge-ingest.md
  - run-retro.md
  - execution-packet-planning.md
  - ../core/ontology/status-lifecycle.md
---

# Playbook: Knowledge Curator

<!-- Knowledge source: GENERALIZE of the private EI's knowledge-curator.md
(v2, with findings ledger and active learning). Kept: the ledger with stable
finding IDs and recurrence escalation, the fix-class model with a closed
safe-fix list and hard path guards, the severity and routing taxonomies, the
repo-state rules, closure-requires-evidence, and the never-merge boundary.

Dropped: that instance's private index paths and PowerShell collectors
(`curator-scan.ps1`, `repo-hygiene.ps1`), its Ukrainian language-drift
checks (an instance convention, not a framework rule), its HTML dashboard
parity checks, and its cross-repo workspace scanning - this framework has
no equivalent multi-repo registry to scan.

Renamed: the private version calls its fix levels "Tier A/B/C". Here they
are CLASSES, because "layer" is already the framework's word for the
context model and reusing "tier" next to it invites exactly the confusion
the layer rename removed. -->

Retro asks what repeated. The curator asks a different question again:
**what in the knowledge base itself has rotted?** Stale artifacts,
orphans, broken authority links, findings that were "resolved" and came
back. It aggregates signals that already exist into one ranked list with
an owner path for each, instead of leaving them scattered across a lint
run, a closeout, and someone's memory.

It is a maintenance operation, not an authoring one. **It never merges
anything, and it never edits another project's source.**

## When to run this

- Before a promotion batch into the framework layer.
- After a packet closeout that changed architecture, methodology or
  skills.
- Before packet planning, as a freshness gate.
- When an agent repeatedly asks something the knowledge base should have
  answered - that is a retrieval or coverage defect, not a model problem.
- On a slow cadence for an active instance, when no event-based run has
  happened.

## What makes it different from the neighbouring operations

| Operation | Question it answers |
|---|---|
| [`knowledge-search.md`](knowledge-search.md) | What do we already know about this task? |
| [`knowledge-ingest.md`](knowledge-ingest.md) | Should this evidence become a durable artifact? |
| [`knowledge-lint.md`](knowledge-lint.md) | Is this one artifact good enough to promote? |
| [`run-retro.md`](run-retro.md) | What keeps happening across sessions? |
| **`knowledge-curator.md`** | **What in the knowledge base needs maintenance, how urgently, and who owns it?** |

The curator does not re-implement the others. It reads their output.

## Inputs

Collect only signals that already exist. A curator run that has to
generate its own evidence has become an authoring session:

- Artifacts under the configured `knowledge.root`, with their `status`,
  `confidence` and `review_after`.
- The generated knowledge index: orphans, artifacts with no incoming
  `related:` link.
- Recent Knowledge Deltas and closeouts, especially their deferred
  sections - a deferred item with no owner path is a finding.
- `scripts/eif_check_links.py` output: broken relative links.
- `scripts/eif_privacy_scan.py` output, including suppression hygiene.
- `scripts/eif_validate_frontmatter.py` output: schema-invalid artifacts.
- Optional integration health, if any is configured (`eifctl doctor`).
- The findings ledger from the previous run.

## The findings ledger

The curator's own artifact, and the thing that makes it more than a
repeated lint. Each finding gets a stable ID that survives across runs, so
the interesting question becomes answerable: **is this new, or is it the
fourth time?**

Each entry carries: ID, what was observed, where, severity, routing, fix
class, evidence label (`OBSERVED`/`INFERRED`/`ASSUMED`), status, first
seen, last seen, occurrence count.

Every report diffs against it:

- **New** - no existing ID.
- **Recurring** - same ID or same class and path.
- **Closed since last run** - with verification evidence, not assumption.
- **Suppressed** - acknowledged, excluded from the backlog, still recorded.
- **Regressed** - was resolved, is observed again. This one deserves an
  explanation of the prevention gap, not just a re-open.

**Recurrence escalation.** A finding still open at three or more
occurrences gets its severity raised one level and needs a prevention
proposal, not another fix. Something recurring three times is a systemic
gap, and treating it as three independent incidents is how it stays one.

## Fix classes

| Class | What it is | What the curator may do |
|---|---|---|
| **A - safe fix** | Mechanical, reversible, semantically unambiguous, inside the framework layer | Apply on its own branch and open a pull request. **Never merge it.** |
| **B - proposed fix** | A semantic change that can be drafted | Include the draft in the report; a human or a later session applies it |
| **C - defer to packet** | Needs a decision, an architectural change, or an edit outside this instance | Route to packet planning; draft a decision-readiness skeleton if several findings cluster |

Class A is a **closed list**. Anything not on it is B or C by definition:

1. Adding or refreshing `review_after` per the freshness policy.
2. Adding `related:` backlinks where the report names the exact mapping.
3. Regenerating the knowledge index, when no dirty source files would be
   legitimised by the regeneration.
4. Fixing broken relative links where the target is unambiguous from
   history (a file was renamed or moved).
5. Updating the findings ledger, which the curator owns.

**Class A never touches** `core/ontology/`, `core/policies/`, any
`SKILL.md`, `.github/workflows/`, or anything outside the instance it was
pointed at. Those are B or C regardless of how mechanical the edit looks.

## Severity

| Severity | When |
|---|---|
| `BLOCKER` | Secrets, private data, raw reasoning committed as knowledge, a broken authority chain, or anything that makes the source hierarchy unreliable |
| `MAJOR` | Wrong type or status, missing index entry, dead authority link, significant orphan drift, a recurring failure with a clear maintenance action |
| `MINOR` | Formatting, weak links, localised stale metadata, a stale-but-still-valid artifact |

## Routing

A closed set. New values require editing this playbook, which is the point
- an open-ended routing vocabulary stops being sortable.

| Routing | Meaning |
|---|---|
| `fix-now` | Trivial, safe, inside the framework layer, no decision needed |
| `defer-to-packet` | Needs a decision, a packet, or an edit outside this instance |
| `promote` | A local lesson validated widely enough to propose for the framework layer |
| `retro-inbox` | A real signal that is not yet actionable |
| `intentional-divergence` | Documented local difference, not a defect |
| `do-not-touch` | Dirty tree, onboarding state, or a safety boundary |

Routing and fix class are **different fields**. A fix class is not a
routing token.

## Repository state

State gates what the curator may propose, before severity does:

| State | Rule |
|---|---|
| `clean` | Normal routing applies |
| `dirty` | Scan only. Never `fix-now`; use `do-not-touch` or `defer-to-packet` |
| `onboarding` | Draft artifacts are not failures. Only flag broken safety rules |
| `not-scanned` | Record explicitly. Not a failure, and not silently omitted |

## Closure requires evidence

A finding becomes `resolved` only against evidence: a merged change, a
regenerated index, a passing check. Not "it looks fixed", and not the same
run that proposed the fix asserting its own success.

If a resolved finding's raw signal returns, it is `regressed`, and the
report explains why prevention did not hold.

## Suppression

Allowed only for a false positive or a documented exception, and only
with: a rationale, the source artifact, an expiry date or review trigger,
and who accepted it. A suppressed finding leaves the backlog but stays in
the ledger. A suppression that expires, or stops matching what it was
written for, becomes a finding itself.

## Output

Write the report from [`templates/curator-report.md`](../templates/curator-report.md).

## Automation boundary

Deliberately conservative, because a maintenance agent with write access
to its own governance is the failure mode this whole framework exists to
prevent:

- The curator **never merges**, and never pushes to the default branch.
- Class A fixes go on their own branch, in a pull request, for a human.
- It never edits source outside the instance it was pointed at; findings
  there are delivered as reports or issues, not commits.
- It does not run paid or external scans.
- Default mode is read-only. Applying fixes is an explicit opt-in.

## Anti-patterns

- Running the curator to *find* problems it then immediately fixes and
  merges. The separation between finding and merging is the safeguard.
- Letting a finding sit at `open` for many runs without escalating it.
  That is what the occurrence count is for.
- Marking something `resolved` in the same run that proposed the fix.
- Expanding the Class A list because a particular edit "is obviously
  safe". If it needs an argument, it is Class B.
- Treating `not-scanned` as clean.
