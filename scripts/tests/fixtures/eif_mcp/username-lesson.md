---
type: fact
status: validated
scope: project
evidence: OBSERVED
source: test
created: 2026-11-21
---

# Username normalization after the K17 attempt

In synthetic regression K17 an attempted normalizer used `raw.replace(" ", "")`.
The multi-word-name test showed that this drops internal spaces from the
username. The accepted approach is trimming both ends with `strip()` while
retaining internal spaces. Rerun the multi-word-name case before closing a
username whitespace change.
