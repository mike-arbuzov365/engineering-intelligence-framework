# How EIF works

<!-- Canonical source document. README, website copy, articles, diagrams,
FAQ, and launch posts should all derive from this file, not diverge from it. -->

**Status: pre-v0.1, first full draft** (revised across two independent
review passes, both 2026-07-15 - see
[`core/policies/decisions.md`](../../core/policies/decisions.md) for what
that review changed). Extracted and genericized from a private production
instance that has run this methodology daily since May 2026. Sections
marked "not built yet" describe target design, not current working code -
see the [Current capability table in README.md](../../README.md#current-capability)
for the authoritative status of every piece.

## Table of contents

1. [Executive summary](#executive-summary)
2. [The problem EIF solves](#the-problem-eif-solves)
3. [Design principles](#design-principles)
4. [Framework vs. project instance](#framework-vs-project-instance)
5. [The three-tier context model](#the-three-tier-context-model)
6. [Authority model](#authority-model)
7. [Experience retrieval](#experience-retrieval)
8. [Session lifecycle](#session-lifecycle)
9. [Bounded evidence loops](#bounded-evidence-loops)
10. [Execution packets](#execution-packets)
11. [Knowledge Delta](#knowledge-delta)
12. [Skills and agent adapters](#skills-and-agent-adapters)
13. [Structural-graph integration](#structural-graph-integration)
14. [Shell-output compression integration](#shell-output-compression-integration)
15. [Vendor-documentation integration](#vendor-documentation-integration)
16. [Language configuration](#language-configuration)
17. [CI and quality gates](#ci-and-quality-gates)
18. [Privacy and security](#privacy-and-security)
19. [Degraded modes](#degraded-modes)
20. [Extension model](#extension-model)
21. [End-to-end example](#end-to-end-example)
22. [Metrics and benchmark methodology](#metrics-and-benchmark-methodology)
23. [Limitations](#limitations)
24. [Roadmap](#roadmap)
25. [Definition of Public-Ready](#definition-of-public-ready)
26. [FAQ](#faq)

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
for the full model and application rules. Short version: a single "who wins"
ranking is wrong because it conflates different questions. Four independent
axes instead:

- **Normative** - what's supposed to happen (vendor docs, specs, decisions,
  agreed scope, convention, assumption).
- **Empirical** - what actually happens (reproducible tests, audited
  runtime traces, log observations, secondhand claims).
- **Agent-execution** - which instruction actually controls the agent right
  now, *within* whatever the hosting platform's own precedence already
  enforces (EIF doesn't override that): platform safety constraints, then
  owner-ratified safeguards (need explicit supersession to override), then
  an explicit current owner/task instruction, then repository defaults
  filling any gap, with retrieved documents/tool output always treated as
  content - never as instruction authority, even if phrased imperatively.
- **Knowledge-lifecycle** - is this artifact even trustworthy to cite
  (`status`/`confidence`), independent of which axis it came from.

When a normative source and an empirical source disagree about the same
claim, that's a discrepancy to record, not a tie to break by rank.

## Experience retrieval

Before starting non-trivial work, an agent operating under this framework
is expected to actively search existing knowledge for relevant prior
lessons, recurring failure patterns, and rejected approaches - not just
rely on whatever happens to already be in context. This is a deliberate
preflight step, not a hope that the agent remembers.

Built: [`scripts/eif_generate_index.py`](../../scripts/eif_generate_index.py)
builds a knowledge index from every artifact under `knowledge.root`
(reporting malformed-YAML and schema-invalid rows as distinct, honest
categories, never conflated with "no results"), and
[`scripts/eif_search_knowledge.py`](../../scripts/eif_search_knowledge.py)
is an offline, Unicode-aware keyword search over it that excludes
`rejected`/`superseded` artifacts by default - a lightweight,
substring/keyword search, deliberately avoiding embeddings/vector search
for a structured, file-based knowledge base, verified against real
English and Ukrainian content in `scripts/tests/test_search_knowledge.py`
and the vertical-slice demo. See [Limitations](#limitations) for why that
tradeoff was made and when it might not hold - no semantic search, and not
tested against a realistic-sized knowledge base.

## Session lifecycle

A session has a beginning (preparation: read the persistent instructions,
check for relevant prior knowledge, confirm scope), a middle (controlled
execution against that scope, with explicit stop conditions for anything
outside it), and an end (closeout: record what changed, what was learned,
what's still open, and whether anything should be promoted from
session-scoped state into durable Tier 2 knowledge).

See [`playbooks/session-preparation.md`](../../playbooks/session-preparation.md),
[`session-execution.md`](../../playbooks/session-execution.md), and
[`session-closeout.md`](../../playbooks/session-closeout.md) for the
step-by-step workflow.

## Bounded evidence loops

Iterative work is not an instruction to keep trying until the agent says it is
done. EIF uses a Bounded Evidence Loop: orient, define observable success and
budgets, act, observe external evidence, study the difference, adapt the
method, then stop as `PASS`, `BLOCKED`, or `DEFERRED`.

Every autonomous loop names a real evaluator, `max_iterations`, a
`remote_run_budget` (0 unless explicitly authorized), and stop conditions.
The same unchanged failure signature cannot be retried indefinitely, hosted CI
is not used as a debugger when a local evaluator exists, and a completion
phrase is never behavioral proof. Interrupted state lives in a gitignored
Tier 3 checkpoint; only validated facts and reusable learning move through
Knowledge Delta.

The procedure is
[`playbooks/bounded-evidence-loop.md`](../../playbooks/bounded-evidence-loop.md),
the contract is
[`templates/bounded-evidence-loop.md`](../../templates/bounded-evidence-loop.md),
and the primary-source research and rejected patterns are documented in
[`docs/research/bounded-evidence-loops.md`](../research/bounded-evidence-loops.md).

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

See [`playbooks/execution-packet-planning.md`](../../playbooks/execution-packet-planning.md)
for the planning workflow and `templates/packet-*.md` for the charter,
facts, decisions, roadmap, self-review, start, and closeout templates it
uses. The task-scope, Knowledge Delta, and session-closeout templates
used by a single-session task are a separate, simpler path - see
[`templates/README.md`](../../templates/README.md).

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

Optional. Adds "what calls this," relationship-path, explanation and impact
navigation over a project's codebase. It requires a separate build/restore
step and commit-derived freshness tracking; graph output is navigation
evidence and every material claim still has to be verified against source.

The experimental Graphify adapter probes a candidate-compatible version,
runs `query`, `path`, and `explain` against a three-node synthetic graph, checks
the project-local artifact boundary and classifies freshness as `fresh`,
`stale`, `diverged`, or `unknown` from Git evidence. Only `fresh` plus passing
canaries can be `healthy`. Semantic/deep modes remain external and fail closed
unless provider, data boundary and cost cap are explicit; doctor never starts
a provider scan. This is behavioral integration evidence, not evidence that a
graph makes engineering work faster or better. See
[`integrations/graphify/`](../../integrations/graphify/).

## Shell-output compression integration

Optional. Filters and summarizes shell command output before it enters the
agent's context, with content-free per-command accounting. Output reduction is
eligible for measurement only after the exact route preserves argv and result
semantics. A single unfiltered high-volume command, or a filter that silently
returns a plausible but wrong empty result, can invalidate an aggregate. Any
tool in this category therefore needs the same failure-mode discipline as the
rest of the system: correctness precedes reduction, and a failed route must be
reported rather than converted into a savings claim.

The optional RTK adapter now checks a compatible version, CLI routes, raw-proxy
argv preservation, grep alternation, git diff and the strict content-free
telemetry contract. Doctor reports `healthy` only when all required canaries
pass. `degraded` keeps core EIF available but makes the failed command class
ineligible for savings claims. Raw proxy and parse-failure routes always count
as zero savings. The framework generates project-local guidance but never
installs hooks or changes user-level configuration. See
[`integrations/rtk/`](../../integrations/rtk/).

## Vendor-documentation integration

Optional. Pulls current, versioned library/API/framework documentation into
context on demand, instead of relying on a model's training-data knowledge
of a library's API surface, which is frequently stale for fast-moving
libraries. The generic external-provider declaration exists; provider-specific
retrieval and health behavior is not ported or tested yet. See
[`integrations/vendor-docs/`](../../integrations/vendor-docs/).

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

Built: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) runs
exactly one hosted job per PR (D-14, 2026-07-19): the critical-path
[`scripts/tests/smoke.py`](../../scripts/tests/smoke.py) suite, privacy
scanning, frontmatter/config/lock schema validation, link checking, a
YAML/JSON-Schema self-consistency check, and Knowledge Delta completeness
(fetched from the live PR body, not the frozen trigger payload). Push to
`main` triggers no workflow at all - a merged PR was already fully
validated by this job. The full runtime test suite
(`scripts/tests/run_all.py`, 28 suites) and the cross-platform package-
build/license-check matrices run on a manual release gate
([`.github/workflows/release-check.yml`](../../.github/workflows/release-check.yml),
`workflow_dispatch`-only) or locally at no Actions cost - see
[`scripts/README.md`](../../scripts/README.md) for what each gate script
does. A controlled merge entrypoint
([`scripts/eif_merge_pr.py`](../../scripts/eif_merge_pr.py)) re-verifies
checks, Knowledge Delta, and review state before merging, pinned to the
verified head SHA. What's *not* done: none of this is the only path to
merge yet - required-status-checks/branch-protection are not configured
at the repository-settings level, and no agent-hook guard blocks a direct
`gh pr merge` (none of the four adapters that exist - Claude Code, Cursor,
Codex, Hermes - ships hook scripts) - see [Limitations](#limitations) and
the [Public-Ready checklist](#definition-of-public-ready).

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

Built: [`examples/demo-workspace/`](../../examples/README.md) is a real,
materialized EIF instance against a synthetic leap-year calculator -
initialize the instance, seed and search real knowledge (experience
retrieval), scope and implement one real change informed by that
retrieval (controlled implementation), verify it with a real
failing-before/passing-after test, write a Knowledge Delta and close out
truthfully, in Ukrainian. Reproduced from a clean checkout with captured
command output - see [`examples/demo-workspace/README.md`](../../examples/demo-workspace/README.md)
and [`docs/product/claims-evidence.md`](../product/claims-evidence.md) for
exactly what this does and does not prove. Not included: structural-graph
and shell-output-compression navigation (both optional integrations,
explicitly excluded from this slice - see
[Optional integrations](../../README.md#optional-integrations)), a second
scenario, and a second adapter.

## Metrics and benchmark methodology

See [`docs/benchmarks/README.md`](../benchmarks/README.md). A first bounded
real-agent pilot exists (2026-07-20): one model, three of ten fixtures, one
attempt per mode, six attempts total, 100% task success. Real, provider-
reported token counts are published alongside it, but n=1 per (task, mode)
cell does not support a general efficiency claim - any "N% token savings"
figure not tied to that specific, bounded result should still be treated as
unverified and non-representative of overall task quality.

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
- **A documented rollback procedure did not by itself account for a
  generated artifact living outside the directory it names.** The
  adoption-hardening round's own end-to-end test proved this the hard
  way: "delete `.eif/`, restore `CLAUDE.md`/`.gitignore`" is not a
  complete rollback once a knowledge index has been generated at a
  configured path outside `.eif/` (the common case for an adopted, not
  greenfield, repository) - the generated `index.md` was left behind
  until the test's own assertion caught it. Fixed in the test; the same
  correction belongs in any hand-followed rollback instructions, not just
  code.
- **Existing-project "governance detected" is a heuristic, not semantic
  understanding.** The adoption preflight (`scripts/eif_preflight.py`)
  decides whether to require an explicit `--adoption-mode` by checking
  whether the existing entrypoint file has more than a small amount of
  content and no EIF markers yet - a content-*presence* check, not a
  content-*meaning* check. It can both over-trigger (a long file that
  isn't actually governance) and under-trigger (real but terse governance
  under the length threshold). Documented as a known limitation rather
  than presented as understanding what the text says. This governance
  heuristic is decoupled from the repository's historical origin:
  `migration_status` is derived by a *separate* read-only check for any
  project-owned file outside `.git/` and `.eif/` (see
  [`instance-contract.md#repository-origin`](instance-contract.md#repository-origin)),
  so an existing code repo with no `CLAUDE.md` is still recorded `adopted`;
  the heuristic's over/under-triggering affects only the coexistence STOP
  decision, never the recorded origin.
- **The first version of this repository's own ontology had the exact
  failure mode it warns against**: a single linear "vendor docs always
  outrank logs" authority ranking that conflated normative claims with
  empirical ones, an evidence-lifecycle metadata enum that had drifted out
  of sync with its own prose (missing `rejected`), and a confidence-level
  description that read as permission to skip verification - the thing
  [`confidence-levels.md`](../../core/ontology/confidence-levels.md)
  now explicitly warns against. Caught and fixed in an independent review
  pass on 2026-07-15, not by the same reasoning that produced the
  original. If a public methodology framework needs a second, independent
  pass to catch inconsistencies in its own core ontology, assume the same
  is true of whatever you build on top of it - review it, don't just
  trust that authoring the thing means it's internally consistent.

## Roadmap

See the [public readiness backlog](#definition-of-public-ready) below.
High-level sequence, updated after the 2026-07-18 adapter/license round:

1. ~~Public/private security audit~~ -> ~~legal foundation~~ -> ~~ontology
   consistency, machine-readable schemas, decision ledger, self-governance
   CI~~ (done).
2. ~~Build the [vertical slice](../guides/vertical-slice.md): one
   synthetic demo, one adapter (Claude Code), end to end~~ (done) ->
   ~~existing-repository adoption hardening (preflight, coexistence mode,
   configurable knowledge paths, privacy-scan suppression baseline),
   driven directly by a real throwaway-copy pilot against a private
   Tier-2 repository~~ (done - see [Limitations](#limitations) for what
   the pilot found and what remains a heuristic, not a solved problem).
3. ~~Repeat the slice against a second adapter (Cursor) to prove the
   framework/adapter boundary holds~~ (done) -> ~~two further,
   experimental-supported (not required) adapters, Codex and Hermes,
   each re-verified against its own primary/installed source rather than
   documentation, with real installed-CLI runtime proof from an isolated
   home directory~~ (done) -> ~~a full directed switching matrix across
   all four adapters (12 ordered pairs)~~ (done) -> **adapter scope is
   now frozen at these four** - no fifth adapter, no hooks-parity
   rewrite, no new adapter abstraction. See
   [`docs/product/claims-evidence.md`](../product/claims-evidence.md)
   for exactly what is and is not verified per adapter.
4. ~~Reproducible dependency/license checking~~ (done - default mode now
   reads a committed SBOM instead of scanning whatever the invoking
   interpreter happens to have installed, confirmed identical on Windows
   and Ubuntu CI - see `scripts/eif_check_licenses.py`).
5. Real merge-gate/CI enforcement wired up in repository settings, not just
   present as workflow files (open).
6. ~~Reproducible quality-per-token benchmark, run against the vertical
   slice~~ (first bounded pilot done - one model, three of ten fixtures,
   one attempt per mode, 2026-07-20, see
   [`docs/benchmarks/README.md`](../benchmarks/README.md); the remaining
   seven fixtures, additional models, and repeated trials for a real
   confidence interval remain open).
7. ~~Port a bounded v0.1 operating set of playbooks/templates/skills,
   including the Bounded Evidence Loop~~ (done). Curator/retro/customer and
   other broader workflows remain post-v0.1 scope.
8. ~~Add optional RTK and Graphify behavioral adapters with explicit degraded
   modes~~ (done). Vendor-docs remains declaration-only.
9. Final local release gate + refreshed fresh-history candidate -> owner-gated
   `v0.1.0`/package publication -> website implementation and community launch.

## Definition of Public-Ready

The authoritative status of every decision behind this checklist lives in
[`core/policies/decisions.md`](../../core/policies/decisions.md) - do not
treat a checked box below as "ratified" unless that file says so; several
items below are checked because they're *done*, not because they were
formally ratified (the file is explicit about which is which).

### Brand
- [x] Full name **ratified**: "Engineering Intelligence Framework" (D-01).
- [x] Descriptor adopted, **provisional** (D-02).
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
- [x] Synthetic demo replaces private examples: the only content under
      `examples/` is `demo-workspace/`, a synthetic leap-year calculator
      with no real project data.

### Legal and community
- [x] Open-source license added (Apache-2.0).
- [x] Third-party licenses audited: direct/transitive dependencies checked
      against [`core/policies/license-policy.json`](../../core/policies/license-policy.json)
      (see [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md)); a real
      GPL-3.0-or-later transitive dependency (`rfc3987`) was found and
      remediated via a drop-in MIT-licensed swap (`jsonschema[format-nongpl]`),
      not a legal exception. The check itself is now reproducible: default
      mode reads the committed SBOM (`sbom.cdx.json`), not a live scan of
      the invoking environment, confirmed identical on Windows and Ubuntu
      CI - see `scripts/eif_check_licenses.py`.
- [x] CONTRIBUTING added.
- [x] CODE_OF_CONDUCT added.
- [x] SECURITY added.
- [x] GOVERNANCE added.

### Product
- [x] `.eif/config.yaml` machine-readable schema implemented and exercised
      ([`core/schemas/eif-config.schema.json`](../../core/schemas/eif-config.schema.json));
      `eifctl init` writes it, `eifctl validate` validates it, and doctor
      checks config/lock/runtime consistency.
- [x] English canonical docs exist for the ontology core.
- [x] A non-English locale works end to end, **partially**: Ukrainian
      status messages, Knowledge Delta, closeout headings, and knowledge
      retrieval are verified (`locales/uk/`,
      `scripts/tests/test_locale.py`, `test_journey.py`); full
      agent-response localization and `terminology.yaml` are not covered.
- [x] An **experimental** bootstrap (`eif_init.py`) works without any
      private repository - proven against a temp-directory instance and a
      disposable copy of a private repository (adoption pilot). A real,
      installable package (`eifctl`, `pyproject.toml` at the repo root) now
      exists - a built wheel, installed into a clean venv with a
      space-and-Unicode path, running every subcommand end to end
      (`scripts/tests/test_package_build.py`); the Windows+Ubuntu x Python
      3.11/3.12 CI package-build matrix confirmed green on all 4
      combinations, twice, so **D-05/D-08 are now Ratified** - see
      `core/policies/decisions.md`.
- [x] Existing-repository adoption does not silently override pre-existing
      project governance: an adoption preflight detects it and stops
      before any write when there is no adoption decision on record,
      keyed off the resolved/persisted adoption basis (a persisted
      `coexist` decision authorizes safe continuation on a later flagless
      run rather than STOPping); a `coexist` mode generates a block that
      defers to existing rules instead of claiming sole authority;
      knowledge paths are user-configured and validated against path
      escape (absolute, drive/UNC, `..` traversal, outside-instance) and
      shell metacharacters, with generated commands quoting the
      configured path; the historical `migration_status` is derived from a
      separate read-only repository-origin check (any project-owned file
      outside `.git/`/`.eif/`), so an existing repo with **no `CLAUDE.md`**
      is still recorded `adopted`, an unreadable origin fails closed, and it
      can never contradict `adoption.mode`; an existing knowledge-index file
      without EIF's own ownership marker is never overwritten;
      privacy-scan suppressions identify one exact finding (rule + path +
      content fingerprint), never a whole rule+file, and the scanner fails
      loudly on an existing but empty/malformed suppression config instead
      of treating it as suppression-free; an existing but broken
      `.eif/config.yaml` stops before any write rather than being treated
      as absent. Tested against a realistic sanitized fixture
      (`scripts/tests/test_adoption.py`, 67 checks) AND re-validated by
      rerunning the full pilot against fresh disposable copies of one real
      private pilot target each round (private planning packet); the
      live repository is never opened for writing, and this is still only
      one real target - a second, different one is not yet exercised.
- [x] At least two agent adapters tested against this repository, **exceeded,
      still partial on runtime validation**: four adapters now exist and are
      each code/test-validated - Claude Code (`CLAUDE.md`, marker-merge),
      Cursor (`.cursor/rules/eif/governance.mdc`, full-regen,
      nested-entrypoint transaction - `scripts/tests/test_cursor_adapter.py`,
      74 checks), Codex (dynamic active-entrypoint resolution, re-verified
      against primary source - `test_codex_adapter.py`, 123 checks), and
      Hermes (dynamic active-source resolution across a real four-tier
      discovery chain, verified against installed source -
      `test_hermes_adapter.py`, 77 checks). All 12 directed switching pairs
      across the four are proven (`test_adapter_switch_matrix.py`, 81
      checks; `adapters/switch-matrix.json`). Codex and Hermes had real
      installed-CLI runtime proof from an isolated home directory
      (`codex debug prompt-input`, `hermes prompt-size --json`) - Cursor
      does NOT yet have this: no human has confirmed a real Cursor
      Agent-chat response reflects the generated rule's content - see
      `adapters/cursor/README.md#runtime-validation-status` and
      `examples/demo-cursor-workspace/MANUAL-RUNTIME-CHECK.md`. D-09
      ratifies which two adapters (Claude Code, Cursor) are *required* for
      v0.1 scope; Codex and Hermes are experimental-supported, not required
      - none of this is a claim that all four are production-ready, or that
      runtime validation is complete for all four.
- [x] Structural-graph and shell-compression integrations are optional,
      behaviorally checked adapters. Graphify has bounded
      query/path/explain and Git-freshness canaries; RTK has version/argv/
      grep/diff canaries, a command registry and content-free telemetry.
      Provider/version coverage is bounded and neither adapter supports a
      general performance claim.
- [x] Degraded mode documented.

### Quality
- [x] CI runs on every PR (one hosted job, D-14): privacy scan,
      frontmatter/config schema validation (real `jsonschema`
      Draft202012Validator, not a hand-rolled parser), link check,
      YAML/JSON Schema syntax check, Knowledge Delta completeness
      (three-way meaningful/mechanical/empty classification, not a bare
      heading check), and the critical-path `scripts/tests/smoke.py`
      suite - see [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).
      Every script's own full test suite (positive + negative fixtures,
      28 suites; exact check count is run evidence, not a fixed contract)
      runs on the manual release gate
      ([`.github/workflows/release-check.yml`](../../.github/workflows/release-check.yml))
      or locally, not on every routine PR - moved there under D-14 to
      keep routine PR cost to one job, not removed.
- [x] A controlled merge entrypoint exists
      ([`scripts/eif_merge_pr.py`](../../scripts/eif_merge_pr.py),
      genericized from the private instance's proven `merge-pr.ps1`
      pattern) that re-verifies checks, Knowledge Delta, and review state
      TWICE (once for evidence, once immediately pre-merge, re-derived not
      re-read), paginates review threads, and merges pinned to the verified
      head SHA. Live-used for real merges, not only `--dry-run` (PR #4 and
      this repository's other merged PRs).
- [ ] Those CI checks and the merge-gate script are not yet the *only*
      path to merge - nothing at the repository-settings level (required
      status checks / branch protection) or the agent-hook level (none of
      the four adapters that exist - Claude Code, Cursor, Codex, Hermes -
      ships hook scripts, so there is no "deny direct `gh pr merge`" guard)
      technically prevents bypassing them. Checks are labeled "required by
      policy," not "blocking," for exactly this reason. This is the same
      gap the private instance found and fixed in itself (see Limitations)
      - do not consider this item done until it's closed the same way
      (repository settings + a hook guard for each adapter).
- [x] Graph freshness is derived from graph baseline, current commit and
      merge-base evidence, with explicit `fresh`, `stale`, `diverged` and
      `unknown` states (`scripts/tests/test_graphify_integration.py`).
- [x] Generated adapters have a machine-readable parity matrix
      (`adapters/parity-matrix.json`, drift-tested by
      `scripts/tests/test_parity_matrix.py` against the live adapter
      registry) covering all four adapters across entrypoint/init/upgrade/
      reconfigure/coexist/doctor/rollback/switching/runtime-evidence, plus a
      separate directed switching matrix (`adapters/switch-matrix.json`,
      `test_adapter_switch_matrix.py`) covering all 12 ordered pairs - the
      two matrices answer different questions (per-adapter capability vs.
      per-pair switching behavior) on purpose, cross-referenced rather than
      merged. `eif_verify_runtime.py` catches config-vs-lock adapter
      mismatches and config-vs-generated-block drift for whichever adapter
      is configured. Not covered: drift in an adapter's *own* behavior
      across its product versions (e.g. Cursor or Claude Code changing how
      they read the entrypoint) - each adapter's README documents the
      version it was verified against and says to re-verify on a material
      version change, but nothing re-runs that check automatically.
- [x] Persistent agent-instruction file (`AGENTS.md`) is compact - a
      stated design principle from day one, not retrofitted.
- [x] Demo workflow has executable evidence:
      `scripts/tests/test_journey.py` (259 checks) drives a real subprocess
      journey against a fresh instance, and
      [`examples/demo-workspace/README.md`](../../examples/demo-workspace/README.md)
      has real captured command output, both reproducible from a clean
      checkout - see
      [`docs/guides/vertical-slice.md`](../guides/vertical-slice.md).
- [x] Benchmark measures quality together with tokens - one bounded real-
      agent pilot run (2026-07-20): 100% task success in both modes,
      real provider-reported token counts, n=1 per cell (not a
      statistically powered claim) - see
      [`docs/benchmarks/README.md`](../benchmarks/README.md).

### Documentation
- [x] This document exists and is the canonical source for README/website/
      FAQ content.
- [ ] README explains EIF in 2-3 minutes (corrected this round to fix
      stale adapter-count claims; still not independently timed by a
      human reading it for the first time).
- [ ] Quickstart completes in 10 minutes: [`docs/guides/quickstart.md`](../guides/quickstart.md)
      now exists as a dedicated entry point. Mechanical execution of the
      full underlying command sequence (init, retrieval, test, both
      renders, all five validation checks) was measured end to end at
      **6.3-7.0 seconds across three runs** - real data, not a guess -
      but that is tool execution time, not the human reading/typing/
      comprehension time a "10-minute quickstart" claim is actually
      about, which remains untimed by an independent human.
- [x] FAQ covers memory/RAG/structural-graph/shell-compression/privacy/
      overhead/adapter-support/tests-and-CI questions (see [FAQ](#faq)
      below) - not claimed exhaustive, but no longer partial on the five
      originally-named topics plus two more added this round.
- [x] Limitations are explicit (see [Limitations](#limitations)).
- [x] Public roadmap published outside this document:
      [`ROADMAP.md`](../../ROADMAP.md) at the repository root.

### Launch
- [ ] `v0.1.0` tag exists.
- [ ] Website is live.
- [ ] Article published.
- [ ] Launch sequence prepared.
- [ ] Feedback/issue intake ready.

## FAQ

**Is this just another memory/RAG system?**
No. Memory/RAG retrieves relevant text; EIF additionally defines a
multi-axis authority model for conflicting sources, a lifecycle for knowledge
artifacts (draft -> validated -> superseded -> deprecated), and a
governed execution workflow around how that knowledge gets used and
updated. Retrieval is one component, not the whole system.

**Is a code graph required?**
No. It's an optional integration for structural navigation and impact
analysis. Without it, an agent falls back to source search/manual navigation;
core EIF remains available, but no graph-level path or impact hint exists.
See [Degraded modes](#degraded-modes).

**Is shell-output compression required?**
No, same as above - optional, with a documented fallback (commands run
unfiltered and no RTK reduction is recorded).

**Why can Graphify or RTK be `degraded` even when it is installed?**
Installation proves reachability, not behavior. EIF probes the installed
version and runs provider-specific canaries. A stale Graphify artifact or a
failed RTK argv/search route stays explicit and ineligible for a healthy or
savings claim; doctor reports the evidence and core EIF uses its documented
fallback.

**What do the RTK and Graphify canaries prove?**
They prove bounded compatibility, behavior, failure reporting and
fallback contracts. The first real-agent benchmark pilot has one attempt per
cell and does not include modes C/D, so no directional performance conclusion
is supported. See [`docs/product/claims-evidence.md`](../product/claims-evidence.md).

**Does EIF send my private code anywhere?**
Core EIF, RTK accounting and structural Graphify mode are designed for local
processing and do not introduce an EIF-hosted telemetry or memory service.
Optional provider slots can declare `external-api`; Graphify semantic/deep mode
is refused unless that external boundary, provider and a positive cost cap are
explicit. Check the configured provider's actual behavior and privacy terms;
a declared boundary is not a substitute for reviewing the tool used in your
threat model.

**Can EIF be adopted into an existing repository that already has its own
agent rules?**
Yes, that is the specific scenario the adoption-hardening round targeted,
driven by a real pilot against a private repository. `eif_init.py` runs a
preflight before writing anything: if your entrypoint file (e.g.
`CLAUDE.md`) already has real content and you have not set an explicit
`adoption.mode`, it stops rather than silently appending a second,
competing authority statement. Passing `--adoption-mode coexist`
generates a block that explicitly defers to your existing rules instead
of claiming to be the project's sole authority, and reads knowledge paths
from your config instead of assuming a root `knowledge/` directory. See
[Limitations](#limitations) for what this preflight is - a content-
presence heuristic - and is not - semantic understanding of your existing
rules.

**What's the overhead of adopting this?**
Not yet measured end to end. The one real-agent benchmark pilot that
exists (see
[Metrics and benchmark methodology](#metrics-and-benchmark-methodology))
measures task-fixing quality and tokens against small synthetic fixtures,
not the ongoing setup/maintenance cost of adopting EIF into a real
project - that specific question remains open. Expect nonzero setup and
maintenance cost; this document will be updated with real numbers once
that's measured.

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

**What coding agents does this support?**
Four adapters exist and adapter scope is frozen at this set: Claude Code
and Cursor are the two required v0.1 adapters; Codex and Hermes are
experimental-supported, not required. All four generate the correct
entrypoint for their agent and have been re-verified against that agent's
own primary or installed source, not just documentation - see
[Skills and agent adapters](#skills-and-agent-adapters) and
[`docs/product/claims-evidence.md`](../product/claims-evidence.md) for
exactly what's verified per adapter. "Supports agent X" here means an
entrypoint is generated and code/test-validated, not that hook-based
enforcement or every agent version has been checked - see
[Limitations](#limitations).

**Does EIF replace my tests, CI, or code review?**
No - see [What EIF is not](../../README.md#what-eif-is-not). It adds a
knowledge/authority layer and a governed workflow around implementation
and evidence; the actual verification (tests passing, CI green, a human
or agent reviewing the diff) still has to happen, the same way it would
without EIF. A merged PR is explicitly not treated as proof of working
behavior on its own - see [Knowledge Delta](#knowledge-delta).
