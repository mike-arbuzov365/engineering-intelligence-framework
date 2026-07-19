---
session_id: eif-closure-003-operating-layer
status: in-progress
date: 2026-07-19
depends_on: eif-closure-002-cost-safe-ci
---

# SESSION-003 checkpoint: public operating layer

## What was built

- **10 playbooks** (`playbooks/*.md`): the full D-006 minimum set -
  `engineering-intelligence-operating-protocol` (entry point/index),
  `session-preparation`/`session-execution`/`session-closeout`,
  `execution-packet-planning`/`execution-packet-execution`/`execution-packet-review`,
  `knowledge-search`/`knowledge-ingest`/`knowledge-lint`. Each has proper
  frontmatter (`type: playbook` or `type: knowledge_operation`,
  `scope: framework`, per `core/schemas/knowledge-frontmatter.schema.json`)
  and a `Knowledge source: GENERALIZE of ...` comment naming what private
  source it's derived from and what was kept/dropped and why.
- **8 new templates** (`templates/packet-*.md` + `session-launch.md`):
  the packet-level anatomy (charter/facts/decisions/roadmap/self-review/
  start/closeout) that `docs/architecture/HOW-EIF-WORKS.md` explicitly
  flagged as "not ported yet," plus the per-session launch file used
  inside a packet (distinct from the existing `task-scope.md`, which
  covers a standalone single-session task).
- **6 skills** (`skills/*/SKILL.md`): `plan-execution-packet`,
  `run-execution-packet`, `review-execution-packet`, `knowledge-search`,
  `knowledge-ingest`, `knowledge-lint` - each a thin pointer to its
  playbook (one canonical source per D-007), with native `name`/
  `description` frontmatter.
- **`scripts/tests/test_operating_layer.py`** (new, added to
  `run_all.py`'s `SUITES`): structural tests - every playbook has the
  required frontmatter/heading/provenance comment, every skill's
  frontmatter `name` matches its directory, no unfinished-content
  markers (`TODO`/`FIXME`/`TBD`/`XXX`) in playbooks/templates/skills.
  111/111 passed.
- Updated `playbooks/README.md`, `templates/README.md`, `skills/README.md`
  (were empty-placeholder or partial indexes) and the two
  `docs/architecture/HOW-EIF-WORKS.md` "not ported yet" notes that are
  no longer accurate.

## Genericization approach

Read the private production instance's actual playbooks/templates (in
`wm-engineering-intelligence/40-playbooks/`, `30-templates/`,
`50-skills/`) as source material, then rewrote each in English,
stripped every private repo name/incident-specific reference, and
aligned terminology with this framework's *own* existing vocabulary
(the three-tier model and authority model already documented in
`HOW-EIF-WORKS.md`, the knowledge types already defined in
`core/ontology/knowledge-types.md`) rather than importing the private
instance's parallel vocabulary wholesale. Deliberately simplified out
multi-worktree/parallel-session coordination machinery throughout,
matching the precedent the existing `templates/task-scope.md` already
set (see its own `Knowledge source` comment) - a v0.1, single-agent,
sequential project instance doesn't need it; re-add only if a project
instance actually runs concurrent sessions.

`execution-packet-review.md` is close to a direct translation rather
than a heavy rewrite - the private source's git-hygiene-preflight and
behavioral-evidence-over-existence-evidence lessons are general, not
private-instance-specific, and are exactly the kind of thing this
session's own [`execution-packet-review.md`](../playbooks/execution-packet-review.md)
now says to apply when reviewing this very packet's later sessions.

## Scope deliberately not covered (per D-006 "minimum," not silently dropped)

- Parallel-session coordination, customer-facing playbooks (intake,
  engagement workflow), curator/retro automation, and their skills -
  `playbooks/README.md`/`skills/README.md` now say this explicitly.
- ADR, incident-report, and rule-record templates -
  `templates/README.md` says this explicitly.
- Wiring `playbooks/*.md`/`templates/*.md`/`skills/*/SKILL.md` into the
  CI frontmatter-validation step (`ci.yml`'s existing
  `eif_validate_frontmatter.py` call) - confirmed all 10 playbooks pass
  that validator directly (`playbooks/*.md` glob, one expected failure
  on `README.md` itself, which correctly has no frontmatter - same
  pattern `core/ontology/*.md`'s glob avoids only because that directory
  happens to have no README). Left for Session 004, which already owns
  runtime/adapter-discovery wiring for these same directories - avoids
  touching `ci.yml` again immediately after Session 002 for a change
  that fits more naturally with Session 004's own scope.
- Deep genericization of `execution-packet-planning.md`/
  `execution-packet-execution.md` down to the private source's full 45K/
  16K depth - written instead as a concise, complete workflow grounded in
  this packet's own lived example (`XREPO-01`, read in full during
  Sessions 001-002) plus the newly-written templates, per the Charter's
  own "minimum coherent slice" principle. Nothing from D-006's required
  list is missing; the private versions' extra depth (multi-repo registry
  coordination, customer-engagement-specific packet modes) genuinely
  doesn't apply to a single-project-instance adopter.

## Verification

| Command | Result |
|---|---|
| `python scripts/tests/test_operating_layer.py` | 111/111 passed |
| `python scripts/tests/smoke.py` | 44/44 passed |
| `python scripts/eif_privacy_scan.py --repo .` | 0 unsuppressed findings (2 real findings caught and fixed mid-session - see Knowledge Delta) |
| `python scripts/eif_check_links.py --repo .` | all relative links resolve |
| `python scripts/eif_validate_frontmatter.py --framework-root . --instance-root . "playbooks/*.md"` | all 10 playbooks valid; `README.md` fails as expected (not a knowledge artifact) |
| `git diff --check` | clean |

## Exit criteria status

- [x] D-006 minimum playbooks/templates/skills exist.
- [x] One canonical source per workflow - skills point to playbooks,
      playbooks point to templates, nothing duplicates a checklist
      that already has a canonical home (e.g. `session-closeout.md` the
      playbook points to `templates/session-closeout.md` rather than
      restating its steps).
- [x] A synthetic packet can be planned/run/reviewed from public docs
      alone - the full `templates/packet-*.md` anatomy plus
      `execution-packet-planning`/`-execution`/`-review` playbooks cover
      it end to end.
- [x] Every public artifact passes privacy/language/link checks.
- [x] No unresolved placeholders or private identifiers remain (verified
      by `test_operating_layer.py` and the privacy scan, not asserted).
- [x] No remote run occurred (all verification local).

## Knowledge Delta

- Two real privacy-scan findings caught mid-session, both self-inflicted:
  this session's own `.session-context/` checkpoint files leaked absolute
  local filesystem paths - once in Session 001's checkpoint (caught in
  Session 002), and again in Session 002's own checkpoint *while
  describing that exact fix* (caught here). Confirms the Session 002
  Knowledge Delta's lesson generalizes: writing *about* a path-leak
  incident is itself a place a path can leak back in - reread
  newly-written checkpoint prose with the same scrutiny as the fix it
  describes, not just the code.
- This framework already has a real, machine-validated knowledge
  frontmatter schema (`core/schemas/knowledge-frontmatter.schema.json`)
  and ontology (`core/ontology/knowledge-types.md`) richer than what the
  private source's own playbooks assumed (e.g. a dedicated
  `knowledge_operation` type, distinct from `playbook`, for exactly the
  search/ingest/lint trio). Ported content should be checked against
  *this* framework's schema/ontology, not just translated 1:1 from the
  private convention - the two have already diverged in useful ways.
