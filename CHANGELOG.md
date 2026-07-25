# Changelog

Notable changes to the Engineering Intelligence Framework.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is [semantic](https://semver.org/), with the caveat that
**anything marked experimental below may change shape within 0.x** - see
[`core/policies/decisions.md`](core/policies/decisions.md) for which
decisions are ratified rather than provisional.

This file follows the same evidence rule as the rest of the repository: a
capability is listed under Added only if it is runnable, not if it is
designed. Anything verified within bounds says so, and the bounds are part
of the entry rather than a footnote.

## [Unreleased]

Nothing since the v0.1.0 preparation entry below.

## [0.1.0] - unreleased

First public extraction from a private production instance that has run
this methodology daily since May 2026. The repository is functional and
reviewable; it is not a stable release, and the checklist that would make
it one lives in
[Definition of Public-Ready](docs/architecture/HOW-EIF-WORKS.md#definition-of-public-ready).

### Added

**Methodology core**

- Four-axis authority model (normative, empirical, agent-execution,
  knowledge-lifecycle) replacing a single ranked source hierarchy. A
  normative source disagreeing with an empirical one is recorded as a
  discrepancy, not resolved by rank.
- Knowledge taxonomy, confidence levels, and a status lifecycle
  (`draft` -> `validated` -> `superseded`/`deprecated`, plus `rejected`
  for hypotheses only) with append-only retraction.
- Three-tier context model: reusable framework method, durable project
  knowledge, ephemeral session state, with Knowledge Delta governing
  promotion between them.
- Two-loop learning model: an inner per-session loop, and an outer
  [retro loop](playbooks/run-retro.md) that asks what repeats across many
  sessions. Promotion is driven by the outer loop, because one session
  cannot establish that its lesson generalizes.
- Bounded Evidence Loop contract: named evaluator, iteration and
  remote-run budgets, failure signatures, and `PASS`/`BLOCKED`/`DEFERRED`
  exits.

**Operating layer**

- 12 playbooks, 14 templates, 8 invokable skills covering session
  preparation/execution/closeout, execution-packet planning/execution/
  review, knowledge search/ingest/lint, the bounded evidence loop, and
  retro.
- Execution packets: a canonical artifact set for work spanning more than
  one session, carrying charter, facts, decisions and roadmap across
  sessions so later ones do not reopen settled questions.

**Tooling**

- Installable `eifctl` package with 7 subcommands (`init`, `doctor`,
  `search`, `render`, `privacy-scan`, `validate`, `version`), verified
  from a built wheel in a clean virtual environment whose path contains a
  space and non-ASCII text. **Not published to PyPI.**
- Instance bootstrap and upgrade with real provenance, a sha256-hashed
  runtime bundle, and transactional rollback proven by fault injection
  after each commit stage and partway through individual writes.
- Instance self-verification (`eif_verify_runtime.py`): config/lock schema
  validity, per-file bundle hashes, adapter/config consistency, marker
  integrity, and drift between config and the generated entrypoint.
- Adoption onto an existing, already-governed repository: a preflight that
  stops before any write when there is no coexistence decision on record,
  a `coexist` mode that defers to existing rules, configurable knowledge
  paths with path-escape validation, and finding-specific privacy-scan
  suppressions.
- Offline, Unicode-aware, lifecycle-aware knowledge retrieval that reports
  unparseable, schema-invalid and not-found as three distinct outcomes
  rather than collapsing them into "no results".

**Adapters** (scope frozen at four)

- Claude Code and Cursor as the two required v0.1 adapters (D-09).
- Codex and Hermes as experimental-supported, each re-verified against
  that agent's own primary or installed source rather than a
  documentation page, with real installed-CLI runtime proof from isolated
  home directories.
- All 12 directed switching pairs proven, with exactly one active EIF
  block and project content preserved after every switch.

**Optional integrations** (none required; each degrades to a named core path)

- RTK shell-output compression: version/argv/native-search/diff canaries,
  a command registry, and content-free local telemetry. A failed required
  canary reports `degraded`; raw proxy routes record zero savings.
- Graphify structural graph: query/path/explain canaries and an artifact
  lifecycle bound to source commit, graph digest, repository identity and
  reviewed scope. Only `fresh` reports healthy.
- Vendor docs: declares Context7 over MCP, with generated routing guidance
  and a reviewable per-adapter config template.

**Governance and safety**

- Privacy scanner, frontmatter/config/lock validation, link checking, and
  Knowledge Delta classification, each with its own test suite and each
  runnable from a project instance's own bundle.
- Controlled merge entrypoint that re-verifies checks, Knowledge Delta and
  review state twice before merging, pinned to a verified head SHA.
- Public claims-evidence ledger recording, per claim, what is `OBSERVED`
  vs `UNVERIFIED` and the exact wording each claim does and does not
  permit.
- Issue templates that require the command and real output rather than a
  recollection, including an evidence-report template for contributing
  verification of anything the repository lists as unverified.

**Localization**

- English-canonical framework docs with a per-instance documentation
  locale. Ukrainian is the first locale pack: status messages, Knowledge
  Delta, closeout headings and knowledge retrieval.

**Presentation**

- Bilingual site source in [`site/`](site/README.md), locally buildable,
  gated on claim citations, byte budgets, two browser engines, axe and
  Lighthouse. **Not deployed.**

### Known limitations

Stated here rather than left to be discovered:

- **Not on PyPI.** No `pip install` from a package index.
- **No quality or rework claim.** No comparative study has been run.
- **Benchmark is one bounded pilot**: one model, three of ten fixtures,
  one attempt per A/B cell, six attempts total. Modes C/D have executable
  integrity contracts but no real-agent result. This cannot support a
  directional efficiency claim.
- **CI is not technically blocking.** Checks are "required by policy";
  branch protection and required status checks are not configured at the
  repository-settings level, and no adapter ships a hook guard against a
  direct merge.
- **Cursor runtime consumption is unconfirmed.** The generated rule file is
  code/test-validated, but no human has verified that Cursor's agent
  actually reflects its content - see
  `examples/demo-cursor-workspace/MANUAL-RUNTIME-CHECK.md`.
- **Vendor-docs is not probed.** EIF generates configuration for an agent
  to load and does not itself speak MCP, so transport reachability is
  reported by the agent and marked unverified in the manifest.
- **EIF installs nothing at the user level.** Not a limitation so much as a
  deliberate boundary: MCP servers and agent hooks are configured outside
  the project instance, and this framework never mutates user-level
  configuration.
- **Existing-governance detection is a heuristic**, a content-length check
  rather than semantic understanding, and can both over- and under-trigger.
- **Retrieval is keyword-based**, not semantic, and is untested against a
  realistically large knowledge base.
- **Adoption is proven against one real target.** A second, different real
  repository has not been exercised.
- **Localization covers project surfaces**, not an agent's own free-form
  responses.

### Explicit non-goals for 0.1

Hosted SaaS, an autonomous multi-agent runtime, a proprietary cloud memory
service, a mandatory code-graph or shell-compression dependency, and any
universal token-savings claim.

[Unreleased]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases/tag/v0.1.0
