# How EIF works

<!-- Canonical source document. README, website copy, articles, diagrams,
FAQ, and launch posts should all derive from this file, not diverge from it. -->

**Status: v1 draft**, extracted and genericized from a private production
instance that has run this methodology daily since May 2026. Sections marked
"not built yet" describe the target design, not current working code.

## Table of contents

1. [Executive summary](#executive-summary)
2. [The problem EIF solves](#the-problem-eif-solves)
3. [Design principles](#design-principles)
4. [Framework vs. project instance](#framework-vs-project-instance)
5. [The three-tier context model](#the-three-tier-context-model)
6. [Authority model](#authority-model)
7. [Experience retrieval](#experience-retrieval)
8. [Session lifecycle](#session-lifecycle)
9. [Execution packets](#execution-packets)
10. [Knowledge Delta](#knowledge-delta)
11. [Skills and agent adapters](#skills-and-agent-adapters)
12. [Structural-graph integration](#structural-graph-integration)
13. [Shell-output compression integration](#shell-output-compression-integration)
14. [Vendor-documentation integration](#vendor-documentation-integration)
15. [Language configuration](#language-configuration)
16. [CI and quality gates](#ci-and-quality-gates)
17. [Privacy and security](#privacy-and-security)
18. [Degraded modes](#degraded-modes)
19. [Extension model](#extension-model)
20. [End-to-end example](#end-to-end-example)
21. [Metrics and benchmark methodology](#metrics-and-benchmark-methodology)
22. [Limitations](#limitations)
23. [Roadmap](#roadmap)
24. [Definition of Public-Ready](#definition-of-public-ready)
25. [FAQ](#faq)

## Executive summary

EIF is a control plane for AI-agent software development: it defines how
persistent knowledge, source authority, execution discipline, and optional
tooling integrations work together so that agentic work compounds instead
of resetting every session. It is not a memory product, not a code graph,
and not a token compressor - it is the governance layer that makes those
things (and the agents using them) trustworthy together.

## The problem EIF solves

Most agentic coding workflows have the same failure modes regardless of
which model or tool is driving them:

- Decisions made in one session live only in that session's chat history
  and vanish on compaction or when a new session starts.
- The agent re-investigates the same files and re-derives the same
  conclusions it already reached last week.
- A lesson learned locally (a fix that didn't work, a fragile file, a
  rejected approach) never resurfaces before the next agent repeats it.
- Raw command output floods the context window with no filtering, crowding
  out the actual reasoning budget.
- Architecture and scope decisions get mixed in with unverified assumptions,
  with no marker distinguishing them.
- A merged pull request gets treated as proof the feature works, without
  behavioral evidence.
- Token-efficiency rules, quality rules, and privacy rules are maintained
  separately and can silently contradict each other.

## Design principles

1. **Authority before inference.** See [Authority model](#authority-model).
2. **Experience retrieval before implementation.** Knowledge is actively
   pulled into context before new work starts, not just passively stored.
3. **Ephemeral and durable context are separated.** A session's working
   state is never mistaken for validated, durable knowledge.
4. **Execution is governed.** Scope, stop conditions, evidence, and
   closeout are first-class parts of the workflow.
5. **Quality wins over token savings.** Any compression layer (structural
   navigation, shell-output filtering) must never weaken verification,
   source hierarchy, or review - if it does, that's a bug in the
   compression layer, not an acceptable tradeoff.
6. **Tool-agnostic core.** The methodology is plain Markdown and works with
   any agent that can read files; specific coding agents (Claude Code,
   Codex, Cursor, Hermes, ...) are adapters on top, not the center.
7. **Optional integrations.** A structural code graph and a shell-output
   compression layer are capabilities you can add, not requirements to get
   started.
8. **Multilingual project documentation.** Framework documentation is
   English-canonical; a project instance can declare its own documentation
   locale without re-translating the whole methodology.
9. **Dogfooded governance.** The private instance this framework was
   extracted from runs its own gates against itself - see
   [Limitations](#limitations) for a concrete example of a gate finding a
   real defect in the system that built it.

## Framework vs. project instance

EIF ships as a **framework** (this repository): ontology, playbooks,
templates, skills, adapter definitions, and optional integration guides. A
**project instance** is a specific project (or workspace of projects) that
adopts the framework, adds its own project-specific knowledge, registry,
and configuration, and runs it day to day.

```text
engineering-intelligence-framework (public, versioned)
  |
  |  referenced from the project's persistent agent-instruction file
  v
your-project-instance (private)
  |
  |  contributes generalizable lessons back
  v
engineering-intelligence-framework (evolves)
```

A project instance should never need to fork the framework to use it -
project-specific content lives in the instance's own repository/registry,
declared via `.eif/config.yaml`, not by editing framework source in place.

## The three-tier context model

- **Tier 1 - framework / global methodology.** This repository. Rules,
  ontology, playbooks, templates, and skills that apply to any project
  instance, independent of tech stack.
- **Tier 2 - project instance.** A specific project or set of related
  projects. Project-specific knowledge cards, registry, ADRs, and
  configuration. References Tier 1 via the persistent agent-instruction
  file; contributes generalizable lessons back to Tier 1 via a Knowledge
  Delta and promotion decision.
- **Tier 3 - session.** Ephemeral, single-session working state (current
  task plan, in-progress reasoning, scratch files). Never treated as
  durable knowledge on its own - it either gets promoted into a Tier 2
  artifact through the Knowledge Delta process, or it's discarded when the
  session ends.

Mixing these tiers is the single most common failure mode this framework
exists to prevent: session-scoped assumptions leaking into project-level
"facts" without going through validation, or project-specific detail
leaking into what should be reusable, tech-stack-agnostic methodology.

## Authority model

See [`core/ontology/authority-model.md`](../../core/ontology/authority-model.md)
for the full hierarchy and application rules. Short version: vendor docs
outrank verified code, which outranks validated knowledge, which outranks
stakeholder-confirmed behavior, which outranks agreed scope, which outranks
chat memory/inference, which outranks nothing - inference is the weakest
source and must be labeled as such.

## Experience retrieval

Before starting non-trivial work, an agent operating under this framework
is expected to actively search existing knowledge for relevant prior
lessons, recurring failure patterns, and rejected approaches - not just
rely on whatever happens to already be in context. This is a deliberate
preflight step, not a hope that the agent remembers.

*(Not built yet in this repository: the retrieval tooling itself. The
private instance implements this as a lightweight ripgrep-based search over
a knowledge index, deliberately avoiding embeddings/vector search for a
structured, file-based knowledge base - see
[Limitations](#limitations) for why that tradeoff was made and when it
might not hold.)*

## Session lifecycle

A session has a beginning (preparation: read the persistent instructions,
check for relevant prior knowledge, confirm scope), a middle (controlled
execution against that scope, with explicit stop conditions for anything
outside it), and an end (closeout: record what changed, what was learned,
what's still open, and whether anything should be promoted from
session-scoped state into durable Tier 2 knowledge).

*(Playbook content not ported yet - see [`playbooks/README.md`](../../playbooks/README.md).)*

## Execution packets

For work larger than a single session, EIF uses execution packets: a
planning artifact set (charter, facts, decisions, roadmap) created before
implementation starts, executed across one or more sessions, and closed out
with an honest summary of what actually happened versus what was planned -
not a summary optimized to look complete.

A packet's closeout is expected to be independently reviewable: someone
other than the agent that did the work (or the same agent in a fresh
session) should be able to verify the claimed evidence against the actual
repository state (merged PRs, passing CI, working code) rather than trust
the closeout narrative at face value.

*(Templates not ported yet - see [`templates/README.md`](../../templates/README.md).)*

## Knowledge Delta

Every pull request that changes methodology, adds a rule, or records a
reusable lesson includes a Knowledge Delta section: what was added, what
changed, what's still unratified, and an explicit promotion decision (does
this belong in Tier 1, or does it stay Tier 2/project-specific). Purely
mechanical changes (typo fixes, formatting) use an explicit
`<!-- no-knowledge-delta: mechanical task -->` marker instead, so the
distinction between "no delta because nothing changed" and "delta omitted
by mistake" is never ambiguous.

## Skills and agent adapters

A **skill** is a reusable, invokable workflow (planning, execution, review,
knowledge curation, search) written once as plain Markdown instructions. An
**adapter** is what makes a specific coding agent aware of that skill and,
where the agent supports it, enforces conventions via hooks.

Adapters are not equally capable. As of this writing, hook-based
`updatedInput`/rewrite support varies significantly between agents and
agent versions - some silently ignore a hook's rewrite instruction and only
honor block/deny, some apply it reliably. **Do not assume hook enforcement
works until you've verified it end-to-end for your specific agent version**;
persistent, always-loaded instructions remain the fallback of record
precisely because hook enforcement cannot be assumed reliable across agents.
See [`adapters/README.md`](../../adapters/README.md).

## Structural-graph integration

Optional. Adds fast "what calls this," "what's the shortest relationship
between A and B," and impact-analysis queries over a project's codebase,
instead of the agent grepping and re-reading files from scratch every
session. Requires a build/refresh step and its own freshness tracking (a
graph built against an old commit is worse than no graph if the agent
trusts it blindly). See [`integrations/graphify/`](../../integrations/graphify/)
(not ported yet).

## Shell-output compression integration

Optional. Filters and summarizes shell command output before it enters the
agent's context, with per-command tracking of how much was actually saved.
The private instance measured this at 52-98% savings depending on the week
- driven almost entirely by whether one or two high-volume command classes
happened to be filtered correctly, not by steady overall efficiency. A
single unfiltered high-volume command (or a filter that silently returns
wrong results, e.g. a search pattern that gets corrupted by the filter and
returns zero matches instead of an error) can dominate or invalidate a
week's numbers. Any tool in this category needs the same failure-mode
discipline as the rest of the system: a filter that fails should fail
loudly, not silently produce plausible-looking wrong output. See
[`integrations/rtk/`](../../integrations/rtk/) (not ported yet).

## Vendor-documentation integration

Optional. Pulls current, versioned library/API/framework documentation into
context on demand, instead of relying on a model's training-data knowledge
of a library's API surface, which is frequently stale for fast-moving
libraries. See [`integrations/vendor-docs/`](../../integrations/vendor-docs/)
(not ported yet).

## Language configuration

Framework documentation (this repository) is English-canonical. A project
instance declares its own documentation locale in `.eif/config.yaml`
(see [`.eif/config.yaml.example`](../../.eif/config.yaml.example)); agents
operating under that instance write prose (Knowledge Delta notes, session
context, generated docs) in that locale while keeping framework
identifiers, schema keys, code, and command examples in English. See
[`locales/README.md`](../../locales/README.md).

## CI and quality gates

A gate that is only documented, and not technically enforced, is not a
gate. A pull request should not be mergeable through a supported path while
a mandatory check is failing - if your CI/hosting plan doesn't support
required-status-check enforcement natively, the merge path itself (not
just documentation) needs to check status before allowing a merge.

*(Concrete gate scripts not ported yet - see [`scripts/README.md`](../../scripts/README.md).)*

## Privacy and security

A framework repository must never contain private project names, real
paths from a specific machine, customer data, or credentials - genericized
examples only. A project instance keeps all of that in its own private
repository/registry, referenced from the framework via configuration, never
copied into it. See [`SECURITY.md`](../../SECURITY.md).

## Degraded modes

Every optional integration must have a documented, functional fallback:

- No structural graph -> the agent falls back to search/manual navigation.
  Slower and more token-hungry, not broken.
- No shell-output compression -> commands run unfiltered. More expensive
  per session, not broken.
- No vendor-doc retrieval -> the agent relies on training-data knowledge of
  a library, with the accuracy risk that implies for fast-moving APIs.

If removing an integration breaks the governance model itself (authority,
knowledge lifecycle, execution discipline), that integration was
mis-classified as optional and needs to move into `core/`.

## Extension model

New knowledge-artifact types, new locales, and new agent adapters are
additive: they extend the taxonomy/config surface without requiring changes
to unrelated parts of the framework. A project instance may add local
extensions (extra folders, extra frontmatter fields) as long as they're
documented in that instance's own configuration - see "Optional local
extensions" in
[`core/ontology/knowledge-types.md`](../../core/ontology/knowledge-types.md#optional-local-extensions).

## End-to-end example

*(Not built yet.)* Planned: a synthetic demo under
[`examples/demo-workspace/`](../../examples/README.md) walking through a
new task, experience retrieval, source authority, structural navigation (or
its degraded-mode fallback), controlled implementation, shell-output
compression (or its fallback), tests, a Knowledge Delta, a promotion
decision, and session cleanup - against synthetic code with no real project
data.

## Metrics and benchmark methodology

See [`docs/benchmarks/README.md`](../benchmarks/README.md). No benchmark has
been run yet; any token-savings number quoted before that benchmark exists
should be treated as unverified and non-representative of overall task
quality.

## Limitations

This section exists to be honest, not to sell. Concrete, dated findings
from the private production instance:

- **A documented blocking CI gate did not actually block a merge.** A pull
  request was merged seconds after a mandatory check reported failure,
  because the hosting plan in use didn't support required-status-check
  enforcement and the "gate" was policy-only, not technical. Fixed by
  routing all merges through a script that re-verifies check status,
  Knowledge Delta presence, and review state before merging, and by
  blocking the agent's direct merge command via hook. This is exactly the
  kind of gap this framework is meant to catch in itself.
- **A shell-output compression filter had a silent correctness bug**: a
  search-pattern filter corrupted a specific character on one platform and
  returned zero matches instead of an error, which is worse than a crash -
  an agent seeing zero matches concludes "this doesn't exist" rather than
  "something went wrong." Any filtering/compression layer needs active
  correctness testing, not just a token-savings measurement, or it will
  produce confident wrong answers.
- **Hook-based enforcement is not uniformly reliable across agents.** One
  agent's rewrite-hook output was measured as not being applied in roughly
  half of observed cases over several days, meaning the persistent,
  always-loaded instruction file - not the hook - was doing the actual
  enforcement work for that agent the whole time. Do not design a system
  that only works if hook enforcement is reliable; verify it, per agent,
  before relying on it.
- **A local automation hook silently failed for weeks** because a
  path-detection routine rejected valid paths containing a space or a
  short-name tilde, with no loud failure - it printed a warning easy to
  miss in ordinary use. Silent degradation of an integration is a design
  smell; prefer loud, specific failures.
- Retrieval currently uses a structured, ripgrep-based search rather than
  embeddings/vector search, on the reasoning that a small, well-organized
  knowledge base is often cheaper and more predictable to search this way.
  This has not been benchmarked against a vector-search alternative and may
  not hold as the knowledge base grows.
- No independent, multi-project benchmark has validated the framework's
  actual effect on task success, rework rate, or total cost - only
  component-level, single-instance measurements exist so far.

## Roadmap

See the [public readiness backlog](#definition-of-public-ready) below.
High-level sequence: public/private security audit -> legal foundation
(license, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, GOVERNANCE - done for
v0.1 skeleton) -> real gate enforcement ported -> generic bootstrap
(`eifctl init`/`doctor`/`validate`) -> core ontology/playbooks/templates/
skills ported and genericized -> demo workspace -> reproducible benchmark
-> `v0.1.0` release -> website and launch content.

## Definition of Public-Ready

Mirrors the checklist ratified before this repository's creation.

### Brand
- [x] Full name ratified: "Engineering Intelligence Framework".
- [x] Descriptor ratified: "A quality-first control plane for governed
      AI-agent software development."
- [x] Repository slug selected: `engineering-intelligence-framework`.
- [x] Preliminary name-collision search performed (no exact GitHub/PyPI/npm
      match found) - **not** a trademark clearance.
- [ ] Domain/social strategy documented.

### Public/private boundary
- [x] Public core repository created, physically separate from the private
      instance.
- [ ] Current tree of the private instance fully audited for
      public/private classification (a preliminary scan found private
      repository names, absolute machine paths, and owner identifiers
      spread across 100+ tracked files and dozens of commits in the
      private instance - full remediation not done).
- [ ] Git history of anything migrated is audited (none migrated yet -
      this repository started with clean history by design).
- [ ] No private paths, customer data, internal telemetry, or raw
      structural-graph artifacts present (spot-checked in ported files so
      far; not exhaustively verified).
- [ ] Synthetic demo replaces private examples.

### Legal and community
- [x] Open-source license added (Apache-2.0).
- [ ] Third-party licenses audited.
- [x] CONTRIBUTING added.
- [x] CODE_OF_CONDUCT added.
- [x] SECURITY added.
- [x] GOVERNANCE added.

### Product
- [ ] `.eif/config.yaml` schema finalized (example exists, not validated by
      tooling yet).
- [x] English canonical docs exist for the ontology core.
- [ ] A non-English locale works end to end.
- [ ] Generic bootstrap (`eifctl init`) works without any private
      repository.
- [ ] At least two agent adapters tested against this repository.
- [x] Structural-graph and shell-compression integrations documented as
      optional.
- [x] Degraded mode documented.

### Quality
- [ ] Mandatory CI checks actually block the merge path (documented
      pattern from the private instance; not yet wired up here).
- [ ] Graph freshness derived from commit evidence (pattern exists in the
      private instance; not ported here).
- [ ] Generated adapters have drift checks.
- [ ] Persistent agent-instruction files here are kept compact (this is a
      stated design principle from day one of this repository, not
      retrofitted).
- [ ] Demo workflow has executable evidence.
- [ ] Benchmark measures quality together with tokens.

### Documentation
- [x] This document exists and is the canonical source for README/website/
      FAQ content.
- [ ] README explains EIF in 2-3 minutes (draft exists, not user-tested).
- [ ] Quickstart completes in 10 minutes (not possible yet - bootstrap
      tooling doesn't exist).
- [ ] FAQ covers memory/RAG/structural-graph/shell-compression/privacy/
      overhead questions (see [FAQ](#faq) below - partial).
- [x] Limitations are explicit (see [Limitations](#limitations)).
- [ ] Public roadmap published outside this document.

### Launch
- [ ] `v0.1.0` tag exists.
- [ ] Website is live.
- [ ] Article published.
- [ ] Launch sequence prepared.
- [ ] Feedback/issue intake ready.

## FAQ

**Is this just another memory/RAG system?**
No. Memory/RAG retrieves relevant text; EIF additionally defines an
authority hierarchy for conflicting sources, a lifecycle for knowledge
artifacts (draft -> validated -> superseded -> deprecated), and a
governed execution workflow around how that knowledge gets used and
updated. Retrieval is one component, not the whole system.

**Is a code graph required?**
No. It's an optional integration for structural navigation and impact
analysis. Without it, an agent falls back to search/manual navigation -
slower, not broken. See [Degraded modes](#degraded-modes).

**Is shell-output compression required?**
No, same as above - optional, with a documented fallback (commands run
unfiltered, which is more expensive but functionally correct).

**Does EIF send my private code anywhere?**
No. EIF is documentation, templates, and scripts that run in your own
environment against your own repositories. It doesn't introduce a hosted
service, telemetry backend, or cloud memory store. Read the actual scripts
before trusting this answer for your threat model.

**What's the overhead of adopting this?**
Not yet measured end to end - see
[Metrics and benchmark methodology](#metrics-and-benchmark-methodology).
Expect nonzero setup and maintenance cost; this document will be updated
with real numbers once the benchmark exists.

**Can I write my project documentation in a language other than English?**
Yes, that's a first-class design goal - see
[Language configuration](#language-configuration). Framework-level
documentation and identifiers stay English; your project's generated
documentation follows your configured locale.

**How production-ready is this?**
Pre-v0.1. The methodology has run daily in a private instance since May
2026, but this public extraction is new and incomplete - see
[Definition of Public-Ready](#definition-of-public-ready) for exactly
what's missing.
