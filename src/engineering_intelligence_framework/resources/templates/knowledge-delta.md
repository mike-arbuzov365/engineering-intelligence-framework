# Template: Knowledge Delta

<!-- Knowledge source: GENERALIZE of the private EI's
knowledge-delta-template.md - section structure, the "escape hatch" for
mechanical tasks, and the append-only rejected-hypothesis pattern are kept
unchanged. The private "Promote to [private companion repository]?" section
(private, multi-repo-specific) is replaced with a generic
"Promote to shared knowledge base?" question so it makes sense for any
project instance, not just the source private workspace. -->

Required output of every EIF session that changes code or decisions.
Goes into the PR description, or a standalone file referenced from it.

A locale-rendered version of this template's headings lives at
`locales/<locale>/templates/knowledge-delta.md`; this file is the
English-canonical source of truth for the section structure itself.

---

```markdown
## Knowledge Delta

### New facts
<!-- type: fact | confidence: high/medium/low | validated: yes/no -->
-

### New rules
<!-- type: rule | scope: global/local | applies to: where exactly -->
-

### New decisions / ADRs
<!-- Link to an ADR or a draft -->
-

### New risks
<!-- probability: H/M/L | impact: H/M/L | trigger: when it materializes -->
-

### New edge cases
<!-- Concrete scenario + how it's handled -->
-

### Rejected hypotheses
<!-- What was tried and why it didn't work - valuable for future sessions -->
-

### Deprecated / superseded guidance
<!-- Previously accepted guidance that should stop steering agents. State the
artifact, reason, evidence/date, and replacement if any. Do not use this for
draft hypotheses. -->
-

### Incidents
<!-- If there was a failed round/deployment/test: link to the incident record -->
-

### Promote to shared knowledge base?
<!-- yes - if useful beyond this one project instance; no - stays local -->
[ ] yes - [rationale]
[ ] no - stays local

### Updated knowledge files
<!-- Which files under knowledge/ were created or updated -->
-
```

---

## If the session taught nothing

```markdown
## Knowledge Delta

<!-- no-knowledge-delta: mechanical task -->
```

This exact HTML comment is the marker `scripts/eif_check_knowledge_delta.py`
checks for. Do not use it for "I didn't feel like filling this in" - it's
for changes that genuinely have no rule/fact/decision implication (typo
fixes, dependency bumps with no behavior change, formatting-only diffs).

Machine-checkable via `scripts/eif_check_knowledge_delta.py`, which
distinguishes `meaningful` / `mechanical` (the marker above) / `empty` (an
untouched template heading) - see that script's own test suite for the
exact rules.
