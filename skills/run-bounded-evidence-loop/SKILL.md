---
name: run-bounded-evidence-loop
description: >
  Run an iterative engineering task with explicit success evidence,
  evaluation, iteration and remote-run budgets, adaptation, and stop rules.
  Use for test/fix/refine cycles; not for unbounded autonomous repetition.
---

# Skill: Run Bounded Evidence Loop

<!-- Knowledge source: EIF Bounded Evidence Loop research, 2026-07-21. -->

Follow
[`playbooks/bounded-evidence-loop.md`](../../playbooks/bounded-evidence-loop.md)
as the canonical workflow and use
[`templates/bounded-evidence-loop.md`](../../templates/bounded-evidence-loop.md)
for the loop contract and iteration record.

Before acting, require observable success evidence, an evaluator, a positive
iteration limit, a remote-run budget, and stop conditions. Close only as
`PASS`, `BLOCKED`, or `DEFERRED`; a completion phrase is never proof.
