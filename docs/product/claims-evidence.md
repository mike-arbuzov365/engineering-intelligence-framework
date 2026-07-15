---
type: claim_register
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

<!-- Knowledge source: vertical slice + takeover review, 2026-07-15. This
document is the source of truth for what README/website/article/LinkedIn
copy is allowed to say. A claim only moves to OBSERVED when this file names
the specific evidence for it - not on the strength of how the framework is
supposed to work.

type: claim_register (see core/ontology/knowledge-types.md#claim_register).
It was briefly mistyped as decision_register; corrected in the takeover
review because claims are not decisions - a decision register tracks what
was decided, a claim register tracks how strongly evidence supports a public
claim. It holds many independently-statused entries, so it carries no single
frontmatter `evidence` label; its own status: validated means the table
below accurately reflects each claim's evidence status, not that every claim
is OBSERVED. -->

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
| EIF can initialize a separate, runnable project instance | OBSERVED | `scripts/eif_init.py` initialized an instance in a temp directory *outside* the framework checkout; the generated commands (referencing the pinned `.eif/runtime/` bundle) then ran from that instance with no framework on the path - search, validate, and Ukrainian render all executed this session. Non-destructive behavior (conflict guard, `--force` backup, `--dry-run`, CLAUDE.md marker merge) and real framework-ref provenance covered by `scripts/tests/test_init.py` (18 checks) | Experimental bootstrap, not a stable CLI - does not ratify D-05/D-08; the bundle duplicates framework code per instance (an accepted v0.1 tradeoff); only exercised on Windows this session | "An experimental bootstrap initializes a self-contained project instance - real framework-ref provenance, a pinned runtime bundle, and a CLAUDE.md entrypoint - whose commands run from the instance with no framework checkout present, non-destructively over an existing repo." | "`eifctl`." "Official CLI." "One-command install." "Zero-copy." |
| EIF retrieves relevant prior engineering knowledge (lifecycle-aware, Unicode) | OBSERVED | `eif_search_knowledge.py "leap year"` returned the relevant failure pattern first and changed the implementation actually written; a Ukrainian query (`високосний`) matched Ukrainian content; a `rejected` hypothesis was excluded by default and reported as status-ineligible; a malformed artifact was reported, not silently dropped (`scripts/tests/test_search_knowledge.py`, 8 checks) | Offline keyword/substring scoring only, no semantic search; tested against small seeded indexes, not a realistic-sized knowledge base | "Offline, lifecycle-aware keyword retrieval surfaces relevant validated knowledge (including Ukrainian), excludes rejected/superseded by default, and reports malformed artifacts distinctly from no-result - and that retrieval changed the implementation." | "Semantic search." "AI-powered retrieval." "Understands your codebase." |
| EIF supports Ukrainian project-facing documentation and retrieval | OBSERVED (partial) | `locales/uk/` rendered for real via the committed `scripts/eif_render.py` command into the demo's Knowledge Delta and closeout; real Ukrainian status messages from `eif_init.py`; Ukrainian knowledge retrieval verified (`test_search_knowledge.py`); English fallback verified (`test_locale.py`, `test_render.py`) | 4 surfaces (status messages, Knowledge Delta, closeout headings, retrieval) - not full agent-response localization; `terminology.yaml` not populated; D-06/D-07 remain open, not ratified | "The slice generates Ukrainian Knowledge Delta, closeout headings and status messages through a locale layer with a real render command, retrieves Ukrainian knowledge, and falls back to English cleanly." | "Fully localized." "Native Ukrainian support." "Multi-language" (implying more than the 2 locales that exist). |
| The first adapter's entrypoint is generated correctly | OBSERVED (partial) | Claude Code CLI `2.1.169` verified live 2026-07-15; official docs confirm Claude Code loads `CLAUDE.md` at session start (Context7, code.claude.com/docs/en/memory), so `eif_init` generates `CLAUDE.md`, not AGENTS.md; instruction/skill discovery OBSERVED in-session | Hook rewrite behavior NOT re-verified end-to-end this round - carried over from dated (2026-06-16) private evidence, flagged in `adapters/claude-code/README.md`; no second adapter | "The bootstrap generates the correct Claude Code entrypoint (CLAUDE.md, the file it actually loads); instruction and skill discovery were verified live; hook behavior is carried over, not re-verified this round." | "Fully verified adapter." "Hooks guaranteed to work." |
| CI validates EIF artifacts | OBSERVED | `.github/workflows/ci.yml` runs privacy scanning, frontmatter/config schema validation, link checking, Knowledge Delta completeness (now fetching the PR body live, not the frozen event payload), the runtime unit tests (init, index, search, locale, render, journey) and the demo behavioral test, with least-privilege `permissions`; all suites run locally with real pass results before push | Branch protection / required status checks are not configured at the GitHub settings level - CI passing is "required by policy," not technically enforced (see `docs/architecture/HOW-EIF-WORKS.md#quality`) | "CI runs schema validation, privacy scanning, link checking, Knowledge Delta completeness, and the runtime + demo test suites on every PR." | "CI blocks merging." "Fully tested." |
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
