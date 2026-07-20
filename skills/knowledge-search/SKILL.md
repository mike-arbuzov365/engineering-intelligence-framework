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

1. Run `python scripts/eif_search_knowledge.py "<query>"`.
2. If the index looks stale or missing, rebuild it first:
   `python scripts/eif_generate_index.py` (reports malformed/invalid
   artifacts as distinct categories, never silently as "no results").
3. Record the query and result - what was found (artifact path), or that
   nothing relevant was found - in whatever preflight section triggered
   the search.
4. If a relevant `rejected` or `superseded` artifact turns up, read why
   before proceeding with a similar approach.

## Output

- The search result (found artifact(s), or confirmed nothing relevant).
- How it changes the current plan, or `n/a`.
