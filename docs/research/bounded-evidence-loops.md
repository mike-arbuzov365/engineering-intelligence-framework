# Bounded Evidence Loops for Agentic Engineering

<!-- Knowledge source: primary-source research completed 2026-07-21 and
reconciled 2026-07-23: Deming Institute PDSA; Argyris double-loop learning;
IBM autonomic-computing MAPE-K; NIST AI RMF; Yao et al. ReAct
(arXiv:2210.03629); Shinn et al. Reflexion (arXiv:2303.11366); Anthropic
Building Effective AI Agents; Anthropic Demystifying Evals for AI Agents;
Anthropic Ralph Wiggum plugin. -->

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
| PDSA | Plan, execute, study the result, and use the learning to adapt the next cycle; "Study" tests the theory rather than merely checking a pass/fail box | Every iteration declares an expected observation, then compares it with actual evidence before adapting |
| Double-loop learning | Correct an action in the first loop; question a governing assumption, objective, policy, or evaluator when the evidence shows the frame itself is wrong | EIF distinguishes an implementation fix from an explicit evaluator/rule change; the latter needs evidence, a recorded decision, and a new validation run |
| MAPE-K | Monitor, analyze, plan, and execute around a shared knowledge base | EIF separates the operating loop from durable knowledge: observations stay in the session layer until validation promotes them to the project or framework layer |
| NIST AI RMF | Iterative Govern, Map, Measure, and Manage functions connect feedback, measurement, accountability, and risk response | Every autonomous loop has policy boundaries, measurement evidence, explicit risk/stop conditions, and owner-only gates |
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

## Single-loop and double-loop changes

A normal iteration is single-loop: the goal, policy and evaluator stay fixed
while the implementation or experiment changes.

A double-loop change is justified only when evidence shows that the governing
frame is defective. Examples include a test that encodes the wrong contract,
a stale authority rule, or a budget policy that measures the wrong unit. The
agent must:

1. preserve the failed observation;
2. name the assumption, rule or evaluator being challenged;
3. record the evidence and authority for changing it;
4. update the governing artifact separately from the implementation fix;
5. rerun a behavioral evaluator against the revised contract.

This prevents two opposite errors: endlessly changing code to satisfy a broken
evaluator, and weakening the evaluator merely to obtain a green result.

## What the knowledge base means

MAPE-K is useful here as an architectural analogy, not as a claim that EIF is
an autonomic runtime. EIF's "K" is external and inspectable:

- The session layer holds temporary observations and hypotheses for the active session;
- The project layer holds validated project facts, decisions, incidents and experience;
- The framework layer holds reusable cross-project rules, playbooks, templates and skills.

Promotion between layers is gated by validation and provenance. No model
weights are changed, and no provider is allowed to silently learn from or
publish the stored artifacts.

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
- Checkpoints live in the session layer: gitignored, factual, compact, and removed at closeout.
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
- [Chris Argyris: Double Loop Learning in Organizations](https://hbr.org/1977/09/double-loop-learning-in-organizations)
- [IBM Research: MAPE-K functional process model](https://research.ibm.com/publications/automated-management-and-service-provisioning-model-for-distributed-devices)
- [NIST AI RMF Core: Govern, Map, Measure, Manage](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [Yao et al.: ReAct](https://arxiv.org/abs/2210.03629)
- [Shinn et al.: Reflexion](https://arxiv.org/abs/2303.11366)
- [Anthropic: Building Effective AI Agents](https://www.anthropic.com/engineering/building-effective-agents)
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Anthropic: Ralph Wiggum plugin](https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md)

## Research limitations

These sources support the design pattern, not EIF-specific outcome claims.
ReAct and Reflexion are research results under their own task settings;
Ralph is a provider-specific automation pattern; PDSA and double-loop learning
are general organizational-learning models; MAPE-K describes autonomic system
management; NIST AI RMF is a voluntary risk-management framework. EIF adapts
selected controls without claiming equivalence to any source method or
evidence of better engineering outcomes. Comparative evaluation on real tasks
is still required.
