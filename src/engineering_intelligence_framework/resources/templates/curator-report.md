# Template: Curator Report

<!-- Knowledge source: GENERALIZE of the private EI's curator report v2
format. Kept: the ledger diff sections, the signal-coverage table, the
required per-finding fields and the self-check. Dropped: that instance's
HTML dashboard parity section and its cross-repo workspace hygiene section,
neither of which has an equivalent here. -->

Output of [`playbooks/knowledge-curator.md`](../playbooks/knowledge-curator.md).

The ledger diff is the part that makes this more than a lint run: it
distinguishes a new problem from the fourth occurrence of an old one.

---

```markdown
# Curator report: <date>

Scope: <what was scanned>
Repository state: clean | dirty | onboarding | not-scanned
Mode: read-only | fixes-proposed

## Ledger diff

### New
<!-- No existing finding ID. -->

### Recurring
<!-- Same ID, or same class and path. Include the occurrence count -
three or more open occurrences escalates severity and needs a prevention
proposal, not another fix. -->

### Closed since last run
<!-- Each with its verification evidence. A finding closed without
evidence is not closed. -->

### Suppressed
<!-- Rationale, expiry, who accepted it. Excluded from the backlog,
still recorded. -->

### Regressed
<!-- Was resolved, observed again. Explain the prevention gap. -->

## Summary

| Severity | Count |  | Routing | Count |
|---|---|---|---|---|
| BLOCKER |  |  | fix-now |  |
| MAJOR |  |  | defer-to-packet |  |
| MINOR |  |  | promote |  |
|  |  |  | retro-inbox |  |
|  |  |  | intentional-divergence |  |
|  |  |  | do-not-touch |  |

## Signal coverage

<!-- Every class gets a status, so a silent gap is visible. Use
"not-applicable (reason)" or "not-scanned (reason)" rather than omitting
a row - an absent row is indistinguishable from a clean one. -->

| Signal | Source | Status |
|---|---|---|
| Broken links | eif_check_links.py | clean / findings: N / not-scanned (reason) |
| Orphans, no incoming links | knowledge index |  |
| Freshness, review_after passed | artifact frontmatter |  |
| Schema-invalid artifacts | eif_validate_frontmatter.py |  |
| Privacy and suppression hygiene | eif_privacy_scan.py |  |
| Missing provenance comment | artifact source |  |
| Deferred items with no owner path | closeouts |  |
| Optional integration health | eifctl doctor |  |

## Findings

<!-- Every finding needs all of these. A finding missing its evidence
label or its owner path is not actionable and should not be counted. -->

### <FINDING-ID> - <one-line summary>

- Severity: BLOCKER | MAJOR | MINOR
- Routing: <one of the six canonical tokens>
- Fix class: A | B | C
- Path or owner: <where this lives>
- Evidence: OBSERVED | INFERRED | ASSUMED - <what was actually seen>
- Occurrences: <n> (first seen <date>)
- Recommended action: <specific, not "review this">
- Ledger action: open | update | close | suppress

## Self-check

- [ ] Every routing value is one of the six canonical tokens.
- [ ] Routing counts sum to the number of active findings.
- [ ] Every finding has severity, routing, fix class, path, evidence and
      a recommended action.
- [ ] No finding is marked resolved without verification evidence.
- [ ] No Class A fix touches a guarded path (`core/ontology/`,
      `core/policies/`, any `SKILL.md`, `.github/workflows/`, or anything
      outside this instance).
- [ ] Nothing was merged by this run.

## Recommended next actions
```

---

## If the run found nothing

A clean run is a real result and worth recording, but state what was
actually checked - an empty report is indistinguishable from a run that
silently failed to collect anything:

```markdown
## Findings

None. Signal coverage above shows <N> classes checked, <M> not applicable.
Ledger unchanged: <k> findings remain suppressed, none regressed.
```
