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
An executing agent reads this file as the source of truth for one
session - not the packet's other files directly, and not chat history.

```yaml
---
id: SESSION-<NNN>
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-<NNN>-<slug>.md
session_context: .session-context/<session-id>.md
depends_on: []
---
```

## Goal

<1-3 sentences, copied/refined from this session's roadmap entry.>

## Required reading order

1. Packet files, in numeric order, up through the roadmap.
2. This project instance's persistent agent-instruction file and any
   directly relevant `knowledge/` artifacts.
3. Anything the prior session's checkpoint flagged as relevant.

## Experience retrieval preflight

<Search `knowledge/` (`scripts/eif_search_knowledge.py "<query>"`) for
anything relevant before implementing. Record what was found, or that
nothing relevant was found - do not skip this because the session looks
routine.>

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

## Exit criteria

- [ ]
- [ ]

## Closeout / Knowledge Delta

<What this session should record before the next one starts: new facts,
rules, or lessons - and an explicit note if it taught nothing durable.>
