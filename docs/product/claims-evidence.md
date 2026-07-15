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
| EIF runs end to end | OBSERVED | `scripts/tests/test_journey.py` (26 checks) - a real subprocess journey against a fresh seed project: init, config/lock validation, runtime materialization, English+Ukrainian retrieval, task-scope, failing-before/passing-after test, config-driven Ukrainian Knowledge Delta + closeout written to real files, artifact/privacy/link validation from the instance's own bundle, non-destructive re-init, a second independent instance, and an injected upgrade failure with proven rollback | One scenario (a leap-year calculator), one adapter (Claude Code), no multi-repo, no Graphify/RTK, single operator this session, not yet reproduced by an independent human | "The v0.1 vertical slice runs end to end - a real subprocess-driven journey, including an injected-failure rollback proof - against one synthetic demo project instance." | "EIF works." "Production-ready." "Proven at scale." |
| EIF can initialize a separate, runnable, upgradeable project instance | OBSERVED | `scripts/eif_init.py` initialized an instance in a temp directory *outside* the framework checkout with real dirty-checked provenance and a sha256-hashed bundle manifest; the pinned `.eif/runtime/` source bundle then ran standalone (search, validate, render) with no framework on the path; a routine re-run left the user's `.eif/config.yaml` byte-for-byte unchanged (upgrade only refreshes the EIF-managed lock/bundle/entrypoint); an injected mid-upgrade failure (a mandatory bundle file removed) left the instance's prior runtime intact and fully functional. `scripts/tests/test_init.py` (38 checks) + `test_journey.py` | Experimental bootstrap, not a stable CLI - does not ratify D-05/D-08; the bundle is a pinned **source** copy, not a self-contained interpreter environment (`pip install` is still required once); only exercised on Windows this session | "An experimental bootstrap initializes a project instance with real, dirty-checked framework provenance and a hashed runtime source bundle, upgradeable without touching user-owned settings, with a proven rollback path if an upgrade fails partway." | "`eifctl`." "Official CLI." "One-command install." "Zero-copy." "Fully self-contained." |
| EIF retrieves relevant prior engineering knowledge (lifecycle-aware, Unicode, schema-aware) | OBSERVED | `eif_search_knowledge.py "leap year"` returned the relevant failure pattern first and changed the implementation actually written; a Ukrainian query (`високосний`) matched Ukrainian content; a `rejected` hypothesis was excluded by default and reported as status-ineligible; an unparseable-YAML artifact and a schema-invalid artifact (parses fine, violates the ontology) are reported in two *distinct* categories, neither confused with "no results" (`scripts/tests/test_search_knowledge.py`, 11 checks; `test_generate_index.py`, 12 checks) | Offline keyword/substring scoring only, no semantic search; tested against small seeded indexes, not a realistic-sized knowledge base; schema-invalid detection requires `--framework-root` to be passed - without it, a schema-invalid artifact silently passes through as if valid (documented, not hidden) | "Offline, lifecycle-aware, schema-aware keyword retrieval surfaces relevant validated knowledge (including Ukrainian), excludes rejected/superseded by default, and reports unparseable vs. schema-invalid vs. not-found as three distinct, honest outcomes." | "Semantic search." "AI-powered retrieval." "Understands your codebase." |
| EIF supports Ukrainian project-facing documentation and retrieval | OBSERVED (partial) | `locales/uk/` rendered for real via the committed, config-driven `scripts/eif_render.py` command - run with **no `--locale` flag**, it reads `documentation_locale` from `.eif/config.yaml` and writes real `knowledge-delta.md`/`session-closeout.md` files (not stdout-only); real Ukrainian status messages from `eif_init.py`; Ukrainian knowledge retrieval verified; English fallback verified for both missing-config and unknown-locale cases (`scripts/tests/test_render.py`, 11 checks) | 4 surfaces (status messages, Knowledge Delta, closeout headings, retrieval) - not full agent-response localization; `terminology.yaml` not populated; D-06/D-07 remain open, not ratified | "The slice generates Ukrainian Knowledge Delta, closeout headings and status messages through a config-driven locale layer that writes real files, retrieves Ukrainian knowledge, and falls back to English cleanly." | "Fully localized." "Native Ukrainian support." "Multi-language" (implying more than the 2 locales that exist). |
| The first adapter's entrypoint is generated correctly | OBSERVED (partial) | Claude Code CLI `2.1.169` verified live 2026-07-15; official docs confirm Claude Code loads `CLAUDE.md` at session start (Context7, code.claude.com/docs/en/memory), so `eif_init` generates `CLAUDE.md`, not AGENTS.md, via a restricted adapter registry (`--adapter` only accepts registered names - an unsupported adapter name is rejected, not silently mapped to the wrong entrypoint); instruction/skill discovery OBSERVED in-session | Hook rewrite behavior NOT re-verified end-to-end this round - carried over from dated (2026-06-16) private evidence, flagged in `adapters/claude-code/README.md`; no second adapter | "The bootstrap generates the correct Claude Code entrypoint (CLAUDE.md, the file it actually loads) from a restricted adapter registry; instruction and skill discovery were verified live; hook behavior is carried over, not re-verified this round." | "Fully verified adapter." "Hooks guaranteed to work." "Any adapter name works." |
| A project instance can validate itself from its own bundle | OBSERVED | `.eif/runtime/` bundles schema-aware frontmatter/config/lock validation, privacy scanning, link checking, and localized rendering - all six ran as real subprocesses from an isolated instance's own bundle in `test_journey.py` steps 2, 5, 6, 11-14, with zero privacy findings and all links resolving. `docs/architecture/instance-contract.md#validation-surface` names exactly what is and is not bundled | PR-workflow-specific tooling (Knowledge Delta CI check, merge-gate script) is deliberately framework-maintainer-only, not bundled - "validate the instance" does not mean "re-implement this repository's entire CI" | "A project instance can run schema validation, privacy scanning, link checking, and localized rendering from its own pinned bundle, with no framework checkout present." | "Full CI in every instance." "Instance and framework CI are identical." |
| CI validates EIF artifacts | OBSERVED | `.github/workflows/ci.yml` runs privacy scanning, frontmatter/config/lock schema validation, link checking, Knowledge Delta completeness (fetching the PR body live via `gh api`, not the frozen event payload - a real gap found and fixed when a body-only edit could not turn a failing check green without a new commit), the runtime unit tests (init, index, search, locale, render, journey - 9 suites, 86+ checks) and the demo behavioral test, with least-privilege job `permissions`; all suites run locally with real pass results before every push | Branch protection / required status checks are not configured at the GitHub settings level - CI passing is "required by policy," not technically enforced (see `docs/architecture/HOW-EIF-WORKS.md#quality`) | "CI runs schema validation (including a separate provenance-lock schema), privacy scanning, link checking, Knowledge Delta completeness against the live PR body, and the runtime + demo test suites on every PR." | "CI blocks merging." "Fully tested." |
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
