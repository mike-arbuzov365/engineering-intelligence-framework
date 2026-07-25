# playbooks/

Step-by-step instructions for recurring engineering-intelligence operations.

| Playbook | Covers |
|---|---|
| [`engineering-intelligence-operating-protocol.md`](engineering-intelligence-operating-protocol.md) | Entry point: routing, skill index, stop conditions |
| [`bounded-evidence-loop.md`](bounded-evidence-loop.md) | Bounded action/observation/adaptation cycles with evidence and budget guards |
| [`session-preparation.md`](session-preparation.md) | Scoping work, task vs. packet routing |
| [`session-execution.md`](session-execution.md) | Running a prepared task or session |
| [`session-closeout.md`](session-closeout.md) | Ending a session, Knowledge Delta |
| [`execution-packet-planning.md`](execution-packet-planning.md) | Planning multi-session work |
| [`execution-packet-execution.md`](execution-packet-execution.md) | Running a planned packet's sessions |
| [`execution-packet-review.md`](execution-packet-review.md) | Independently auditing a closed packet |
| [`knowledge-search.md`](knowledge-search.md) | Finding relevant prior knowledge |
| [`knowledge-ingest.md`](knowledge-ingest.md) | Turning evidence into durable knowledge |
| [`knowledge-lint.md`](knowledge-lint.md) | Reviewing knowledge-artifact quality |
| [`run-retro.md`](run-retro.md) | Finding patterns that repeat across many sessions |
| [`knowledge-curator.md`](knowledge-curator.md) | Ranking what in the knowledge base needs maintenance |

The two loops these implement: the inner one runs inside a session
(prepare, execute, close out, Knowledge Delta); the outer one runs across
many of them (`run-retro.md`) and asks what repeats. A pattern is only
promotable evidence once the outer loop has seen it more than once.

This is the minimum coherent set (D-006), genericized from the private
production instance's ~24 playbooks with private repo names, examples,
and instance-specific tooling removed - see each file's own
`Knowledge source` comment for what was kept, dropped, and why. Not
ported: parallel-session coordination, customer-facing playbooks
(customer intake, engagement workflow), and the private instance's
scripted signal collectors - the curator here is a procedure an agent
follows, not automation, because no equivalent scripts exist publicly;
see [`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#session-lifecycle)
for the concepts every playbook here implements.
