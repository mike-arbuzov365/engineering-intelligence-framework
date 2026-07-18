# Hermes adapter

Status: dynamic active-source resolver implemented and tested (77
acceptance checks in `scripts/tests/test_hermes_adapter.py`, including a
real, pinned-version proof against the actual installed Hermes threat
scanner), plus real runtime proof against the actual installed Hermes
Agent CLI (see "Runtime-validation status" below). Marked **experimental,
supported** - does not change EIF's v0.1 required-adapter set
(`core/policies/decisions.md` D-09; Claude Code and Cursor remain the only
required pair). `SOUL.md` is out of scope for this adapter - a separate
personality/identity mechanism (loaded from `HERMES_HOME` only, never the
working directory), unrelated to project context.

**This adapter supersedes closed, unmerged public PR #12.** That PR's own
implementation and its own "verified" evidence are not reused or treated
as historical fact - see "What PR #12 got wrong" below before relying on
anything from it.

## Verified evidence

| Field | Value |
|---|---|
| Product/version tested | Hermes Agent `0.18.2` (`2026.7.7.2`) - a **git install**, not a black-box wheel (local HEAD `6142203bd7`, upstream `d59b79fa`, +1 locally carried commit unrelated to context-file discovery) |
| Date tested | 2026-07-18 |
| Primary source read directly | `agent/prompt_builder.py`, `agent/subdirectory_hints.py`, `tools/threat_patterns.py`, `agent/system_prompt.py`, `agent/conversation_loop.py`, `hermes_constants.py`, `hermes_cli/config.py` - the actual installed Python source, not a secondary documentation page |
| Verification commands | `hermes prompt-size --json` (offline, no API call - reports byte/char-count breakdowns by prompt section, never raw content), `hermes config set` (isolated `HERMES_HOME`), `hermes --version` |

## What PR #12 got wrong (why this is a rebuild, not a port)

PR #12 was built entirely from a secondary documentation page and limited
empirical probing, never the installed Python source itself. Re-deriving
the contract from that source directly found several concrete errors:

- **No ancestor depth cap for the `.hermes.md`/`HERMES.md` startup tier.**
  PR #12 claimed "empirically confirmed up to 5 parent directories" and
  hardcoded a `ANCESTOR_WALK_MAX_DEPTH = 5` constant. The real
  `_find_hermes_md()` (`agent/prompt_builder.py`) walks unboundedly from
  cwd to the git root with no cap at all - confirmed against the real
  installed CLI at 7 levels deep (see "Runtime-validation status"). The
  "5 levels" figure belongs to a *completely different* mechanism -
  `agent/subdirectory_hints.py`'s `SubdirectoryHintTracker`, a progressive,
  tool-call-triggered hint loader with its own, genuinely-capped
  `_MAX_ANCESTOR_WALK = 5` - PR #12 conflated the two.
- **Lowercase `agents.md`/`claude.md` fallbacks exist** (checked after
  their uppercase counterparts, same directory) and were never modeled in
  PR #12's `entrypoint_candidates`.
- **`.cursorrules` + `.cursor/rules/*.mdc` is a real 4th tier** in
  Hermes's own first-match startup chain (reached when tiers 1-3 are all
  absent; every matching `.cursorrules`/`.mdc` file concatenated together) -
  PR #12 treated it only as a `governance_discovery` side-signal, never as
  something that could actually be Hermes's real active source.
- **The truncation model is nothing like Codex's.** The real algorithm
  (`_truncate_content`) is per-tier, independent, head(70%)+tail(20%)-
  preserving with the *middle* dropped and a marker inserted, character-
  counted (not bytes), with a default cap *dynamically scaled to the
  model's context window* (`_dynamic_context_file_max_chars`: floor
  20,000, ceiling 500,000) unless `context_file_max_chars` is explicitly
  configured - fundamentally different from Codex's combined-chain
  running-byte-budget-with-front-truncation model. PR #12 never modeled a
  truncation algorithm in enough detail to be right or wrong.
- **The cross-directory shadow risk PR #12 correctly identified was
  handled the wrong way**: "WARN but still write" (reusing Codex's own
  pre-correctness-round `discover_shadow_signals()`/always-shown-WARN
  design) - exactly the "no active-target ambiguity may degrade to a
  warn-and-write path" anti-pattern the Codex correctness round rejected.
  This adapter STOPs instead (see below).

## Startup discovery contract (verified live against the installed source)

