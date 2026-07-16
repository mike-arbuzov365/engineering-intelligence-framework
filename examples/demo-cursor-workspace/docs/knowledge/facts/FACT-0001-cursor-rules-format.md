---
type: fact
status: validated
scope: project
evidence: OBSERVED
source: official_specification
confidence: high
created: 2026-07-16
review_after: 2027-07-16
---

# Cursor project-rule format

Cursor's current, official project-rule format is `.cursor/rules/*.mdc`:
YAML frontmatter (`description`/`globs`/`alwaysApply`) followed by markdown
content. The legacy `.cursorrules` file is deprecated.
