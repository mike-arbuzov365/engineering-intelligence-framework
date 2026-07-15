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

## The problem

AI coding agents are powerful, but most agentic workflows still treat chat
history as engineering memory:

- Previous decisions live only in a conversation that gets compacted or lost.
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
3. **Ephemeral and durable context are separated.** Session-scoped state is
   never mistaken for validated, durable knowledge.
4. **Execution is governed.** Scope, stop conditions, evidence, and closeout
   are part of the workflow, not an afterthought.
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
| Machine-readable schemas + real validator | **Available** | [`core/schemas/`](core/schemas/) validated with `jsonschema`'s `Draft202012Validator` + format checking via [`scripts/eif_validate_frontmatter.py`](scripts/eif_validate_frontmatter.py); 15 positive/negative fixtures, all passing. Not wrapped in a bootstrap CLI (`eifctl validate`) yet - invoke the script directly, or via `scripts/eif_init.py` for a new instance's config. |
| Governance docs (LICENSE, CONTRIBUTING, SECURITY, ...) | **Available** | repo root |
| Privacy scan / frontmatter+config+lock validation / link check / Knowledge Delta check | **Available** | [`scripts/`](scripts/), each with its own test suite, run in CI on every PR; the first four also run from a project instance's own bundle, not just the framework repo - see [`docs/architecture/instance-contract.md#validation-surface`](docs/architecture/instance-contract.md#validation-surface) |
| Decision ledger | **Available** | [`core/policies/decisions.md`](core/policies/decisions.md) |
| `.eif/config.yaml` schema | **Available (schema + validator)**, no bootstrap CLI | validated the same way as frontmatter - see above; `eif_init.py` generates one with real provenance |
| Vertical-slice plan | **Built (experimental)** | [`docs/guides/vertical-slice.md`](docs/guides/vertical-slice.md) (design) + [`examples/demo-workspace/`](examples/demo-workspace/) (the actual, reproduced slice - see its README) |
| Controlled merge entrypoint | **Available**, not wired into repo settings or a hook guard | [`scripts/eif_merge_pr.py`](scripts/eif_merge_pr.py) - dry-run tested against this repo's real PR #1 |
| Bootstrap script (`eif_init.py`) | **Experimental** | [`scripts/eif_init.py`](scripts/eif_init.py) - initializes a **separately-runnable** instance: real dirty-checked framework provenance, a hashed `.eif/runtime/` source bundle, a CLAUDE.md entrypoint via a marker-safe merge (refuses to write, rather than corrupt, malformed `BEGIN`/`END` markers). Every managed artifact - config (when written), runtime bundle, lock, entrypoint, `.gitignore` - commits as one ordered transaction, with proven rollback of every already-committed stage if a later one fails. Mode (init / routine upgrade / explicit `--force` reconfigure) is decided by what's already on disk: a routine upgrade derives project/adapter/locale/migration-status from the existing config and lock instead of CLI defaults, and never touches `.eif/config.yaml`. See [`docs/architecture/instance-contract.md`](docs/architecture/instance-contract.md). Does not ratify a CLI name/packaging (D-05/D-08 open) |
| Instance self-verification (`eif_verify_runtime.py`) | **Available (experimental)** | [`scripts/eif_verify_runtime.py`](scripts/eif_verify_runtime.py) - bundled "doctor" command: config/lock schema validity, manifest digest self-consistency, per-file bundle hash verification, missing/unexpected-file classification, config/adapter/lock/entrypoint consistency, provenance (dirty/asserted) notes, and `CLAUDE.md`/`.gitignore` marker integrity - all from the instance's own bundle, no framework checkout needed |
| Instance contract / upgrade / adoption | **Available (experimental)** | [`docs/architecture/instance-contract.md`](docs/architecture/instance-contract.md) - provenance, upgrade-by-re-init, and safe adoption of an existing repo (the basis for the eventual private-instance migration) |
| Knowledge index / lifecycle + schema-aware retrieval | **Available (experimental)** | [`scripts/eif_generate_index.py`](scripts/eif_generate_index.py), [`scripts/eif_search_knowledge.py`](scripts/eif_search_knowledge.py) - offline, Unicode-aware keyword search that returns only eligible statuses by default (excludes rejected/superseded), and reports three honest outcomes for anything wrong: unparseable YAML, schema-invalid (parses fine, violates the ontology), or status-ineligible - never conflated with "no results." No embeddings; not tested at scale |
| Locale layer (Ukrainian project docs + retrieval) | **Available (experimental)**, 4 surfaces | [`locales/`](locales/), [`scripts/eif_locale.py`](scripts/eif_locale.py), [`scripts/eif_render.py`](scripts/eif_render.py) - status messages, Knowledge Delta, closeout headings, and Ukrainian knowledge retrieval, with a real render command and English fallback; not full agent-response localization; D-06/D-07 remain open |
| Playbooks, templates, skills | **Partial** | 4 templates built ([`templates/`](templates/)) - task-scope, Knowledge Delta, session closeout, agent instructions. No playbooks or skills ported yet |
| Agent adapters | **1 of N (Claude Code), entrypoint generated** | [`adapters/claude-code/README.md`](adapters/claude-code/README.md) - `eif_init` generates the correct `CLAUDE.md` entrypoint (the file Claude Code loads, per official docs + CLI `2.1.169`); instruction/skill discovery verified live; hooks not re-verified this round; no hook scripts shipped. See [`adapters/README.md`](adapters/README.md) |
| Structural-graph / shell-compression / vendor-docs integrations | **Not built** | optional either way, see [`integrations/README.md`](integrations/README.md) |
| Demo workspace | **Built** | [`examples/demo-workspace/`](examples/demo-workspace/) - reproduced from a clean checkout, see its own README for captured command output |
| Benchmark | **Not run** | see [`docs/benchmarks/README.md`](docs/benchmarks/README.md) |
| Public claims evidence ledger | **Available** | [`docs/product/claims-evidence.md`](docs/product/claims-evidence.md) - what's OBSERVED vs. UNVERIFIED vs. NOT TESTED, and the allowed/forbidden wording for each |

**Experimental quickstart.** Cloning this repository gets you the ontology,
schemas, governance docs, CI, and one reproduced vertical slice - not a
stable CLI or a representative sample of real engineering tasks. Follow
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

## Planned agent adapters

No adapter is ported yet. See
[`adapters/README.md`](adapters/README.md#recommended-v01-priority) for an
evidence-based (not yet ratified) priority order.

## Optional integrations

EIF does not require any of these - it works in a degraded mode without
them, with explicit tradeoffs documented in
[`integrations/README.md`](integrations/README.md):

- **Structural code graph** - broad codebase/architecture navigation and
  impact analysis (`integrations/graphify/`).
- **Shell-output compression** - token-efficient command output filtering
  with tracked savings (`integrations/rtk/`).
- **Vendor documentation retrieval** - current, versioned library/API docs
  instead of stale training data (`integrations/vendor-docs/`).

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

A reproducible quality-per-token benchmark is planned and not yet published.
See [`docs/benchmarks/README.md`](docs/benchmarks/README.md) for the
methodology and current status.

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

## License

[Apache License 2.0](LICENSE).

## FAQ

See [`docs/architecture/HOW-EIF-WORKS.md`](docs/architecture/HOW-EIF-WORKS.md#faq).
