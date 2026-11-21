---
name: knowledge-search
description: >
  Search existing project knowledge before non-trivial work, so a
  plausible-looking approach doesn't repeat a mistake a prior session
  already found and recorded. Use as a preflight before implementing,
  or while planning, to find relevant prior lessons/incidents.
---

# Skill: Knowledge Search

<!-- Knowledge source: GENERALIZE, built from this framework's own
Experience Retrieval design - see playbooks/knowledge-search.md, the
canonical source this skill is a thin pointer to. -->

Full workflow: [`playbooks/knowledge-search.md`](../../playbooks/knowledge-search.md).

## Process

1. Resolve the project's retrieval route in the playbook. For managed
   knowledge use the EIF reader or CLI. For external knowledge use the
   project's own retrieval policy.
2. Check coverage before concluding that nothing relevant was found.
3. Record the query and result, including source, coverage and effect on
   the plan, in the existing preflight. On resume, recheck changed sources.
4. If a relevant `rejected` or `superseded` artifact turns up, read why
   before proceeding with a similar approach.

## Output

- The search result, with the coverage actually available.
- How it changes the current plan, or `n/a`.
