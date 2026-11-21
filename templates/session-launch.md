# Template: Session Launch File

<!-- Knowledge source: SPLIT of the private EI's session-launch-template.md
- see templates/task-scope.md for the standalone-task half of that split.
This file is the other half: one session that belongs to a multi-session
execution packet's roadmap. Kept: required reading order, explicit
no-touch zone, concrete verification, boolean exit criteria,
`depends_on` sequencing. Dropped: worktree/branch/parallel-group
bookkeeping beyond a single `depends_on` list - re-add only if a project
instance runs more than one concurrent session against the same packet;
strict single-agent sequential execution (this framework's default) does
not need it. -->

One file per packet session: `<packet-root>/sessions/SESSION-<NNN>-<slug>.md`.
The canonical progress statuses are `prepared`, `in_progress`, `completed`,
`blocked`, and `deferred`. Update status when starting and closing a session.
Other historical values are `legacy` to progress readers and do not prove
completion. A next session requires every `depends_on` entry to be `completed`.
An executing agent reads this file as the source of truth for one
session - not the packet's other files directly, and not chat history.

```yaml
---
id: SESSION-<NNN>
logical_session: SESSION-<NNN>
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-<NNN>-<slug>.md
session_context: .session-context/<session-id>.md
continuation_mode: same_chat | new_chat | auto
depends_on: []
---
```

## Goal

<1-3 sentences, copied/refined from this session's roadmap entry.>

## Required reading order

1. Packet files, in numeric order, up through the roadmap.
2. The project's persistent agent instructions and any directly relevant
   artifacts from its configured knowledge source.
3. Anything the prior session's checkpoint flagged as relevant.

The logical session may span multiple sequential physical chats. The selected
`continuation_mode` does not change scope, approval or dependency state. Before
handoff or manual compaction, update and validate `session_context`; native chat
summaries are not authority.

## Experience retrieval preflight

<Use the knowledge-search playbook and the project's configured source for
anything relevant before implementing. Record the query, source path or
identifier, revision or date when available, coverage and effect on the plan.
Record the observed limit if the source cannot be searched.>

## Scope

<What this specific session must accomplish. Should map to exactly the
slice this session owns in the roadmap - not more.>

## Out of scope / do not touch

<Explicit no-touch zone for this session - files/directories owned by a
different session, or out of the packet entirely.>

## Verification

```text
<runnable command>
<runnable command>
```

## Bounded loop contract

For iterative work, copy the compact contract from
[`templates/bounded-evidence-loop.md`](bounded-evidence-loop.md) and fill:

- observable `success_evidence`;
- the evaluator command/reference;
- `max_iterations` (default 5 only when the packet sets no narrower limit);
- `remote_run_budget` (default 0 unless explicitly authorized);
- stop conditions and the gitignored checkpoint path.

For a one-action session, write `not needed - <reason>`.

## Exit criteria

- [ ]
- [ ]

## Closeout / Knowledge Delta

<What this session should record before the next one starts: new facts,
rules, or lessons - and an explicit note if it taught nothing durable.>
