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

1. **Authority before inference.** Vendor docs, verified code, and validated
   knowledge have an explicit hierarchy - the agent knows what to trust when
   sources disagree.
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
9. **Dogfooded governance.** This framework's own gates have found real
   defects in its own private production instance - see
   [Benchmarks](docs/benchmarks/).

## Five-minute quickstart

```bash
git clone https://github.com/mike-arbuzov365/engineering-intelligence-framework.git
cd engineering-intelligence-framework
# quickstart tooling (eifctl init / doctor / validate) is not built yet - see
# docs/architecture/HOW-EIF-WORKS.md and the v0.1 roadmap below.
```

A working `eifctl init` bootstrap and a synthetic demo workspace are tracked
in the [v0.1 scope](#v01-scope) below and are not available yet.

## Core concepts

| Concept | What it does | Where |
|---|---|---|
| Authority model | Resolves conflicts between sources of truth | [`core/ontology/authority-model.md`](core/ontology/authority-model.md) |
| Knowledge taxonomy | Classifies knowledge artifacts (fact, rule, decision, risk, ...) | [`core/ontology/knowledge-types.md`](core/ontology/knowledge-types.md) |
| Confidence levels | Marks how trustworthy a claim is | [`core/ontology/confidence-levels.md`](core/ontology/confidence-levels.md) |
| Status lifecycle | draft -> validated -> superseded -> deprecated | [`core/ontology/status-lifecycle.md`](core/ontology/status-lifecycle.md) |
| Full architecture | End-to-end explanation of how it all fits together | [`docs/architecture/HOW-EIF-WORKS.md`](docs/architecture/HOW-EIF-WORKS.md) |

## Supported agents

Adapter directories exist for Claude Code, Codex, Cursor, and Hermes
(`adapters/`); each is being ported and verified incrementally. See
[`adapters/README.md`](adapters/README.md) for current status per agent.

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
own documentation locale in `.eif/config.yaml`; a Ukrainian locale pack is
the first non-English target (`locales/uk/`). See
[`locales/README.md`](locales/README.md).

## Quality and safety model

- Source authority is explicit and hierarchical - vendor docs and verified
  code outrank inference and assumption.
- `OBSERVED` / `INFERRED` / `ASSUMED` evidence labels are never silently
  collapsed into unqualified claims.
- Compression (structural navigation, shell-output filtering) is required
  to preserve correctness before it is allowed to save tokens - see
  [`docs/benchmarks/`](docs/benchmarks/).
- CI gates are designed to actually block a non-compliant merge path, not
  just document a policy - see `scripts/` and `docs/guides/`.

## Benchmarks

A reproducible quality-per-token benchmark is planned and not yet published.
See [`docs/benchmarks/README.md`](docs/benchmarks/README.md) for the
methodology and current status.

## Demo

A synthetic `examples/demo-workspace/` is planned and not yet built - see
[v0.1 scope](#v01-scope).

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
