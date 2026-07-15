# Demo: v0.1 vertical slice

<!-- Knowledge source: vertical slice + takeover review, 2026-07-15. Every
command below was actually run; output blocks are real captured evidence.
This demo is a project instance that lives inside the framework repo, but its
generated commands reference the pinned `.eif/runtime/` bundle, so they are
exactly what a *separate* repository would run. See the private migration
ledger and PR #2 description for provenance. -->

A synthetic single-file Python task that walks through the smallest complete
EIF workflow, as a real, separately-runnable project instance: initialize,
seed and retrieve knowledge (lifecycle-aware), make one real change informed
by that retrieval, verify with a real test, and close out in Ukrainian via
the locale layer.

No familiarity with the private EI this framework was extracted from is
assumed.

## Prerequisites

- Python 3.11+
- After step 1 generates the runtime bundle: `pip install -r .eif/runtime/requirements.txt`
  (PyYAML + jsonschema, pinned). No pytest - the demo's behavioral test uses
  only the standard library.

## 1. Initialize the instance

`scripts/eif_init.py` is an **experimental** bootstrap (it does not ratify a
CLI name or packaging strategy - D-05/D-08 remain open). From the framework
root:

```
python scripts/eif_init.py --framework-root . --instance-path examples/demo-workspace --project-name demo-workspace --locale uk --force
```

Real output, captured 2026-07-15:

```text
Ініціалізація EIF project instance у <path>/examples/demo-workspace
overwrite .eif/config.yaml (framework.ref 4a5c804)
eif-validate: 1 file, 0 error(s)
Створено .eif/config.yaml (locale: uk)
refresh .eif/runtime (pinned bundle)
create CLAUDE.md (EIF-managed block)
Згенеровано agent instructions у <path>/examples/demo-workspace/CLAUDE.md
Knowledge index згенеровано: 2 артефакт(ів)
```

This generates three things, all runnable from the instance root even with no
framework checkout present:

- `.eif/config.yaml` - records the **real** framework commit it was generated
  from (`framework.ref`), validated on the spot against the config schema.
- `.eif/runtime/` - a pinned, self-contained bundle of the scripts, schemas,
  ontology, locales and templates the instance's own commands use (gitignored;
  regenerated on init/upgrade).
- `CLAUDE.md` - the agent entrypoint Claude Code loads at session start (not
  AGENTS.md - verified against the official docs and CLI `2.1.169`). Only the
  `EIF:BEGIN`/`EIF:END` block is managed; project-authored content is never
  clobbered.

Init is **non-destructive**: it refuses to overwrite an existing config
without `--force` (which backs it up first), and `--dry-run` writes nothing.
That is what makes adopting an existing repository - the eventual migration of
the private production instance - safe. See
[`../../docs/architecture/instance-contract.md`](../../docs/architecture/instance-contract.md).

## 2-3. Retrieve a relevant prior lesson (lifecycle-aware)

The knowledge index was built by step 1. Search it - by default only
validated knowledge is returned, and every result shows its status/evidence:

```
python .eif/runtime/eif_search_knowledge.py --knowledge-root knowledge "leap year"
```

```text
eif-search-knowledge: 2 result(s) for query: leap year
  [ 44] failure-patterns/PATTERN-0001-naive-leap-year-check.md  (status=validated, evidence=OBSERVED, confidence=high, type=failure_pattern)
        The obvious, plausible-looking implementation of a leap-year check is:
  [ 21] facts/FACT-0001-gregorian-leap-year-rule.md  (status=validated, evidence=OBSERVED, confidence=high, type=fact)
        A year is a leap year if and only if:
```

Retrieval is not decorative: [`task-scope.md`](task-scope.md) records it and
the implementation follows the retrieved rule rather than the naive check the
failure pattern warns against. A `rejected` hypothesis on the same topic would
be **skipped** by default (reported as status-ineligible), not returned as if
it were validated - see `scripts/tests/test_search_knowledge.py`. Ukrainian
(Cyrillic) queries work too - the tokenizer is Unicode-aware.

## 4. Task scope

[`task-scope.md`](task-scope.md), written before the change.

## 5-6. Make the change, verify with a real test

The behavioral test [`tests/test_calendar_utils.py`](tests/test_calendar_utils.py)
covers ordinary years and the century-exception cases (1900, 2000, 2100) that
a naive `year % 4 == 0` fails. `src/calendar_utils.py` implements the rule from
`FACT-0001`.

The failing-before -> passing-after transition is reproduced **deterministically**
by [`../../scripts/tests/test_journey.py`](../../scripts/tests/test_journey.py):
in an isolated copy it resets the implementation to an unimplemented stub,
asserts the test FAILS, applies the committed solution, and asserts it PASSES.
That test is what proves the journey reproduces from a clean clone - not merely
re-running the already-passing committed state.

```
python examples/demo-workspace/tests/test_calendar_utils.py -v   # passes on the committed solution
python scripts/tests/test_journey.py                             # proves failing-before -> passing-after
```

## 7-8. Knowledge Delta and closeout, in Ukrainian

[`knowledge-delta.md`](knowledge-delta.md) and
[`session-closeout.md`](session-closeout.md) were generated from the Ukrainian
locale pack with the real render command (not a one-off script):

```
python .eif/runtime/eif_render.py --framework-root .eif/runtime --locale uk knowledge-delta
python .eif/runtime/eif_render.py --framework-root .eif/runtime --locale uk session-closeout
```

then filled with what actually happened. The Knowledge Delta's promotion
section demonstrates correct routing: the leap-year failure pattern is a
**project-level** domain lesson and stays local; the two framework-tooling
incidents found while building this (non-English console encoding, non-ASCII
retrieval) are the **framework-level** promotion candidates, flagged for owner
ratification, not auto-promoted.

## 9. Validate the instance

```
python .eif/runtime/eif_validate_frontmatter.py --framework-root .eif/runtime --instance-root . "knowledge/**/*.md"
python .eif/runtime/eif_validate_frontmatter.py --framework-root .eif/runtime --config .eif/config.yaml
```

## Known limitations

- One scenario (leap-year), one adapter (Claude Code - see
  [`../../adapters/claude-code/README.md`](../../adapters/claude-code/README.md);
  instruction/skill discovery verified live, hooks not re-verified end-to-end).
- Retrieval is offline keyword/substring scoring, not tested at scale.
- No Graphify, no RTK (out of scope for this slice).
- `eif_init.py` is an experimental bootstrap, not a stable CLI.
- Ukrainian locale coverage is status messages + Knowledge Delta + closeout
  headings + knowledge retrieval - not full agent-response localization.

See [`../../docs/product/claims-evidence.md`](../../docs/product/claims-evidence.md)
for exactly which claims this demo supports and the allowed/forbidden wording
for each.