Hermes builds its project-context section of the system prompt once, on
the **first turn of a new session** (`agent/conversation_loop.py`: "First
turn of a new session... build from scratch"; cached thereafter as
`agent._cached_system_prompt`, rebuilt on a compression event that
compares against the cache). `build_context_files_prompt()`
(`agent/prompt_builder.py`) checks exactly 4 tiers, first match wins
across tiers:

1. **`.hermes.md`, then `HERMES.md`** - `_find_hermes_md()`: the nearest
   directory from cwd up to (and including) the git root that contains
   either name, checked in that order. **No git root anywhere -> cwd
   only** (the source's own stated reason: walking parents with no git
   root "could pick up a `.hermes.md` planted in `/tmp`, `/home`, etc.").
   **No depth cap** - confirmed against the real installed CLI at 7
   levels deep.
2. **`AGENTS.md`, then `agents.md`** - instance root (cwd) only, no
   ancestor walk at all, not even to the git root.
3. **`CLAUDE.md`, then `claude.md`** - instance root only, same as
   `AGENTS.md`.
4. **`.cursorrules` and every immediate (non-recursive) `.cursor/rules/*.mdc`**,
   sorted by filename - instance root only. All matching files in this
   tier are concatenated together (not first-match *within* the tier);
   the tier as a whole is only reached when tiers 1-3 are all absent.

An existing-but-**empty** (whitespace-only) tier-1 file still terminates
`_find_hermes_md`'s *search* (it checks `.is_file()` only, never content -
it never walks past what it finds, even to a farther, non-empty ancestor),
but `_load_hermes_md()` then returns `""` for it, and the real
`or`-chained resolution falls through to tier 2. `resolve_hermes_active_source()`
(`scripts/eif_adapters.py`) mirrors this exactly - not "skip empty and
keep walking."

### Transformation pipeline (per tier, exact order)

- **Tier 1** (`.hermes.md`/`HERMES.md`): read -> `.strip()` -> strip YAML
  frontmatter (`_strip_yaml_frontmatter` - `---`-delimited, this tier
  only) -> security scan (see below) -> prepend `## <relpath>` heading ->
  head/tail truncate.
- **Tiers 2-3** (`AGENTS.md`/`CLAUDE.md` and their lowercase variants):
  read -> `.strip()` -> security scan -> prepend `## <name>` heading ->
  truncate. **No frontmatter stripping** - the real source never calls
  `_strip_yaml_frontmatter` for these tiers; content starting with `---`
  is injected as-is.
- **Tier 4** (`.cursorrules` + `*.mdc`): each component independently
  read -> `.strip()` -> security-scanned -> given its own heading ->
  concatenated -> the **combined** tier truncated **once**, at the end
  (not per component). No frontmatter stripping here either, even though
  real `.mdc` files normally have YAML frontmatter (`description`/
  `globs`/`alwaysApply`) - injected raw.

### Security scanning (`tools/threat_patterns.py`, scope=`"context"`)

Every loaded tier is regex-scanned for prompt-injection/promptware/
role-hijack patterns before truncation. A match replaces the **entire**
content with `[BLOCKED: <name> contained potential prompt injection
(...)]"` - not a partial redaction. EIF does not vendor this pattern
library (would drift silently from the pinned version, and duplicating a
third party's security-relevant logic is a real maintenance and
correctness risk). Instead:

- `scripts/eif_adapters.py`'s core simulator (`simulate_hermes_context()`)
  works without Hermes installed at all - it accepts an *optional* real
  scanner function and reports `scanner_checked=False` honestly when none
  is supplied (never a silently-assumed-safe result).
- `scripts/tests/test_hermes_adapter.py` imports and calls the **real**
  installed `scan_for_threats` function directly against EIF's *actual*
  generated EN and UK content, proving neither is ever blocked, plus one
  deliberately-unsafe synthetic control fixture proving the check can
  actually detect a real block (not just the absence of failure). When
  Hermes is not importable in the running environment, this is reported
  as an explicit `NOT VERIFIED` limitation and does not fail the rest of
  the suite - core EIF never hard-depends on Hermes being installed.
- Future Hermes-version drift in the pattern library is a real,
  documented runtime-evidence limitation, not something EIF can detect
  ahead of time without a pinned re-run.

### Size limit resolution

