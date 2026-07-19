# Template: Execution Packet Roadmap

<!-- Knowledge source: GENERALIZE of the private EI's
execution-packet-planning.md roadmap section. Kept: one session = one
file with its own goal/scope/verification/exit-criteria, strict
numeric/sequential ordering, concrete (not "run the tests") verification
commands. Dropped: parallel-session-group and cross-worktree coordination
detail - re-add only if a project instance actually runs more than one
session of the same packet concurrently; a v0.1 single-agent, sequential
packet does not need it. -->

One file per packet: `<packet-root>/04-ROADMAP-<NNN>-<slug>.md`. Turns
`02-FACTS`' gaps into an ordered list of sessions. Each session below
should also get its own launch file under `<packet-root>/sessions/` (see
[`templates/session-launch.md`](session-launch.md)) once this roadmap is
ratified.

```yaml
---
packet: <packet-id>
type: roadmap
status: prepared
execution: single-agent-sequential
---
```

## Global execution constraints

<Anything that applies to every session below: which branch/worktree
convention, "local commits only until the final session" if that's the
policy, any resource budget guard (e.g. avoid triggering paid/hosted CI
until a stated condition holds).>

## Session `<NNN>` - `<short title>`

1. `<concrete step>`
2. `<concrete step>`

Verification:

```text
<runnable command>
<runnable command>
```

Exit: `<the observable state that means this session is actually done -
not "implemented X" but "X passes this specific check">`

<Repeat one `## Session <NNN>` block per session, in the exact order they
must execute. A later session may declare `depends_on` an earlier one in
its own launch file; the roadmap's ordering is the authority for what
"earlier" means.>

## Definition-of-done cross-check

<Confirm every item in `01-CHARTER`'s Definition of Done maps to at least
one session above. An item with no session is either out of scope after
all (say so, update the charter) or a missing session (add one) - it
should never be silently unaddressed.>
