# Template: Session Closeout

<!-- Knowledge source: SPLIT of the private EI's session-closeout.md (11
steps). Kept: assess-what-happened, run verification with PASS/FAIL (not
"looks OK"), fill the Knowledge Delta, final report shape. Dropped:
planning-status/dashboard updates, the visual-hub drift gate, worktree
cleanup, and parallel-session-group manifest updates - none of these have
an equivalent in a single-session, single-repo v0.1 project instance. If a
project instance later grows multi-session packets, planning-status and
worktree steps are the first candidates to re-add, not reinvent. -->

Run at the end of any EIF session that changed code, decisions, or
documentation. Turns ephemeral session memory into durable knowledge
(Knowledge Delta + `knowledge/`) and then discards the ephemeral part.

A locale-rendered version of this template's headings lives at
`locales/<locale>/templates/session-closeout.md`.

## Step 1 - What happened

- [ ] Which files changed?
- [ ] What was decided?
- [ ] What new facts, risks, or edge cases surfaced?
- [ ] Any hypotheses confirmed or rejected?
- [ ] Any incidents (broken build, failed test, secret leak)?

## Step 2 - Run verification

- [ ] The commands listed in the task-scope document's verification
      section were actually run.
- [ ] Results are `PASS`/`FAIL`, not "looks fine."
- [ ] The existence of a file, a successful build, or a merge is not
      treated as behavioral evidence on its own - a test that actually
      exercises the changed behavior is.
- [ ] If a check depends on an environment that isn't available, its
      result is `SKIPPED`, not `PASS`.
- [ ] If verification failed, go back to implementation - don't close out.

## Step 2a - Close the bounded loop

- [ ] Final status is `PASS`, `BLOCKED`, or `DEFERRED`.
- [ ] Iterations and remote runs used are recorded against their budgets.
- [ ] Success evidence and encountered failure signatures are recorded.
- [ ] Adaptations explain how the method changed after negative evidence.
- [ ] The Tier 3 checkpoint is deleted; only validated learning is routed to
      Knowledge Delta.

## Step 3 - Fill the Knowledge Delta

Use [`templates/knowledge-delta.md`](knowledge-delta.md) (or its locale
variant). If the session taught nothing, use the explicit
`<!-- no-knowledge-delta: mechanical task -->` marker instead of leaving
the section blank.

## Step 4 - Route new knowledge artifacts

For each new fact/rule/decision/risk/edge case/failure pattern: decide
whether it belongs in this project instance's `knowledge/` directory
(local) or should be proposed for the framework/shared level (see the
Knowledge Delta's "Promote to shared knowledge base?" question). Apply
`scripts/eif_validate_frontmatter.py` before treating anything as durable.

## Step 5 - Final report

```markdown
## Session Done: <short task name>

- Branch/PR: <link>
- Verification: <PASS/FAIL with the actual commands run>
- Artifacts created:
  - knowledge/...
- Promoted to shared knowledge base: <yes/no, which candidates>
- Not done / out of scope: <list with reasons>
- Open questions left: <list>
- Loop: <PASS/BLOCKED/DEFERRED; iterations; remote runs; evidence>
- Knowledge Delta: <included in PR>
```

## Anti-patterns

- Closing out without verification - "tests are green" without having run
  the commands.
- Copy-pasting a Knowledge Delta from a previous session - it stops
  meaning anything.
- Marking a task complete on class/endpoint/script/build/merge evidence
  without a behavioral test.
