---
type: ontology
status: validated
scope: framework
---

# Authority model

The hierarchy of truth sources - what wins when they conflict.

## Hierarchy

```text
1. Vendor documentation (the library/API/service's official docs)
      |  outranks
2. Verified code (real, audited code - not an inferred or assumed name)
      |  outranks
3. Validated knowledge assets (facts, ADRs with status: validated)
      |  outranks
4. Customer/stakeholder-confirmed behavior
      |  outranks
5. Agreed scope documents (charter, acceptance scope)
      |  outranks
6. Chat memory / AI inference
      |  outranks (weakest)
7. Explicitly labeled assumptions
```

## Application rules

### Logs vs. vendor docs
**Vendor docs win.** A log describes what is currently happening; docs
describe what is supposed to happen.

### A planning brief vs. verified facts
**Verified facts win.** A brief may use logical/informal names; a facts
artifact should carry wire names taken from an actual code audit.

### Persistent agent instructions vs. ad-hoc chat instructions
**Persistent instructions win.** Chat-scoped instructions may be temporary;
a versioned instruction file is a durable contract.

### An older decision record vs. new evidence
**New evidence wins**, if it is validated. Update the old decision record's
status to `superseded` and create a new one - do not silently overwrite it.

### Code vs. docs disagreement
- **Code wins** if the disagreement reflects real runtime behavior.
- **Docs win** if the code has a bug the docs correctly describe.
- Either way, record the discrepancy as a finding - don't just pick a side
  and move on.

## Confidence levels

| Level | Description | What raises it |
|---|---|---|
| `low` | Assumption or unverified inference | A test or vendor-doc confirmation |
| `medium` | Observed once, not independently cross-verified | A second, independent source |
| `high` | Tested, or validated against both vendor docs and code | - |

See [`confidence-levels.md`](confidence-levels.md) for the full rubric and
[`knowledge-types.md`](knowledge-types.md) for how this maps onto knowledge
artifact types.
