---
type: playbook
status: validated
scope: framework
confidence: high
created: 2026-07-21
related:
  - session-execution.md
  - session-closeout.md
  - ../templates/bounded-evidence-loop.md
  - ../docs/research/bounded-evidence-loops.md
---

# Playbook: Bounded Evidence Loop

<!-- Knowledge source: SYNTHESIZE of PDSA, ReAct, Reflexion,
evaluator-optimizer, agent-eval, and bounded Ralph-style loop patterns;
research digest and primary sources in docs/research/bounded-evidence-loops.md. -->

Use this playbook when a task benefits from iterative action and feedback.
It makes the feedback loop explicit, bounded, evidence-driven, and resumable.

## Preconditions

Do not start a loop until all of these are known:

- `goal` - one observable outcome;
- `success_evidence` - what proves the outcome behaviorally;
- `evaluator` - test, tool, source comparison, rubric, or named human decision;
- `max_iterations` - a positive integer, default 5 if no narrower limit exists;
- `remote_run_budget` - default 0 unless explicitly authorized;
- `stop_conditions` - safety, ambiguity, budget, or owner-only boundaries;
- `checkpoint` - a gitignored Tier 3 path if interruption is possible.

Fill [`templates/bounded-evidence-loop.md`](../templates/bounded-evidence-loop.md)
or include its fields in a task-scope/session-launch artifact.

## One iteration

1. **ORIENT** - read current source and relevant retrieved knowledge. Record
   facts separately from assumptions.
2. **DEFINE** - state the next smallest hypothesis and the observation that
   would confirm or reject it.
3. **ACT** - make one reversible change or run one diagnostic experiment.
4. **OBSERVE** - run the declared evaluator and record its actual output.
5. **STUDY** - compare expected and actual results. If not successful, record
   a concise `failure_signature` that can be compared across attempts.
6. **ADAPT** - select the next action because of the observation. Do not repeat
   an unchanged failing action with no new evidence.

## Loop control

- Stop `PASS` only when `success_evidence` exists.
- Stop `BLOCKED` when a stop condition is reached, the evaluator is unavailable
  with no adequate substitute, the iteration budget is exhausted, or the same
  unchanged failure signature would be attempted a third time.
- Stop `DEFERRED` only when the remaining work is explicitly owner-gated or
  outside the ratified scope; name the destination artifact or decision.
- Changing instrumentation, the hypothesis, or the method is a real adaptation.
  Rewording the same prompt is not necessarily one.
- A completion phrase, file existence, build result, merge, or self-review alone
  never satisfies a behavioral success condition.
- A remote run consumes budget even if it fails before tests start. Do not use
  hosted CI as an iterative debugger when a local check is available.

## Checkpoint format

Record only compact state:

```yaml
iteration: 2
state: STUDY
expected_observation: "focused regression test passes"
actual_observation: "test fails at case invalid-empty-value"
failure_signature: "validation-empty-value"
evidence_refs:
  - "local test command and result"
decision: "add input-boundary instrumentation before changing behavior"
next_action: "run the focused test with boundary logging"
budget_remaining:
  iterations: 3
  remote_runs: 0
```

Do not store raw chain-of-thought. The checkpoint is gitignored and deleted at
closeout after validated learning is routed through Knowledge Delta.

## Nested loops

- **Micro loop** - one implementation or diagnostic change.
- **Session loop** - exit criteria across several micro loops.
- **Packet loop** - sequential sessions with packet-level Definition of Done.
- **Learning loop** - validated recurring patterns promoted through Knowledge
  Delta and retrieved before the next similar task.

Each outer level consumes evidence from the inner level; it must not replace
that evidence with a summary assertion.

## Closeout

Record iteration count, final status, success evidence, failure signatures,
budget used, adaptations made, and residual risk. Promote only validated,
reusable learning. Delete the Tier 3 checkpoint.
