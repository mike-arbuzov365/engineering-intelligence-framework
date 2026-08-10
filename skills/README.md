# skills/

Slash-command-style skills for AI coding agents.

| Skill | Playbook it wraps |
|---|---|
| [`create-professional-profile/`](create-professional-profile/SKILL.md) | `playbooks/professional-profile-creation.md` |
| [`plan-idea/`](plan-idea/SKILL.md) | `playbooks/idea-planning.md` |
| [`plan-prd/`](plan-prd/SKILL.md) | `playbooks/product-requirements-planning.md` |
| [`run-bounded-evidence-loop/`](run-bounded-evidence-loop/SKILL.md) | `playbooks/bounded-evidence-loop.md` |
| [`plan-execution-packet/`](plan-execution-packet/SKILL.md) | `playbooks/execution-packet-planning.md` |
| [`run-execution-packet/`](run-execution-packet/SKILL.md) | `playbooks/execution-packet-execution.md` |
| [`review-execution-packet/`](review-execution-packet/SKILL.md) | `playbooks/execution-packet-review.md` |
| [`knowledge-search/`](knowledge-search/SKILL.md) | `playbooks/knowledge-search.md` |
| [`knowledge-ingest/`](knowledge-ingest/SKILL.md) | `playbooks/knowledge-ingest.md` |
| [`knowledge-lint/`](knowledge-lint/SKILL.md) | `playbooks/knowledge-lint.md` |
| [`run-retro/`](run-retro/SKILL.md) | `playbooks/run-retro.md` |
| [`knowledge-curator/`](knowledge-curator/SKILL.md) | `playbooks/knowledge-curator.md` |

Each skill is a thin `<skill-name>/SKILL.md` pointer to its playbook (one
canonical source per D-007, not a second copy of the workflow) with the
native `name`/`description` skill-manifest frontmatter agent adapters
expect.

## Local tested contract

Кожен із 12 core skills має compact `tests/contract.yaml` поруч із
`SKILL.md`. Три skills у bundled starter profiles мають той самий contract.
Fixture зберігає positive і negative trigger examples, canonical references,
required evidence/commands, stop conditions, forbidden behavior,
deterministic assertions, supporting-file declarations і provenance.
Canonical workflow prose лишається у playbook, а fixture не копіює його.

Model-free check:

```bash
eifctl skills check
```

Command validates frontmatter, JSON Schema, path containment, references,
script digests/declarations, trigger separation, grounded assertions і
duplicate canonical prose. Він не виконує supporting scripts, не запускає
model calls і не встановлює external content. Behavioral eval є окремим,
owner-budgeted surface лише для material semantic change.

EIF-021 representative pilot має complete deterministic dry-run, але
behavioral result `DEFERRED`: hard zero-cost boundary не підтверджено й model
runs дорівнюють `0`. Див.
[`docs/benchmarks/skill-eval/`](../docs/benchmarks/skill-eval/). Static PASS не
є quality, trigger-precision, token або time improvement evidence.

Supporting `tests/`, `scripts/`, `references/` та `evals/` materialize разом
із canonical skill directory. Generated adapter loader лишається compact і
вказує лише на selected `SKILL.md`; fixtures не входять у normal model
context. Policy для future external candidates описано в
[`docs/reference/external-skill-admission.md`](../docs/reference/external-skill-admission.md).

## Reaching the agent

`eif_init.py` copies this directory into a project's
`.eif/runtime/skills/`. That is where the pinned copies live; it is **not**
where any agent looks for them. Each adapter reads its own location
(`.claude/skills/`, `.agents/skills/`, and so on, per
[`adapters/README.md`](../adapters/README.md)).

`scripts/eif_sync_skills.py` generates the loaders that connect the two.
`eifctl init`/`upgrade` runs it automatically for the selected adapter, and a
workspace fleet apply runs it again after profile materialization so a
profile-selected professional skill is visible in the next agent session.
`eifctl doctor` fails if a selected skill is missing or points at a stale
source.

The standalone command remains the repair/check surface:

```bash
python .eif/runtime/eif_sync_skills.py --instance-path . --adapter claude-code
python .eif/runtime/eif_sync_skills.py --instance-path . --adapter claude-code --check
```

Before 0.2.5 nothing did this, so an adopting project received every skill
and could invoke none of them unless someone hand-wrote a loader per skill.
The failure was silent: a missing skill produces no error, the agent simply
never learns the workflow exists. Found in a real adoption where one of
eleven loaders had been written by hand, and the absence of
`run-execution-packet`, `run-retro` and `knowledge-ingest` showed up months
later as "this project never ran retros" rather than as a defect.

A project-owned `skills/<name>/SKILL.md` wins over a pinned workspace skill,
which wins over the public EIF runtime skill. The loader points to the winner;
it does not copy the body. A loader without the generated marker is never
overwritten, so adapter-specific hand-authored overrides survive upgrades.
Not yet ported: customer-facing skills. Knowledge health is covered
by the curator; community skill discovery remains a separate future
trust-boundary workflow rather than an automatic installer.
