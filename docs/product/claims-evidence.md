---
type: decision_register
status: validated
scope: framework
created: 2026-07-15
review_after: 2026-10-15
related:
  - ../../examples/demo-workspace/README.md
  - ../../adapters/claude-code/README.md
  - ../benchmarks/README.md
---

# Public claims evidence ledger

<!-- Knowledge source: this PR's vertical slice, 2026-07-15. This document
is the source of truth for what README/website/article/LinkedIn copy is
allowed to say. A claim only moves to OBSERVED when this file names the
specific evidence for it - not on the strength of how the framework is
supposed to work.

type: decision_register (not a single-claim type - same "maintained list
of many entries, each independently statused" shape core/policies/
decisions.md uses, see core/ontology/knowledge-types.md#decision_register
- so the frontmatter `evidence` field is correctly absent: this document's
own status: validated means the table below accurately reflects each
claim's status as of review_after, not that every claim is OBSERVED. -->

Before writing any public-facing claim about EIF (README, website,
article, LinkedIn post, demo video, FAQ), check this table. A status of
`OBSERVED` requires the Evidence column to name something concrete and
reproducible - a command, a file, a test - not "the design supports this."

## Status definitions

- **OBSERVED** - directly exercised and verified in this repository, with
  evidence named below.
- **UNVERIFIED** - plausible, planned, or partially built, but not yet
  backed by a reproducible test or measurement.
- **NOT TESTED** - explicitly out of scope for what has been built so far
  (not a judgment that it wouldn't work - just that nothing here tests it).

## Claims

| Claim | Status | Evidence | Limitations | Allowed public wording | Forbidden wording |
|---|---|---|---|---|---|
| EIF runs end to end | OBSERVED | `examples/demo-workspace/` - init, config validation, knowledge index generation, real retrieval, scoped task, failing-before/passing-after test, Knowledge Delta, closeout, instance validation, all executed for real this session with captured output (see `examples/demo-workspace/README.md`) | One scenario (a leap-year calculator), one adapter (Claude Code), no multi-repo, no Graphify/RTK, single operator this session, not yet reproduced independently by a third party | "The v0.1 vertical slice runs end to end against one synthetic demo project instance, reproduced from a clean directory outside the framework checkout." | "EIF works." "Production-ready." "Proven at scale." |
| EIF can initialize a separate project instance | OBSERVED | `scripts/eif_init.py`, exercised against `examples/demo-workspace/` and against a temporary directory outside the framework checkout (`scripts/tests/test_init.py`) | Experimental bootstrap script, not a stable CLI - does not ratify D-05 (CLI name) or D-08 (dependency model); no package or installer; only exercised on Windows this session | "An experimental bootstrap script initializes a new project instance with a validated config, generated instructions, and a knowledge index." | "`eifctl`." "Official CLI." "One-command install." |
| EIF retrieves relevant prior engineering knowledge | OBSERVED | `scripts/eif_search_knowledge.py "leap year"` against the seeded 2-artifact index returned the relevant failure pattern first (see `examples/demo-workspace/task-scope.md`'s "Experience retrieval preflight" section) and the retrieval directly changed the implementation actually written | Offline keyword/substring scoring only, no semantic search; tested against a 2-artifact seeded index, not a realistic-sized knowledge base | "Keyword-based retrieval over a small seeded knowledge base surfaced the relevant prior lesson before implementation, and that retrieval changed the implementation." | "Semantic search." "AI-powered retrieval." "Understands your codebase." |
| EIF supports Ukrainian project-facing documentation | OBSERVED (partial) | `locales/uk/` messages and templates, rendered for real via `scripts/eif_locale.py` into `examples/demo-workspace/knowledge-delta.md` and `session-closeout.md`; real Ukrainian status messages printed by `scripts/eif_init.py` this session | Only 3 output surfaces covered (status messages, Knowledge Delta headings, closeout headings) - not full agent-response localization; `locales/*/terminology.yaml` not populated; D-06 (canonical language) and D-07 (Ukrainian release timing) remain open, not ratified by this slice | "This slice generates Ukrainian Knowledge Delta and closeout headings and status messages through a locale layer, with verified English fallback." | "Fully localized." "Native Ukrainian support." "Multi-language" (implying more than the 2 locales that exist). |
| The first adapter has been verified | OBSERVED (partial) | Claude Code CLI `2.1.169` verified live 2026-07-15 (`claude --version`); persistent-instruction auto-load and skill discovery OBSERVED directly in the session that built this slice | Hook rewrite behavior was NOT re-verified end-to-end this round - carried over from the private instance's dated (2026-06-16) evidence, explicitly flagged in `adapters/claude-code/README.md`; no second adapter tested | "Claude Code's instruction and skill discovery were verified live; hook behavior is carried over from earlier private-instance testing, not re-verified end-to-end this round." | "Fully verified adapter." "Hooks guaranteed to work." |
| CI validates EIF artifacts | OBSERVED | `.github/workflows/ci.yml` runs privacy scanning, frontmatter/config schema validation, link checking, Knowledge Delta completeness, and (as of this PR) the vertical-slice tests and the demo's behavioral test, on every PR; all suites run locally this session with real pass results before push | Branch protection / required status checks are not configured at the GitHub settings level - CI passing is "required by policy," not technically enforced (see `docs/architecture/HOW-EIF-WORKS.md#quality`) | "CI runs schema validation, privacy scanning, link checking, and Knowledge Delta completeness checks on every PR." | "CI blocks merging." "Fully tested." |
| EIF saves tokens | UNVERIFIED | None run yet - see `docs/benchmarks/README.md` | No benchmark exists | "A token-efficiency benchmark is planned and not yet run." | Any specific percentage. "Saves tokens." "More efficient." |
| Graphify improves structural navigation | NOT TESTED | Explicitly excluded from this slice (hard boundary - optional integration, not ported here) | Not included, not exercised, not measured in this repository at all | "Graphify is an optional integration; this slice does not include or test it." | "Improves navigation." "Faster codebase understanding." |
| RTK reduces tool-output context | NOT TESTED | Explicitly excluded from this slice (hard boundary - optional integration, not ported here) | Not included, not exercised, not measured in this repository at all | "RTK is an optional integration; this slice does not include or test it." | Any specific percentage. "Reduces context." |
| EIF improves task quality or rework rate | UNVERIFIED | No comparative study exists | No baseline, no control, no measurement methodology defined yet | "No comparative study has been run; this claim is not yet supported by evidence." | "Improves quality." "Reduces rework." "Fewer bugs." |

## How to use this table

- Writing README/website/article copy: quote the "Allowed public wording"
  column verbatim or paraphrase conservatively - never strengthen it.
- Never use anything in "Forbidden wording," even qualified ("might save
  tokens," "could improve quality") - if evidence doesn't support the
  claim, say what's actually true instead (planned, not yet measured).
- A claim only moves from `UNVERIFIED`/`NOT TESTED` to `OBSERVED` when a
  new row's Evidence column names something reproducible, added in the
  same PR that changes its status - not retroactively assumed.
