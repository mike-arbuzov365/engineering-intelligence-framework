# templates/

Reusable artifact templates.

4 built and in active use by the vertical slice - [`task-scope.md`](task-scope.md)
(scope/stop-condition declaration before implementation),
[`knowledge-delta.md`](knowledge-delta.md) (required PR-description output,
locale-rendered per instance), [`session-closeout.md`](session-closeout.md)
(end-of-session summary, locale-rendered per instance), and
[`agent-instructions.md`](agent-instructions.md) (the source `eif_init.py`
renders into a project instance's entrypoint file, e.g. `CLAUDE.md`).

Not yet ported: ADR, planning-packet artifacts (charter, facts, decisions,
roadmap), incident report, rule record - see
[`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#execution-packets).
