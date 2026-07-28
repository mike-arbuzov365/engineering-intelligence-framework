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
expect. Not yet ported: customer-facing skills. Knowledge health is covered
by the curator; community skill discovery remains a separate future
trust-boundary workflow rather than an automatic installer.
