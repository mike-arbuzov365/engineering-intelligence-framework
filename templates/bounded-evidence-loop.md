# Template: Bounded Evidence Loop Contract

<!-- Knowledge source: EIF Bounded Evidence Loop research and playbook,
2026-07-21. -->

Use this block inside a task-scope or session-launch artifact. Keep it small
enough to guide execution, but precise enough to decide when to stop.

```yaml
loop:
  goal: "<one observable outcome>"
  success_evidence:
    - "<behavioral evidence required for PASS>"
  evaluator:
    kind: "test | tool | source-comparison | rubric | human"
    command_or_reference: "<exact command, file, rubric, or owner gate>"
  max_iterations: 5
  remote_run_budget: 0
  time_budget_minutes: "<integer or not-set>"
  stop_conditions:
    - "<security/data-loss/public-commitment/ambiguity boundary>"
  checkpoint: ".session-context/<session-id>.md"
```

## Iteration record

```yaml
iteration: <number>
state: "ORIENT | DEFINE | ACT | OBSERVE | STUDY | ADAPT"
hypothesis: "<what this iteration tests>"
expected_observation: "<what should happen>"
actual_observation: "<what the evaluator showed>"
failure_signature: "<stable short label or none>"
evidence_refs:
  - "<command/result/file/trace>"
adaptation: "<what changes before the next attempt or none>"
next_action: "<smallest next action>"
budget_remaining:
  iterations: <number>
  remote_runs: <number>
```

## Closeout record

```yaml
loop_result:
  status: "PASS | BLOCKED | DEFERRED"
  iterations_used: <number>
  remote_runs_used: <number>
  success_evidence:
    - "<actual evidence or none>"
  failure_signatures:
    - "<signature or none>"
  durable_learning: "<Knowledge Delta reference or none>"
  residual_risk: "<risk or none>"
```

The checkpoint lives in the session layer: gitignored, factual, and deleted at closeout. Never
persist raw chain-of-thought or use a completion phrase as success evidence.