`_get_context_file_max_chars()`'s real resolution order: (1) explicit
`context_file_max_chars` in the user's own `config.yaml`; (2) a dynamic
cap scaled to the model's context window
(`context_length x 4 chars/token x 0.06`, floored at 20,000, ceilinged at
500,000); (3) the flat 20,000 floor. **No authless, machine-readable
command was found that exposes Hermes's live, currently-effective value**
for either key (`hermes config show` has no `--json` mode and does not
print `context_file_max_chars` at all when unset; `hermes prompt-size
--json` reports a `"model"` name string, not a token-count
`context_length`) - EIF does not invent this value from a model-name
lookup table. `adapter.options.hermes.context_file_max_chars`, when
configured, is used directly; otherwise EIF's own fallback is always the
conservative 20,000-char floor, never the dynamic value, and evidence is
labeled `default-fallback` accordingly (see `check_size_budget()`'s
`limit_source` field).

## Active-source resolution: the corrected contract

`resolve_hermes_active_source()` replaces `resolve_active_entrypoint()`
for this adapter only - Hermes's real precedence needs the tier-1
ancestor walk evaluated *before* tiers 2-4 are even considered at the
instance root, a shape the generic single-directory resolver cannot
express. Reuses the existing five-state vocabulary:

- **`ACTIVE_MANAGEABLE`** - a real, safely-writable target found at the
  instance root (any tier), or nothing exists anywhere and the greenfield
  default (`.hermes.md`) applies.
- **`SHADOWED`** - a non-empty `.hermes.md`/`HERMES.md` in a **parent**
  directory (not the instance root) is the real active source today, per
  Hermes's own nearest-wins ancestor walk. Creating a local `.hermes.md`
  would silently shadow it and change effective governance for the whole
  subtree - STOPs by default. Overridable only via an explicit, persisted
  `adapter.options.hermes.parent_context_action: override-with-local` -
  generic `adoption.mode: coexist` does **not** imply this.
- **`ACTIVE_UNMANAGEABLE`** - an active Cursor-tier source (`.cursorrules`
  or `.cursor/rules/*.mdc`, nothing higher-precedence present).
  Unconditional STOP: this format **is** Hermes's real active source
  today (active and valid on its own terms), but EIF cannot marker-merge
  it (YAML-frontmattered, per-file granularity, structurally unlike a
  flat markdown context file), and creating a `.hermes.md` here would
  *change* precedence rather than *adopt* what's already governing - no
  such semantic-override decision exists for this adapter yet.
- **`AMBIGUOUS`** - a higher-precedence candidate exists but could not be
  safely read as plain text. STOPs unconditionally, never silently
  skipped past.
- **`NOT_FOUND`** - nothing exists anywhere in the resolved precedence;
  the greenfield default applies.

## A real, pre-existing defect found and fixed while building this adapter

