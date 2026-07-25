# Engineering Intelligence Framework

A quality-first control plane for governed AI-agent software development.

EIF gives AI coding agents persistent engineering knowledge, explicit source
identity, controlled execution workflows, quality gates and token-efficient
tool integrations.

> **Status: pre-release (v0.1 in progress).** This repository is being
> extracted from a private production instance that has run this
> methodology daily since May 2026. Expect gaps until the
> [Definition of Public-Ready](docs/architecture/HOW-EIF-WORKS.md#definition-of-public-ready)
> checklist is complete.

A presentation website source lives in [`site/`](site/README.md), buildable
and previewable locally (`npm ci && npm run build:preview && npm run preview`
from that directory). It is **not deployed** - domain, hosting and
publication are owner-gated decisions that have not been made.

## The problem

AI coding agents are powerful, but most agentic workflows still treat chat
history as engineering memory:

- Previous decisions live only inside one session and are lost when its
  context is compacted or the session ends.
- The agent re-discovers the same files and re-derives the same conclusions
  every session.
- Local lessons never resurface before a new, similar task.
- Command output floods the context window without filtering.
- Architecture decisions and scope get mixed up with unverified assumptions.
- A merged PR gets treated as proof of working behavior, without evidence.
- Quality, privacy, and token-efficiency are governed by separate,
  sometimes contradictory rules.

## What EIF is

A **control plane** that coordinates tools and agents without replacing them:

```text
User intent
  -> Experience retrieval
  -> Authority and scope
  -> Structural navigation
  -> Controlled execution
  -> Tests and evidence
  -> Knowledge Delta
  -> Durable engineering intelligence
```

## What EIF is not

- Another chat memory store.
- A replacement for source code.
- A vector database.
- A code graph (though it integrates with one - see below).
- A token compressor (though it integrates with one - see below).
- An autonomous agent that merges unchecked changes.
- A replacement for tests, CI, or human ownership.

## Core differentiators

1. **Authority is multi-axis, not one ranked list.** Normative claims
   ("what should happen"), empirical claims ("what actually happens"),
   which instruction controls the agent, and whether an artifact is even
   trustworthy to cite are four different questions with four different
   answers - conflating them produces wrong defaults. See
   [Authority model](core/ontology/authority-model.md).
2. **Experience retrieval before implementation.** Knowledge isn't just
   stored, it's actively pulled into context before new work starts.
   Learning runs as [two loops](docs/architecture/HOW-EIF-WORKS.md#the-two-loops),
   not one: the inner loop asks what a session learned, the outer
   ([retro](playbooks/run-retro.md)) asks what keeps happening across many
   of them. Promotion is driven by the outer loop, because a single session
   has no evidence that its lesson generalizes.
3. **Ephemeral and durable context are separated.** Session-scoped state is
   never mistaken for validated, durable knowledge.
4. **Execution is governed and iterative work is bounded.** Scope, observable
   success, evaluators, iteration/remote-run budgets, evidence, and closeout
   are part of the workflow, not an afterthought. See the
   [Bounded Evidence Loop](playbooks/bounded-evidence-loop.md).
5. **Quality wins over token savings.** Compression can never weaken
   verification, source hierarchy, or review.
6. **Tool-agnostic core.** Claude Code, Codex, Cursor, Hermes, and others are
   adapters, not the center of the system.
7. **Optional integrations.** A structural code graph and a shell-output
   compression layer plug in as capabilities, not required dependencies.
8. **Multilingual project documentation.** Framework documentation is
   English-first; project instances can declare their own documentation
   locale without duplicating the whole methodology.
9. **Dogfooded governance.** This repository's own review process found and
   fixed real inconsistencies in its own ontology and honesty about what's
   built - see [Limitations](docs/architecture/HOW-EIF-WORKS.md#limitations).

## Current capability

<!-- Keep this table honest - see AGENTS.md. A row claiming "Available"
that isn't runnable is worse than not having the row. -->

| Capability | Status | Notes |
|---|---|---|
| Ontology (authority, types, confidence, lifecycle) | **Available** | [`core/ontology/`](core/ontology/) |
| Machine-readable schemas + real validator | **Available** | [`core/schemas/`](core/schemas/) validated with `jsonschema`'s `Draft202012Validator` + format checking via [`scripts/eif_validate_frontmatter.py`](scripts/eif_validate_frontmatter.py); 15 positive/negative fixtures, all passing. Also reachable via `eifctl validate` - see the installable-package row below. |
| Governance docs (LICENSE, CONTRIBUTING, SECURITY, ...) | **Available** | repo root |
| Privacy scan / frontmatter+config+lock validation / link check / Knowledge Delta check | **Available** | [`scripts/`](scripts/), each with its own test suite, run in CI on every PR; the first four also run from a project instance's own bundle, not just the framework repo - see [`docs/architecture/instance-contract.md#validation-surface`](docs/architecture/instance-contract.md#validation-surface). Privacy scan has a narrow, auditable suppression mechanism (`privacy.suppressions` in config: rule + exact path + a content fingerprint + rationale + review date - identifies one specific finding, never a whole rule+file; never weakens a detection pattern itself; an expired, no-longer-matching, or malformed suppression is reported as its own finding rather than silently accepted) |
| Decision ledger | **Available** | [`core/policies/decisions.md`](core/policies/decisions.md) |
| `.eif/config.yaml` schema | **Available** | Validated the same way as frontmatter; `eifctl init` and the standalone `eif_init.py` generate it with real provenance |
| Vertical-slice plan | **Built (experimental)** | [`docs/guides/vertical-slice.md`](docs/guides/vertical-slice.md) (design) + [`examples/demo-workspace/`](examples/demo-workspace/) (the actual, reproduced slice - see its README) |
| Controlled merge entrypoint | **Available**, not wired into repo settings or a hook guard | [`scripts/eif_merge_pr.py`](scripts/eif_merge_pr.py) - dry-run tested against this repo's real PR #1 |
| Installable package (`eifctl`) | **Built, Ratified (D-05/D-08), not published** | `pip install .` gives 7 tested subcommands (`init`, `doctor`, `search`, `render`, `privacy-scan`, `validate`, `version`) without requiring a framework checkout. The expanded installed-wheel suite passes 60/60 locally, including machine-readable integration states, the standalone benchmark C/D contract tool and injected upgrade rollback; the updated Windows/Ubuntu Python 3.11/3.12 matrix remains a manual release gate under D-14, not routine PR CI. See [`docs/product/claims-evidence.md`](docs/product/claims-evidence.md). |
| Bootstrap (`eifctl init` / `eif_init.py`) | **Available (experimental)** | Initializes or upgrades a separately runnable instance with provenance, a hashed runtime bundle, marker-safe adapter entrypoints, path validation, adoption/coexistence preflight, and transactional rollback. D-05/D-08 ratify the CLI/package model; PyPI publication and stable-release compatibility are still open. See [`docs/architecture/instance-contract.md`](docs/architecture/instance-contract.md). |
| Instance self-verification (`eif_verify_runtime.py`) | **Available (experimental)** | [`scripts/eif_verify_runtime.py`](scripts/eif_verify_runtime.py) - bundled "doctor" command: config/lock schema validity, manifest digest self-consistency, per-file bundle hash verification, missing/unexpected-file classification, config/adapter/lock/entrypoint consistency, provenance (dirty/asserted) notes, `CLAUDE.md`/`.gitignore` marker integrity, and drift between `.eif/config.yaml` and the generated entrypoint block or knowledge index (a hand-edited config or index with no regeneration fails with a specific fix instruction, not a silent pass) - all from the instance's own bundle, no framework checkout needed |
| Instance contract / upgrade / adoption | **Available (experimental)** | [`docs/architecture/instance-contract.md`](docs/architecture/instance-contract.md) - provenance, upgrade-by-re-init, and safe adoption of an existing repo, hardened against a real external pilot: adoption preflight, `coexist` mode, repository-origin provenance (an existing repo with no `CLAUDE.md` is recorded `adopted`, not `greenfield`), configurable knowledge paths, path-escape validation, finding-specific privacy suppressions, tested with a realistic sanitized fixture (`scripts/tests/test_adoption.py`, 67 checks) |
| Knowledge index / lifecycle + schema-aware retrieval | **Available (experimental)** | [`scripts/eif_generate_index.py`](scripts/eif_generate_index.py), [`scripts/eif_search_knowledge.py`](scripts/eif_search_knowledge.py) - offline, Unicode-aware keyword search that returns only eligible statuses by default (excludes rejected/superseded), and reports three honest outcomes for anything wrong: unparseable YAML, schema-invalid (parses fine, violates the ontology), or status-ineligible - never conflated with "no results." No embeddings; not tested at scale |
| Locale layer (Ukrainian project docs + retrieval) | **Available (experimental)**, 4 surfaces | [`locales/`](locales/), [`scripts/eif_locale.py`](scripts/eif_locale.py), [`scripts/eif_render.py`](scripts/eif_render.py) - status messages, Knowledge Delta, closeout headings, and Ukrainian knowledge retrieval, with a real render command and English fallback; not full agent-response localization; D-06/D-07 remain open |
| Playbooks, templates, skills | **Available (v0.1 operating set)** | 13 playbooks, 15 templates, and 9 skills, including planning/execution/review, knowledge operations, the [Bounded Evidence Loop](playbooks/bounded-evidence-loop.md), the outer [retro loop](playbooks/run-retro.md) that finds patterns repeating across many sessions, and the [knowledge curator](playbooks/knowledge-curator.md) that ranks what in the knowledge base needs maintenance; knowledge-health metrics and customer workflows remain out of v0.1 scope |
| Agent adapters | **2 of 2 required for v0.1 (Claude Code, Cursor) + 2 experimental-supported (Codex, Hermes) - adapter scope now FROZEN at 4, entrypoints generated for all** | [`adapters/claude-code/README.md`](adapters/claude-code/README.md) - `eif_init` generates the correct `CLAUDE.md` entrypoint (the file Claude Code loads, per official docs + CLI `2.1.169`); instruction/skill discovery verified live; hooks not re-verified this round; no hook scripts shipped. [`adapters/cursor/README.md`](adapters/cursor/README.md) - `eif_init` generates `.cursor/rules/eif/governance.mdc` (Cursor's current Rules format, per official docs + installed `3.11.19`); code/test-validated (74 acceptance checks); real Cursor runtime consumption not yet manually confirmed - see that README's "Runtime-validation status". [`adapters/codex/README.md`](adapters/codex/README.md) - dynamic active-entrypoint resolution, re-verified against Codex's own primary Rust source (not documentation) and real installed-CLI runtime proof from an isolated `CODEX_HOME` (123 checks). [`adapters/hermes/README.md`](adapters/hermes/README.md) - dynamic active-source resolution, verified against Hermes's own installed Python source and real installed-CLI runtime proof from an isolated `HERMES_HOME` (77 checks). All 12 directed adapter-switching pairs proven - see [`adapters/switch-matrix.json`](adapters/switch-matrix.json) (81 checks). Codex and Hermes remain experimental-supported, not required v0.1 adapters (D-09), and neither is a claim of production readiness. See [`adapters/README.md`](adapters/README.md) |
| Optional integration contract | **Behavioral adapters built (experimental)** | RTK has version/argv/native-`rg`/diff canaries, a command registry and content-free local telemetry; Graphify has version/query/path/explain canaries plus a D-08 artifact lifecycle bound to source commit, graph digest, explicit repository identity and reviewed scope. Both remain optional and degrade to core-safe fallbacks. Focused evidence is provider/version bounded, not a general performance claim; see [`integrations/README.md`](integrations/README.md). Vendor-docs now declares a named provider (Context7, over MCP) with generated routing guidance and a reviewable per-adapter config template, but EIF does not install it and cannot probe it - see that integration's own README for the stated verification gap. |
| Demo workspace | **Built** | [`examples/demo-workspace/`](examples/demo-workspace/) - reproduced from a clean checkout, see its own README for captured command output |
| Benchmark | **Bounded A/B pilot published; C/D attempt contracts executable** | The existing real-agent pilot remains 6/6 attempts across three synthetic tasks and modes A/B, n=1 per cell. Modes C/D now require integrity-bound Graphify consumption and, for D, attempt-attributed RTK telemetry. Their deterministic runs are contract tests with token figures suppressed, not new performance evidence; see [`docs/benchmarks/README.md`](docs/benchmarks/README.md). |
| Public claims evidence ledger | **Available** | [`docs/product/claims-evidence.md`](docs/product/claims-evidence.md) - what's OBSERVED vs. UNVERIFIED vs. NOT TESTED, and the allowed/forbidden wording for each |

**Experimental quickstart.** Cloning this repository gets you the ontology,
schemas, governance docs, `eifctl` source package, operating layer, and one
reproduced vertical slice - not a stable release or a representative sample
of real engineering tasks. Follow
[`examples/demo-workspace/README.md`](examples/demo-workspace/README.md)
for the exact commands, real captured output, and known limitations. See
[`docs/guides/vertical-slice.md`](docs/guides/vertical-slice.md) for how
this slice was scoped and what's deliberately excluded from it.

## Core concepts

| Concept | What it does | Where |
|---|---|---|
| Authority model | Distinguishes normative, empirical, agent-execution, and knowledge-lifecycle authority instead of one ranked list | [`core/ontology/authority-model.md`](core/ontology/authority-model.md) |
| Knowledge taxonomy | Classifies knowledge artifacts (fact, rule, decision, risk, ...) | [`core/ontology/knowledge-types.md`](core/ontology/knowledge-types.md) |
| Confidence levels | Marks how trustworthy a claim was when validated - not a license to skip applicability checks | [`core/ontology/confidence-levels.md`](core/ontology/confidence-levels.md) |
| Status lifecycle | draft -> validated -> superseded -> deprecated (+ rejected for hypotheses) | [`core/ontology/status-lifecycle.md`](core/ontology/status-lifecycle.md) |
| Decision ledger | Which brand/license/structure decisions are ratified vs. provisional vs. open | [`core/policies/decisions.md`](core/policies/decisions.md) |
| Full architecture | End-to-end explanation of how it all fits together | [`docs/architecture/HOW-EIF-WORKS.md`](docs/architecture/HOW-EIF-WORKS.md) |

## Agent adapters

Four adapters are ported and **adapter scope is now frozen** at this set -
no fifth adapter, no hooks-parity rewrite, no new adapter abstraction. Two
are the required set for v0.1 per ratified decision D-09
(`core/policies/decisions.md`): **Claude Code** (`eif_init` generates
`CLAUDE.md`; see [`adapters/claude-code/README.md`](adapters/claude-code/README.md))
and **Cursor** (`eif_init` generates `.cursor/rules/eif/governance.mdc`; see
[`adapters/cursor/README.md`](adapters/cursor/README.md)). Two are
experimental-supported, not required for v0.1: **Codex** (`eif_init`
resolves and marker-merges into whichever entrypoint is actually active,
re-verified against Codex's own primary source; see
[`adapters/codex/README.md`](adapters/codex/README.md)) and **Hermes**
(`eif_init` resolves and marker-merges into whichever of a real four-tier
discovery chain is actually active, verified against Hermes's own
installed source; see [`adapters/hermes/README.md`](adapters/hermes/README.md)).
None requires Graphify or RTK - both remain optional integrations. No hook
scripts ship with any of the four adapters yet. Switching between any two
of the four (`--force --adapter <name>`) is supported and tested for all
12 directed pairs - see [`adapters/switch-matrix.json`](adapters/switch-matrix.json).
See [`adapters/README.md`](adapters/README.md) for the full adapter
registry and [`docs/product/claims-evidence.md`](docs/product/claims-evidence.md)
for exactly what is and is not verified for each.

## Optional integrations

EIF does not require any of these - it works in a degraded mode without
them, with explicit tradeoffs documented in
[`integrations/README.md`](integrations/README.md):

- **Structural code graph** - broad codebase/architecture navigation and
  impact analysis (`integrations/graphify/`).
- **Shell-output compression** - token-efficient command output filtering
  with tracked savings (`integrations/rtk/`).
- **Vendor documentation retrieval** - current, versioned library/API docs
  instead of stale training data (`integrations/vendor-docs/`). Declared
  provider: Context7, over MCP. EIF ships routing guidance and a reviewable
  config template but **does not install it**: an MCP server is configured
  at the user level, outside the project instance, and this framework never
  mutates user-level configuration.

## Language configuration

Framework documentation is English-first. Project instances declare their
own documentation locale in `.eif/config.yaml`; Ukrainian is the first
non-English locale pack built (`locales/uk/`) - status messages, Knowledge
Delta headings, and closeout headings are generated in Ukrainian for a
`uk` instance, verified end to end in
[`examples/demo-workspace/`](examples/demo-workspace/). Not yet covered:
full agent-response localization and `terminology.yaml`. See
[`locales/README.md`](locales/README.md).

## Quality and safety model

- Source authority is explicit and multi-axis - normative and empirical
  claims are never silently collapsed into a single ranking; disagreements
  are recorded, not discarded. See
  [Authority model](core/ontology/authority-model.md).
- `OBSERVED` / `INFERRED` / `ASSUMED` evidence labels are first-class
  frontmatter fields (`evidence:`), not just a prose convention - see
  [`core/schemas/knowledge-frontmatter.schema.json`](core/schemas/knowledge-frontmatter.schema.json).
- Compression (structural navigation, shell-output filtering) is required
  to preserve correctness before it is allowed to save tokens - see
  [`docs/benchmarks/`](docs/benchmarks/).
- CI gates are designed to actually block a non-compliant merge path, not
  just document a policy - see [`scripts/`](scripts/) and
  [`.github/workflows/ci.yml`](.github/workflows/ci.yml). This repository
  runs its own privacy scan, frontmatter validation, and link check on
  every PR - see [`AGENTS.md`](AGENTS.md).

## Benchmarks

A first bounded real-agent pilot is published: one model, three synthetic
tasks, modes A/B, and one attempt per cell. All six attempts succeeded, but
the sample is too small to support a general token-efficiency claim. See
[`docs/benchmarks/README.md`](docs/benchmarks/README.md) for raw-result links,
methodology, and limitations.

## Demo

A synthetic `examples/demo-workspace/` walks through the full v0.1 slice -
initialize an instance, seed and search real knowledge, scope and
implement one real change informed by that retrieval, verify it with a
real failing-before/passing-after test, and close out truthfully in
Ukrainian. See [`examples/demo-workspace/README.md`](examples/demo-workspace/README.md)
for the exact commands and captured output, and
[`docs/product/claims-evidence.md`](docs/product/claims-evidence.md) for
what this demo does and does not prove.

## v0.1 scope

Tracked in [`docs/architecture/HOW-EIF-WORKS.md`](docs/architecture/HOW-EIF-WORKS.md#roadmap)
and the public readiness checklist there. Non-goals for v0.1: hosted SaaS,
autonomous multi-agent runtime, proprietary cloud memory service, mandatory
code-graph or shell-compression dependency, universal token-savings claims.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). This project is not yet accepting
external contributions while the public/private extraction is in progress -
the file explains current status.

## Changelog

[`CHANGELOG.md`](CHANGELOG.md) - what each version added, and the known
limitations stated alongside rather than discovered later.

## License

[Apache License 2.0](LICENSE). Third-party Python dependencies and their
own licenses are listed in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
and [`sbom.cdx.json`](sbom.cdx.json); `core/policies/license-policy.json`
and `scripts/eif_check_licenses.py` enforce the policy on every CI run.

## FAQ

See [`docs/architecture/HOW-EIF-WORKS.md`](docs/architecture/HOW-EIF-WORKS.md#faq).
