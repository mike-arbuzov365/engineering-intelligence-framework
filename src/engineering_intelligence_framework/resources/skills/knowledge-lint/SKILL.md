---
name: knowledge-lint
description: >
  Manually review knowledge-artifact quality before proposing promotion
  beyond this project instance, or after a significant packet closeout.
  Checks source/evidence discipline, type correctness, status/confidence,
  duplication, links, and privacy.
---

# Skill: Knowledge Lint

<!-- Knowledge source: GENERALIZE of the private EI's knowledge-lint
SKILL.md. Thin pointer to playbooks/knowledge-lint.md - one canonical
source per D-007. -->

Full workflow: [`playbooks/knowledge-lint.md`](../../playbooks/knowledge-lint.md).

## Process

Run the checklist in the playbook above: source/evidence, type
discipline, status/confidence, location/duplication, links/indexes,
privacy (`scripts/eif_privacy_scan.py`), and session/packet closeout
hygiene. Classify every finding `BLOCKER` / `MAJOR` / `MINOR`.

## Output

```markdown
Status: PASS | PASS_WITH_NOTES | FAIL

Findings:
- [BLOCKER|MAJOR|MINOR] <file>: <issue> -> <recommended fix>

Verified: <what was actually checked>
Deferred: <what wasn't, and why>
```