`CLAUDE.md` is both claude-code's own fixed entrypoint **and** one of
Hermes's tier-3 candidates - switching `claude-code -> hermes` when
nothing higher-precedence exists lands the OLD and NEW entrypoint on the
identical path. The transaction-staging code on `main` computed the "old
entrypoint, strip its EIF block" `.next` staging file at
`old_entry_path.with_name(old_entry_path.name + ".next")` **without
checking whether that path coincided with the new entrypoint's own
`.next` staging file** - when it did, both stages wrote to the literal
same file, the entrypoint stage's commit (a rename) consumed it, and the
old-entrypoint stage's own commit then found its staged file already
gone ("staged artifact missing"), rolling back the entire transaction.
This defect pre-dates this adapter (it lived in the generic adapter-
switching code, unexercised because no *merged* adapter's candidates
previously overlapped with claude-code's fixed entrypoint) and was
already found and fixed once, on closed PR #12's own branch - but that
fix never reached `main` because the PR itself was never merged. Fixed
here, at the source, in `eif_init.py`: when the old and new entrypoint
paths coincide, the old-entrypoint plan is neutralized entirely (the new
entrypoint's own marker-merge render, which reads the *current* file
content including the old EIF block, already fully subsumes the "strip
the old block" step - keeping both would not just collide on the staging
path, the old-entrypoint plan's own output is also substantively wrong in
this case, since it lacks the new block). Verified directly: scenario 3
in `scripts/tests/test_hermes_adapter.py`.

## Adapter switching

`claude-code <-> hermes` (scenarios 3/4) and every other pairing reuse the
same marker-merge switching machinery as Codex/Claude Code. Hermes and
Claude Code are both effectively marker-merge once an entrypoint is
resolved, so switching away strips the old EIF block but does not delete
the file unless nothing but whitespace remains once the block is gone.
Malformed markers on the OLD entrypoint STOP the entire run before any
file is written (scenario 5). Switching a dynamic-resolve adapter AWAY
reads the old adapter's actual entrypoint from the existing lock, not the
static greenfield default - the prior write may have gone to any of the
six candidate names.

## Doctor: active-source and size-budget drift

`eif_verify_runtime.py` recomputes `resolve_hermes_active_source()` fresh
against the instance's current disk state and config, exactly as it does
for Codex, and fails with a message distinguishing **FILE INTEGRITY**
(is the locked file itself still present and well-formed?) from **AGENT
CONSUMPTION** (would Hermes actually still read that file as the active
source today?). Because a *local* tier-1 `.hermes.md` always wins at the
instance root regardless of any parent (tier 1 checks the nearest
directory - the instance root itself - first), a parent gaining a new
`.hermes.md` *after* a tier-1-based generation is not itself a drift risk;
the genuinely meaningful case is a **lower** tier (e.g. a locked
`AGENTS.md`) later outranked by a **new, higher** tier appearing in a
parent directory - proven directly (scenario 33). Size-budget drift
(`check_size_budget_drift()`) recomputes `simulate_hermes_context()`
against the current on-disk content and the current configured limit
(scenario 34).

## Runtime-validation status

Everything is testable and tested without any authenticated Hermes
session: file generation, marker-merge preservation, adapter switching,
active-source resolution (all 4 tiers, parent-STOP, explicit override,
Cursor-tier STOP, empty-file fall-through, unreadable-candidate
`AMBIGUOUS`, unbounded ancestor walk, `.git`-as-file and `.git`-as-
directory root boundaries), size-budget enforcement (dynamic/explicit
limits, head/tail truncation, managed-block survival), the real installed
security scanner against EIF's actual generated content, and
`eif_verify_runtime.py` doctor drift detection - all in
`scripts/tests/test_hermes_adapter.py` (77/77) plus the unchanged
existing suites (no regressions - `run_all.py` still green).

**Beyond that**: the actual discovery/precedence/truncation mechanism was
executed against the real, currently-installed Hermes CLI (`0.18.2`) via
`hermes prompt-size --json`, from an isolated, freshly-created
`HERMES_HOME` (no personal configuration ever entered the captured
output, not even transiently) with the wheel built from this adapter's
own commit:

1. `eifctl init --adapter hermes` (installed wheel) against a disposable
   probe project, with a random unguessable token injected through a
   genuinely EIF-generated value (`--knowledge-root`) - confirmed present
   in the generated `.hermes.md`.
2. `hermes prompt-size --json`, run from a cwd **7 directory levels below**
   the probe project's root (no `.hermes.md` of its own anywhere in
   between) - the reported context section was non-zero, confirming the
   real CLI's ancestor walk has no depth cap, directly contradicting PR
   #12's "5 levels" claim.
3. `hermes config set context_file_max_chars 2000` (isolated `HERMES_HOME`,
   never touching a real config file) followed by `hermes prompt-size
   --json` from the probe root: the real CLI's own truncation warning
   ("Context file .hermes.md TRUNCATED: 4104 chars exceeds limit of
   2000") reported the **exact same source character count** (4104) that
   `simulate_hermes_context()` independently computed for the identical
   generated file at the identical limit - a precise, non-coincidental
   match, not merely a plausible one. The real CLI's post-truncation
   reported size (2248 chars) is consistent with the known 70%/20%
   head/tail-plus-marker-overhead model.

**No raw probe output was retained anywhere** - captures were inspected
only for the specific token/size facts above, never displayed or diffed
in full, and the isolated `HERMES_HOME` had no personal content to begin
with.

**Not independently verified**: Hermes Cloud/gateway/mobile surfaces (this
adapter targets the local CLI, the same surface Claude Code/Cursor/Codex
are evaluated against); whether a future Hermes version's threat-pattern
library would still pass EIF's generated content (see "Security scanning"
above - a documented, explicit limitation, not silently assumed stable).

## Re-verification

If the Hermes Agent version changes materially, re-run `hermes --version`
and re-read the installed source (not a cached copy or a documentation
page) before relying on the precedence/transformation/limit details
above - current as of `0.18.2` (`2026.7.7.2`) / 2026-07-18, not assumed
stable indefinitely.
