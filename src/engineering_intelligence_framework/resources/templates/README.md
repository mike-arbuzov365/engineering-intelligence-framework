# templates/

Reusable artifact templates.

## Product planning

[`idea.md`](idea.md) turns a raw request or opportunity into a sourced,
bounded artifact with an explicit approval and route.
[`prd.md`](prd.md) turns an approved idea into traceable product
requirements with observable acceptance criteria. See
[`playbooks/idea-planning.md`](../playbooks/idea-planning.md) and
[`playbooks/product-requirements-planning.md`](../playbooks/product-requirements-planning.md).

## Single-session task

[`task-scope.md`](task-scope.md) (scope/stop-condition declaration before
implementation), [`knowledge-delta.md`](knowledge-delta.md) (required
PR-description output, locale-rendered per instance),
[`session-closeout.md`](session-closeout.md) (end-of-session summary,
locale-rendered per instance), and
[`agent-instructions.md`](agent-instructions.md) (the source `eif_init.py`
renders into a project instance's entrypoint file, e.g. `CLAUDE.md`) -
built and in active use by the vertical slice.

Iterative tasks additionally use
[`bounded-evidence-loop.md`](bounded-evidence-loop.md) to declare success
evidence, the evaluator, iteration and remote-run budgets, stop conditions,
and a compact loop closeout.

## Execution packet (multi-session work)

[`session-launch.md`](session-launch.md) (one packet session) plus the
packet-level anatomy: [`packet-charter.md`](packet-charter.md),
[`packet-facts.md`](packet-facts.md),
[`packet-decisions.md`](packet-decisions.md),
[`packet-roadmap.md`](packet-roadmap.md),
[`packet-self-review.md`](packet-self-review.md),
[`packet-start.md`](packet-start.md), and
[`packet-closeout.md`](packet-closeout.md) - see
[`playbooks/execution-packet-planning.md`](../playbooks/execution-packet-planning.md)
for the workflow that uses them together.

Not yet ported: ADR, incident report, and rule-record templates - see
[`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#execution-packets).
