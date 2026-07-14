# Template: Task Scope and Stop Conditions

<!-- Knowledge source: SPLIT of the private EI's session-launch-template.md.
Kept: goal, explicit scope, no-touch zone, concrete verification commands,
boolean exit criteria, an experience-retrieval preflight line. Dropped:
worktree/branch bookkeeping, session_id collision rules, depends_on
sequencing, parallel_group coordination - these exist to coordinate
multiple concurrent sessions on the same repo, which a single-session v0.1
project instance does not need. Re-add them only if a project instance
actually runs multiple concurrent agent sessions against the same repo. -->

One task, one file. Written before implementation starts; referenced, not
duplicated, by the Knowledge Delta and closeout.

## Goal

<1-3 sentences. What this task does. Clearly bounded.>

## Experience retrieval preflight

Before implementing, search existing knowledge for anything relevant
(`scripts/eif_search_knowledge.py "<query>"`). Record what was found - or
explicitly record that nothing relevant was found. Do not skip this step
because the task looks simple; the whole point is that a plausible-looking
simple approach can be exactly what a past lesson warns against.

- Searched for: <query>
- Found: <artifact path, or "nothing relevant found">
- How it changes the plan: <concrete effect on the approach below, or "n/a">

## In scope

<What this task must accomplish. What "done" looks like.>

## Out of scope / do not touch

<Explicit list of files, directories, or systems this task must not
change.>

## Verification

<Concrete, runnable commands - not "run the tests." Example:
`pytest tests/test_calendar_utils.py -v`.>

## Exit criteria

<Boolean checklist. The task is done only when every item is checked.>

- [ ]
- [ ]

## Stop conditions

Stop and ask for an explicit decision if:

- the source of truth for a requirement is ambiguous or contradictory;
- a change would require a rule with global/framework-wide effect;
- the only source for a claim is unverified chat memory with no way to
  validate it.
