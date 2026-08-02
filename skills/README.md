# skills/

Slash-command-style skills for AI coding agents.

| Skill | Playbook it wraps |
|---|---|
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

## Reaching the agent

`eif_init.py` copies this directory into a project's
`.eif/runtime/skills/`. That is where the pinned copies live; it is **not**
where any agent looks for them. Each adapter reads its own location
(`.claude/skills/`, `.agents/skills/`, and so on, per
[`adapters/README.md`](../adapters/README.md)).

`scripts/eif_sync_skills.py` generates the loaders that connect the two:

```bash
python scripts/eif_sync_skills.py --instance-path . --adapter claude-code
python scripts/eif_sync_skills.py --instance-path . --adapter claude-code --check
```

Before 0.2.5 nothing did this, so an adopting project received every skill
and could invoke none of them unless someone hand-wrote a loader per skill.
The failure was silent: a missing skill produces no error, the agent simply
never learns the workflow exists. Found in a real adoption where one of
eleven loaders had been written by hand, and the absence of
`run-execution-packet`, `run-retro` and `knowledge-ingest` showed up months
later as "this project never ran retros" rather than as a defect.

A project-owned skill of the same name always wins, and a loader without the
generated marker is never overwritten, so overrides survive upgrades. Not yet ported: customer-facing skills. Knowledge health is covered
by the curator; community skill discovery remains a separate future
trust-boundary workflow rather than an automatic installer.
