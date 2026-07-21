# Bounded Evidence Loops for Agentic Engineering

<!-- Knowledge source: primary-source research completed 2026-07-21:
Deming Institute PDSA; Yao et al. ReAct (arXiv:2210.03629); Shinn et al.
Reflexion (arXiv:2303.11366); Anthropic Building Effective AI Agents;
Anthropic Demystifying Evals for AI Agents; Anthropic Ralph Wiggum plugin. -->

**Status:** researched design adopted into EIF's operating layer. This is a
methodology contract, not evidence that EIF improves task quality. Comparative
quality and rework claims remain unverified in
[`docs/product/claims-evidence.md`](../product/claims-evidence.md).

## Research question

How should EIF support iterative agent work without creating an infinite retry
loop, treating a completion phrase as proof, persisting raw model reasoning, or
spending an unbounded CI/API budget?

## What the source methods contribute

| Source method | Useful contribution | EIF adaptation |
|---|---|---|
| PDSA | Plan, execute, study the result, and use the learning to adapt the next cycle | Every iteration declares an expected observation, then compares it with actual evidence before adapting |
| ReAct | Interleave action with observations from tools or an environment | A tool result, test, source file, or runtime trace grounds each plan update |
| Reflexion | Use feedback from a failed attempt to improve the next attempt | Persist only a compact failure signature, verified facts, decision, and next experiment - never raw chain-of-thought |
| Evaluator-optimizer | Iterate when success criteria are clear and evaluation gives actionable feedback | A loop is allowed only when it has an observable success contract and a real evaluator |
| Ralph-style repeated prompting | Persistent file state, small goals, tests, and a maximum iteration count can keep long-running work moving | EIF adopts bounded repetition and file-backed checkpoints, but not an infinite stop-hook loop or a completion string as evidence |
| Agent evals | Define success and graders explicitly; use code, model, and human graders where appropriate | Each loop names its evidence source and evaluator before execution |

## The EIF synthesis: Bounded Evidence Loop

EIF uses one small state machine for a change, a session, or an execution
packet:

```text
ORIENT -> DEFINE -> ACT -> OBSERVE -> STUDY -> ADAPT
              ^                         |        |
              |                         |        +-> next bounded iteration
              |                         +-> PASS / BLOCKED / DEFERRED
              +------------------------------- changed plan
```

1. **Orient** - retrieve relevant authority, prior knowledge, current source,
   and starting-state evidence.
2. **Define** - write the observable success condition, evaluator, evidence,
   iteration limit, cost/time/remote-run budget, and stop conditions.
3. **Act** - make the smallest reversible change or run the smallest useful
   experiment.
4. **Observe** - capture external evidence. The agent's statement that it is
   done is not evidence.
5. **Study** - compare expected and actual observations; assign a stable
   `failure_signature` when the result is not the expected one.
6. **Adapt** - change the hypothesis, plan, instrumentation, or scope before
   the next iteration. Repeating the same failing action without new evidence
   is prohibited.
7. **Close** - finish as `PASS`, `BLOCKED`, or `DEFERRED`, with the evidence
   and residual risk recorded.

The reusable contract is in
[`templates/bounded-evidence-loop.md`](../../templates/bounded-evidence-loop.md)
and the procedure is in
[`playbooks/bounded-evidence-loop.md`](../../playbooks/bounded-evidence-loop.md).

## Safety and budget rules

- Autonomous loops require a positive `max_iterations`. If a project or
  packet does not set one, EIF's default is 5.
- Hosted CI, paid APIs, deployment, publication, and other remote mutations
  have a default budget of 0 unless the task or packet explicitly authorizes
  them. A local equivalent is preferred when it answers the same question.
- The same unchanged failure signature may recur once. Before a third attempt,
  the method or instrumentation must change; if it cannot, close `BLOCKED`.
- A file existing, a build completing, a PR merging, or a model emitting a
  completion token is not sufficient behavioral evidence.
- Human judgment remains the evaluator for ambiguous product taste, public
  commitments, security exceptions, and irreversible decisions.
- Checkpoints are Tier 3: gitignored, factual, compact, and removed at closeout.
  Durable promotion happens through Knowledge Delta.
- Never store hidden chain-of-thought or a verbatim reflection trace. Store
  observations, a short reasoning digest, decisions, and evidence references.

## Where loops help and where they do not

Good fits:

- test-driven bug fixing with a deterministic test;
- document refinement against an explicit rubric;
- local lint/schema/privacy repair;
- a packet session with boolean exit criteria;
- recovery where each attempt can add diagnostic evidence.

Bad fits:

- an unclear goal with no observable evaluator;
- production debugging where repeated mutation can increase harm;
- owner-only publication, payment, visibility, or destructive actions;
- repeatedly triggering remote CI to discover errors that local checks expose;
- open-ended content polishing with no stopping rule.

## Primary sources

- [Deming Institute: PDSA Cycle](https://deming.org/explore/pdsa/)
- [Yao et al.: ReAct](https://arxiv.org/abs/2210.03629)
- [Shinn et al.: Reflexion](https://arxiv.org/abs/2303.11366)
- [Anthropic: Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Anthropic: Ralph Wiggum plugin](https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md)

## Research limitations

These sources support the design pattern, not EIF-specific outcome claims.
ReAct and Reflexion are research results under their own task settings;
Ralph is a provider-specific automation pattern; PDSA is a general learning
cycle. EIF's synthesis still needs repeated comparative evaluation on real
engineering tasks. The next integration packet therefore measures loop count,
failure-signature changes, task success, rework, and token/tool cost together.
