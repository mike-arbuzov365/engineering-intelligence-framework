---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-19
related:
  - session-execution.md
  - execution-packet-planning.md
  - ../templates/task-scope.md
---

# Playbook: Session Preparation

<!-- Knowledge source: GENERALIZE of the private EI's
session-preparation.md. Kept: the task-vs-packet routing checkpoint, the
scope questions, the handoff-prompt pattern. Dropped: worktree/parallel-
session bookkeeping (see templates/task-scope.md and
templates/session-launch.md for what's kept vs. dropped and why at the
template level). -->

Decide how much planning a piece of work actually needs, and produce the
artifact that lets execution start from that artifact instead of from
chat history.

## When to use this

- A light task (one bounded action, clear requirements and approval, low risk,
  obvious result check): skip preparation and persistent planning files. Use
  the relevant profile skill, retrieve only relevant project knowledge, check
  the result and perform a learning check.
- A structured single task: fill
  [`templates/task-scope.md`](../templates/task-scope.md), then use
  [`session-execution.md`](session-execution.md).
- Work that spans multiple sessions, has real architectural decisions to
  make first, has unresolved factual conflicts, or should run
  autonomously without routine questions: this playbook, producing an
  execution packet.

## Step 1 - Classify the work

State the intended result and its check before changing anything. Choose
the smallest path that covers the consequences and dependencies.

| Route | Choose when | Work to prepare | Example |
|---|---|---|---|
| `light` | One authorized, low-risk action with a clear result and an obvious check | Work from the request. Retrieve relevant knowledge and verify the result | Correct one label and check that it appears |
| `structured` | One session needs written scope, decisions or several checks | Fill one [task scope](../templates/task-scope.md). Include iterative feedback only when the [Bounded Evidence Loop](bounded-evidence-loop.md) applies | Reproduce and fix a form regression, then check save and retry |
| `packet`, compact | Two or more dependent sessions with settled behavior and ordinary integration risk | Use the packet files. Keep each decision and its evidence short. Name what each session hands to the next | Update a validated data export, then apply it to a dependent report |
| `packet`, expanded | Architectural or cross-project decisions, unresolved factual conflicts, unattended work needing more controls, or material compatibility, migration or irreversible risk | Use the same packet files. Detail affected consumers, verification, recovery and owner decisions as applicable | Remove a public API field even if the code change is short |

An unattended request still uses a packet. Use the compact depth when the
sources, permissions and failure handling are already clear. Choose the
expanded depth when a consequential unknown needs resolving first.

Reuse approved requirements as the source for expected behavior. Add a data or
migration plan only when stored data or its contract changes. Put test commands
beside the relevant acceptance criteria when those commands describe enough.
Define affected clients and compatibility checks whenever a public contract
changes. Put clarification, implementation and verification in the same
session when one executor can deliver a result that can be accepted together.

When a defect is reported, reproduce it and find the source for the expected
behavior. For a clear regression, capture a failing check, fix the cause and
rerun the check. When a criterion is ambiguous or a product behavior is
missing, look for an approved source that settles it. Ask the owner for the
specific behavior only if the sources leave a consequential decision open.

### Choose who writes and checks tests

- Keep tests with implementation for routine checks and ordinary regressions.
- Use a short independent check when the implementation and its tests are
  ready but a consequential criterion benefits from a second reader.
- Give a separate author the acceptance tests before implementation when
  expected results can be derived from approved sources and a false pass
  would be costly. Require a failing case that reaches the intended assertion
  and a positive control that proves the evaluator works. Accept the
  expectations before implementation and review any later changes to them.

Keep reversible implementation choices with the executor. The owner decides
changes to the approved goal, ambiguous product behavior and external
commitments. Use the stronger available model where unclear requirements or
costly mistaken acceptance call for more judgment. Use a lighter available
model for bounded work with objective checks. Keep a separate session only
when its result changes a later decision or is needed by the next executor.

A light task does not require a checkpoint by default. Create one only if the
task must survive an interruption or planned handoff. Structured and packet
work declares its logical session and continuation mode in the prepared
artifact; the canonical semantics are in
[`HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#logical-sessions-physical-chats-and-continuation).

## Step 2 - If it needs a packet, build the packet anatomy

See [`execution-packet-planning.md`](execution-packet-planning.md) for the
full workflow. Use the chosen depth in the existing charter, facts, decisions,
roadmap, self-review and start files.

## Step 3 - Determine session order

If the packet has more than one session, decide their exact dependency
order before writing launch files - a later session's `depends_on` should
name the earlier one explicitly, not rely on "obviously B comes after A."

## Step 4 - Self-review before handoff

Checklist (also in [`templates/packet-self-review.md`](../templates/packet-self-review.md)
for packets; for a single task, re-read the task-scope file's own
sections once before starting):

- [ ] Goal and scope are unambiguous.
- [ ] No-touch zone is explicit.
- [ ] Verification commands are concrete, not "run the tests."
- [ ] Exit criteria are boolean.
- [ ] Sequential dependencies (if any) are explicit.

## Step 5 - Hand off

End preparation with a short prompt pointing at the artifact, not a
restatement of it in the prompt itself:

```text
Run the prepared task/session at:
<path to the task-scope file, or the packet's start file>

Use that file as the source of truth - do not rely on this chat as
hidden context. Work until its exit criteria are met.
```

## Anti-patterns

- The whole plan lives only in a chat prompt, never becomes a file - an
  execution session (possibly in a fresh context) can't see it.
- A worktree/branch convention left as "figure it out" - state it
  explicitly if the project instance uses one.
- Verification stated as "tests pass" instead of the actual command.
