---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - session-preparation.md
  - session-closeout.md
  - ../templates/task-scope.md
---

# Playbook: Session Execution

<!-- Knowledge source: GENERALIZE of the private EI's session-execution.md.
Kept: the three-tier read order, the experience-retrieval preflight, the
start-state check before the first change, the pause-vs-fail distinction.
Dropped: worktree/parallel-session-specific steps with no equivalent in a
single-agent, single-worktree v0.1 project instance. -->

Run a prepared task or packet session. The artifact from preparation
(a task-scope file or a session launch file) is the source of truth -
this playbook does not depend on the preparation chat's history.

## Preconditions

- A task-scope file or session launch file exists.
- If this is a packet session, its `depends_on` sessions are already
  merged/complete.

## Step 1 - Read in tier order

Per the framework's three-tier model
([`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#the-three-tier-context-model)):

1. **Tier 1** - this framework: only the playbooks/templates/ontology
   actually relevant to the task at hand, not everything.
2. **Tier 2** - this project instance: its persistent agent-instruction
   file, relevant `knowledge/` artifacts, the task-scope or launch file
   itself.
3. **Tier 3** - nothing yet; this step creates it next.

## Step 2 - Experience retrieval preflight

Before implementing, search `knowledge/` for anything relevant
(`scripts/eif_search_knowledge.py "<query>"`). Record what was found in
the task-scope file's preflight section, or record explicitly that
nothing relevant was found. Do not skip this because the task looks
simple - a plausible-looking simple approach is exactly what a past
lesson is most likely to warn against.

## Step 3 - Verify the starting state

Before the first change:

1. Confirm the branch/working state matches what the task-scope or
   launch file expects.
2. If a prior attempt's state exists (e.g. a session context file for
   this same session), read it and continue from its progress instead of
   starting over.

If something doesn't match - stop and say so. Do not silently "fix" an
unexpected starting state.

## Step 4 - Execute against scope

Rules:

- The Facts file (if this is a packet session) outranks stale prose
  elsewhere.
- Ratified decisions resolve uncertainty without stopping.
- The no-touch zone is not negotiable mid-session.
- Verification commands are exactly what the task-scope/launch file
  states - not a substitute the agent judges "close enough."

Anti-patterns:

- Working outside the declared scope because it "seems related."
- Touching the no-touch zone because it "seems like it needs it."
- Declaring verification done without having actually run the commands.
- Expanding scope into an adjacent refactor mid-session.

## Step 5 - Move to closeout

Once every exit criterion is met, run
[`session-closeout.md`](session-closeout.md).

## If you need to pause mid-session

1. Record progress so far (what's done, what's next).
2. Commit work-in-progress on the feature branch - never on the
   project's main/integration branch.
3. Do not run closeout - the session isn't finished, and closeout exists
   to mark durable completion, not a save point.

## If the session is genuinely blocked

1. Record the blocker and what was tried.
2. Stop. Do not guess past a safety/decision boundary the packet's
   decisions (or the task-scope's stop conditions) didn't already resolve.
3. Wait for an explicit decision before continuing.
