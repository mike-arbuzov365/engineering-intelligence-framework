# Codex adapter

Status: entrypoint generated and tested (100 acceptance checks in
`scripts/tests/test_codex_adapter.py`), plus real, unauthenticated runtime
proof against the actual installed Codex CLI (see "Runtime-validation
status" below) - stronger evidence than a code-only adapter, since the
discovery mechanism itself was executed, not just documented.

**Active-entrypoint correctness round (2026-07-17)**: this adapter's
first version had a real defect, found and fixed before merge - see
"Active-entrypoint resolution: what changed and why" below before relying
on anything in the superseded first-pass description of the shadow risk.

**Post-merge correctness round (2026-07-18)**: an independent review of
the merged adapter (`d8bc9b1`) found two further P1 defects in project-doc
*discovery* and *size-budget* semantics, both confirmed against Codex's
own primary Rust source (not the secondary documentation page the first
two rounds relied on) and fixed before this round's own merge - see
"Project-root discovery and the size budget: what changed and why" below.
The "Configured fallback filenames and the size budget" section elsewhere
in this document, and any scenario numbers below 24g, describe the
**pre-2026-07-18** behavior and are kept only as history; do not rely on
the whole-file-skip or git-root-only claims in them.

"Codex" here means the Codex CLI / Codex Cloud / ChatGPT desktop app
product family - OpenAI's own framing (`ChatGPT Codex is OpenAI's coding
agent across the ChatGPT desktop app on macOS and Windows, CLI, IDE
integrations, mobile Remote Control, and Cloud`), not a separate product
per surface. This adapter is marked **experimental, supported** - it does
not change EIF's v0.1 required-adapter set (Claude Code and Cursor remain
the only required pair; see `core/policies/decisions.md`).

## Verified evidence

| Field | Value |
|---|---|
| Product/version tested | Codex CLI `0.144.5` (installed locally via `npm install -g @openai/codex`, `codex --version`) |
| Date tested | 2026-07-17 |
| Verification commands | `codex --version`, `codex debug prompt-input` (real runtime proof, no authentication required) |
| Documentation source | `developers.openai.com/codex/guides/agents-md` (redirects to `learn.chatgpt.com/docs/agent-configuration/agents-md`), cross-checked against `github.com/openai/codex` |

## Entrypoint discovery contract (verified live, not from memory)

Codex builds an instruction chain at the start of every run (once per
launched session in the TUI):

1. **Global scope**: in `$CODEX_HOME` (default `~/.codex`), reads
   `AGENTS.override.md` if it exists, else `AGENTS.md`. Only the first
   non-empty file loads. This is the user's own personal, cross-project
   configuration - **EIF never reads, writes, or depends on it**, same
   boundary as Claude Code's own `~/.claude/CLAUDE.md`.
2. **Project scope**: Codex finds the **nearest ancestor directory
   (starting from cwd) that contains at least one configured
   `project_root_markers` entry** (default `[".git"]`; an explicitly
   configured empty list disables ancestor search entirely - cwd is
   inspected alone). **If no marker is found anywhere in the ancestry,
   Codex does not walk to the filesystem root and read what it finds
   there - it inspects only cwd.** From that resolved root down to cwd,
   each directory is checked (in order) for `AGENTS.override.md`, then
   `AGENTS.md`, then any configured fallback filename
   (`project_doc_fallback_filenames`). At most one file per directory.
3. **Concatenation with a truncating budget**: files are processed
   root-to-cwd against a single running `remaining` byte counter seeded
   from `project_doc_max_bytes` (default 32 KiB). Each file is included
   up to `min(file_size, remaining)` bytes - **a file that would exceed
   what's left is truncated mid-content, not skipped whole** - and
   `remaining` is decremented by however much of it was actually
   included. Processing stops once `remaining` reaches zero. A file whose
   decoded text is empty after this is not counted against the budget at
   all.

This adapter's entrypoint is a **project-scope** file at the instance
root, `entry_ownership=shared` - but which file that actually is depends
on what's already there: `entry_strategy=dynamic-resolve`
(`scripts/eif_adapters.py`), the same axis Hermes will use, resolved by
`resolve_active_entrypoint()` (see below) rather than a single fixed
name. Marker-merge safety still applies to whichever file is resolved -
project-owned content outside the `EIF:BEGIN`/`EIF:END` markers is always
preserved byte-for-byte. It is always a **flat file**, not a nested
dedicated path like Cursor's `.mdc` - there are no parent directories to
create or roll back.

### Active-entrypoint resolution: what changed and why

Verified **empirically**, not just read from documentation: a disposable
probe project (a fresh git repo with a root `AGENTS.md` containing a
random unguessable marker string) was queried via `codex debug
prompt-input` (renders the exact model-visible prompt input as JSON,
without needing to authenticate or spend a real model call). With only
`AGENTS.md` present, its content appeared in the merged chain as
expected. Adding an `AGENTS.override.md` in the **same directory** and
re-running the identical command made the base file's content **vanish
from the merged chain entirely** - not merged, not appended, not
present in any form.

**The first version of this adapter handled that fact wrong.** It always
targeted `AGENTS.md`, and treated a same-directory `AGENTS.override.md`
as a same-directory "shadow signal" - an always-shown WARN, independent
of adoption mode, while still writing `AGENTS.md` anyway. That write was
real but pointless: Codex would never read it while the override file was
present, and nothing forced anyone to notice the warning. A
correctness-pass review (2026-07-17) rejected this as a silent
"warn-and-write-a-dead-file" pattern and required a real fix before this
PR could merge.

**The fix**: `scripts/eif_adapters.py` now models Codex's own
per-directory precedence directly as `entry_strategy="dynamic-resolve"`
with `entrypoint_candidates=["AGENTS.override.md", "AGENTS.md"]` (plus any
configured fallback filenames - see below), the exact same mechanism
`resolve_active_entrypoint()` provides generically. A generic, five-state
result replaces the old ad hoc shadow-signal warning:

- `ACTIVE_MANAGEABLE` - a real, safely-writable target was found (or
  nothing exists yet). For Codex this covers both "only `AGENTS.md`
  exists" AND "`AGENTS.override.md` exists" - **when the override file is
  present, it IS the active target: EIF marker-merges into
  `AGENTS.override.md` itself, never into a now-dead `AGENTS.md`
  alongside it.** `discover_governance_surfaces()` excludes every one of
  this adapter's own candidate filenames from the generic "other
  governance" report - a shadowed sibling candidate is not double-
  reported there; it is named directly in the resolution's own rationale
  message instead (`scripts/tests/test_codex_adapter.py` scenarios 9/10).
- `ACTIVE_UNMANAGEABLE` / `SHADOWED` - not reachable for Codex today (no
  non-Markdown mechanism competes with `AGENTS.md`-shaped files, and
  Codex's own root-to-cwd **concatenation** - confirmed live, see below -
  means an ancestor directory's file never hides EIF's own instance-root
  write the way a first-match-wins adapter's would). Still part of the
  returned vocabulary: this is adapter-generic infrastructure, and Hermes
  (first-match-wins, real cross-directory shadow risk) will exercise both.
- `AMBIGUOUS` - a higher-precedence candidate exists but could not be
  safely read as plain text (e.g. invalid UTF-8) - STOPs unconditionally,
  never silently skipped past in favor of a lower-precedence candidate
  (scenario 21).
- `NOT_FOUND` - nothing exists yet; the greenfield default (`AGENTS.md`)
  applies.

Any state other than `ACTIVE_MANAGEABLE`/`NOT_FOUND` now STOPs before any
write - "no active-target ambiguity may degrade to a warn-and-write path"
is enforced as code, not just a comment.

A nested subdirectory's own `AGENTS.md` or `AGENTS.override.md` (below
the instance root, not sitting next to EIF's own entrypoint) is a
genuinely different case - it is part of Codex's own chain the same way
the root file is, so it is reported via the ordinary "other governance
surface" OK/WARN/STOP channel like any other adapter's sibling files
(scenarios 11/12), not the active-entrypoint-resolution one.

Also verified in the same probe: a nested subdirectory's own `AGENTS.md`
is appended **after** the root file's content when the working directory
is inside that subdirectory (root-first, closest-to-cwd-last, exactly as
documented) - confirming the discovery order, not just its existence, and
the reason `SHADOWED` is not reachable here (concatenation, not
first-match, so an ancestor's content is never hidden - only additional).

**Raw probe output was not committed or reproduced anywhere.** The
`codex debug prompt-input` command dumps the *entire* merged prompt,
which on the machine this was verified from also included that
operator's own real, personal global `~/.codex/AGENTS.md` content
(unrelated project workflow notes). Only the structural facts above -
never that content - are recorded here or in any commit.

### Project-root discovery and the size budget: what changed and why (2026-07-18)

An independent post-merge review flagged that the first-pass description
of both project-root discovery and the size budget had never been
checked against Codex's own **primary source** (`github.com/openai/codex`,
`codex-rs/core/src/agents_md.rs` and the `project_root_markers`/`find_up`
support crates) - only against the secondary documentation page. Pinned
against commit `3a067484584861606ad842de5bc4ac735a865ddf`, two real
defects were found in this adapter's own simulation of that contract:

1. **Root discovery walked to the filesystem root when no marker
   existed.** The first-pass `_codex_ancestor_chain_bytes()` only
   short-circuited when the instance root itself contained `.git`; with
   no `.git` anywhere in the ancestry, it kept walking upward and would
   have read (and budgeted against) arbitrary parent directories'
   `AGENTS.md` files all the way to the OS filesystem root - content no
   real Codex run would ever load, since Codex's own resolver falls back
   to **cwd alone** once the walk exhausts itself without finding a
   marker. Fixed by `_find_codex_project_root()` /
   `_codex_search_dirs()`, which return `[instance_root]` alone (no
   ancestor reads at all) in that case - proven directly by scenario 24g
   (a 40000-byte decoy parent `AGENTS.md` with no marker anywhere is
   never read).
2. **The size budget was modeled as whole-file skip, not truncation.**
   Codex's real `read_agents_md()` processes the root-to-cwd chain
   against a single running `remaining` byte counter and **truncates a
   file mid-content** when it would exceed what's left - it does not skip
   the file whole. The first-pass `SizeBudgetCheck` assumed whole-file
   inclusion/exclusion only (sourced from an AI-paraphrased secondary doc
   page, not the source itself), which meant a limit that actually
   truncated only a file's trailing, project-owned content (never
   reaching EIF's own managed block) was reported as a hard STOP it
   should not have been. Fixed by the `simulate_codex_budget()` /
   `CodexDocEntry` per-file simulator, which computes exact
   included/truncated byte counts per file and derives `fits` from
   **whether the EIF-managed block itself survives** (`EIF:BEGIN` through
   `EIF:END`, both boundaries checked independently) - not whether the
   whole file fits. A truncated trailing footer is not a failure;
   scenario 23b proves this explicitly.

Root markers are now first-class, configurable state, modeled with the
same `adapter.options.codex.*` shape as fallback filenames (see below):
`project_root_markers` (default `[".git"]`), validated through the same
runtime path-policy check as every other configured filename (absolute
paths and `..`-traversal STOP before any write - scenario 24k), recorded
in the lock as `adapter.effective_root_markers` so `eif_verify_runtime.py`
can detect configuration drift the same way it already detected entrypoint
drift (scenario 26c). Scenarios 24g-24n cover: no marker anywhere (24g),
a custom non-`.git` marker (24h), an explicitly empty marker list
disabling detection (24i), nearest-ancestor-wins when two real roots are
nested (24j), path-policy STOPs (24k), a `.git` **file** (the real shape
of a git-worktree child) honored the same as a directory (24l), an empty
`.git` **directory** honored the same way - presence-only, not
content-based (24m), and a multi-entry marker list matching on its second
entry (24n).

### Configured fallback filenames and the size budget

Codex's own `~/.codex/config.toml` supports three keys this adapter's
correctness now depends on getting right - `project_doc_fallback_filenames`
and `project_doc_max_bytes` re-verified live 2026-07-17 against
`learn.chatgpt.com/docs/agent-configuration/agents-md`, `project_root_markers`
and the corrected `project_doc_max_bytes` truncation model verified
2026-07-18 against the primary Rust source (see above):

- **`project_root_markers`** (default `[".git"]`) - the marker set used to
  find the nearest ancestor project root (see previous section). Modeled
  as `adapter.options.codex.project_root_markers`; an explicitly
  configured empty list is a valid, real "disable ancestor search"
  value, distinct from the key being absent (which uses the default).
- **`project_doc_fallback_filenames`** (e.g. `["TEAM_GUIDE.md",
  ".agents.md"]`) - extra filenames Codex treats as an instructions file,
  checked (in the configured order) after `AGENTS.override.md`/
  `AGENTS.md` in the same directory. Documented default: an empty list.
  Modeled as `entrypoint_candidates` extended by
  `adapter.options.codex.project_doc_fallback_filenames` in this
  instance's own `.eif/config.yaml` (see
  `core/schemas/eif-config.schema.json`) - scenarios 19/20 prove both the
  resolution (a configured fallback is adopted when nothing higher-
  precedence exists) and the precedence (a base `AGENTS.md` still beats
  it).
- **`project_doc_max_bytes`** (documented default `32768` / 32 KiB, real
  minimum `0` - zero means Codex loads no project docs at all) - a
  **combined** budget across the whole root-to-cwd chain enforced with a
  single running `remaining` counter: each file is included up to
  `min(file_size, remaining)` bytes and **truncated mid-content**, not
  skipped whole, when it would exceed what's left; Codex emits no warning
  of its own when this happens. Modeled as
  `adapter.options.codex.project_doc_max_bytes`, enforced by
  `eif_adapters.check_size_budget()` before every write via
  `simulate_codex_budget()`: `fits` is true exactly when the **EIF-managed
  block** (not the whole rendered file) is guaranteed to survive - if not,
  `eif_init.py` STOPs rather than publish a write Codex would truncate
  before the block ends (scenario 22 for the block's own exact boundary,
  scenario 23 for one byte short of it, scenario 23b proving a truncated
  *trailing footer* alone does not STOP, scenarios 24/24b for an ancestor
  chain alone exhausting the budget before EIF's own file is even
  reached).

**Not independently verified**: whether Codex exposes these two keys'
*live, currently-effective* values through any authless, machine-readable
command. Checked and ruled out as of `codex-cli 0.144.5`: `codex doctor
--json` (documented "Emit a redacted machine-readable report" - reports
installation/auth/network/sandbox/config-file-path state, but not
project-doc-specific settings), `codex features list`, `codex debug
--help`'s subcommands (`models`, `app-server`, `prompt-input` - none
dump project-doc config). Because no such introspection command exists,
`adapter.options.codex.*` is this **instance's own asserted** value, used
only to compute EIF's resolution/size-budget checks - it does not read or
change the user's real `config.toml`, and a project must keep the two in
sync by hand if `config.toml` changes. This is recorded as an explicit
limitation, not silently assumed away.

## Skill discovery

**Supported.** The same probe's raw output included a live
`<skills_instructions>` block enumerating real installed Codex skills
(`SKILL.md`-sourced, analogous in shape to Claude Code's Skills
mechanism). EIF does not currently generate or manage any
Codex-specific skill files - this only confirms the mechanism exists,
the same standard this repo applies to Claude Code's own "skill-
discovery" capability entry.

## Adapter switching

`claude-code <-> codex` (scenarios 3/4/18a/18b) and `cursor <-> codex`
(scenarios 27/28/29/30) are all supported via `eif_init.py --force
--adapter <name>`, in the same transaction as everything else. Codex and
Claude Code are both `entry_strategy=marker-merge`, so switching away from
either one **strips** the old entrypoint's EIF block but does **not**
delete the file - eif_init.py only deletes a marker-merge entrypoint if
nothing but whitespace remains once the block is removed, and the
generated "Project-specific rules" placeholder footer is never empty.
This is a real difference from Cursor's dedicated, full-regen file, which
has no legitimate content outside the block by contract and so is always
deleted outright on switch-away regardless of direction - verified
explicitly (not assumed) in `scripts/tests/test_codex_adapter.py`
scenario 4 (claude-code direction) and scenario 27 (cursor direction).
Malformed markers on the OLD entrypoint STOP the entire run before any
file is written (scenario 5). Switching a dynamic-resolve adapter AWAY
reads the old adapter's actual entrypoint from the existing lock, not
`entrypoint_for()`'s static greenfield default - the prior write may have
gone to `AGENTS.override.md`, not `AGENTS.md`, and the lock is the only
record of which one actually happened.

Switching INTO Cursor while Codex's own `AGENTS.md` still exists
(pre-strip) correctly requires an explicit `--adoption-mode`: Cursor's own
registry entry declares `AGENTS.md` a real `shared_signal` (a separate,
official mechanism Cursor also reads - see `adapters/cursor/README.md`),
independent of the switch itself - scenario 28 exercises this with
`--adoption-mode greenfield`.

## A real, adapter-agnostic bug found and fixed while building this

The shared managed-block template
(`templates/agent-instructions.md`, feeding every marker-merge adapter)
hardcoded a literal reference to `CLAUDE.md` in its "before opening a
PR" instructions, unconditionally - wrong for any adapter other than
Claude Code, and already present (uncaught) in the already-merged Cursor
demo workspace fixture. Fixed by adding a fourth template placeholder,
`{entrypoint_name}`, filled from the adapter's own registered entrypoint
(`eif_adapters.entrypoint_for()`) - `scripts/tests/test_codex_adapter.py`
scenario 1 asserts the generated content names itself correctly. The
already-merged Cursor demo workspace fixture was left untouched (no test
regenerates or diffs it against the live template, so nothing depends on
it matching); this is a cosmetic, non-functional drift in a static
example, not something this PR reopens.

## Doctor: active-entrypoint and size-budget drift

`eif_verify_runtime.py` does not just re-validate the file recorded in the
lock - it **recomputes** active-entrypoint resolution fresh, right now,
against the instance's actual current disk state and config, and fails if
it no longer agrees (scenario 25: an `AGENTS.override.md` appears after
generation with no re-run - doctor FAILs even though the locked
`AGENTS.md` is itself still perfectly well-formed). Every failure message
is written to distinguish **FILE INTEGRITY** (is the locked file itself
still present and well-formed on disk?) from **AGENT CONSUMPTION** (would
Codex actually still read that file as its active source today?) - a
locked entrypoint can be the former without being the latter, and a
doctor that only checked the former would miss exactly that regression.
Separately, `check_size_budget_drift()` runs two checks. First, it
compares the lock's recorded `adapter.effective_root_markers` against the
freshly-recomputed current value and fails as "AGENT CONSUMPTION invalid"
if `project_root_markers` has changed since generation (scenario 26c) -
before the size budget itself is even considered, since a different root
means a different chain. Second, it recomputes the size-budget check
against the **current** on-disk entrypoint content and the **current**
configured limit (scenario 26: lowering `project_doc_max_bytes` below the
managed block's own end offset, with no re-run, is caught; scenario 26b:
lowering it so only the *trailing project-owned footer* would truncate
does **not** fail, matching the safety rule that only the managed block's
own survival matters) - content grows and configured limits change after
generation; neither re-runs `eif_init.py` automatically.

## Runtime-validation status

Everything is testable and tested without any authenticated Codex
session - file generation, marker-merge preservation, adapter switching
(including Cursor), active-entrypoint resolution (override-as-target,
configured fallback filenames, the `AMBIGUOUS` unreadable-candidate case),
project-root discovery (no-marker-anywhere, custom/empty/multi-entry
marker lists, nearest-ancestor-wins, `.git`-as-file, empty `.git`
directory, path-policy STOPs on absolute/traversal marker names),
truncating size-budget enforcement (exact managed-block boundary, a
truncated trailing footer alone not failing, an ancestor chain alone
exhausting the budget), and `eif_verify_runtime.py` doctor drift
detection (entrypoint drift and root-marker drift, independently), all in
`scripts/tests/test_codex_adapter.py` (123/123) plus the unchanged
existing suites (no regressions - `run_all.py` still green).

**Beyond that**: the actual discovery/precedence/concatenation mechanism
itself was executed against a real, currently-installed Codex CLI
(`0.144.5`) via `codex debug prompt-input`, which requires no
authentication and performs no model call - this is a stronger form of
evidence than "opened the app and it didn't reject the files" (the
current state of the Cursor adapter's own manual-gate probe), since it
directly proves what Codex would load, not just that it tolerates the
files existing.

### Real wheel-installed runtime probe (2026-07-17, active-entrypoint correctness round)

Repeated end-to-end from the **installed wheel**, not a framework
checkout - `eifctl init --adapter codex` (confirmed by the lock recording
`framework.ref pkg:engineering-intelligence-framework@0.1.0.dev0`), against
a disposable probe project, with a random unguessable token
(`secrets.token_hex(8)`) injected through a genuinely EIF-owned generated
value - `--knowledge-root "knowledge-probe-<token>"`, which flows into the
rendered managed block's search-command line, not hand-typed into the
entrypoint file directly:

1. Greenfield init (`AGENTS.md`, nothing else present) -> `codex debug
   prompt-input -C <probe dir>` (authless, no model call) found the probe
   token present exactly once - the actual EIF-generated file is loaded,
   the managed block and generated search command are both present.
2. A same-directory `AGENTS.override.md` was then added by hand (its own
   distinguishing marker text, a second random token) - `eifctl doctor`
   was run **first** and correctly FAILed, predicting the active-source
   shift with the exact FILE INTEGRITY / AGENT CONSUMPTION distinction
   documented above, before anything was re-resolved.
3. A routine upgrade (`eifctl init`, no flags) re-resolved and
   marker-merged into `AGENTS.override.md` exactly as doctor predicted;
   `eifctl doctor` then passed cleanly.
4. `codex debug prompt-input` was re-run: the override's own
   distinguishing marker text was found present (Codex is reading
   `AGENTS.override.md` specifically, not a stale `AGENTS.md`), and the
   original knowledge-root probe token was still present too (the same
   governed content correctly followed the resolution to the new active
   file).

**No raw probe output was retained anywhere** - each capture was searched
only for the known-safe token strings above (never displayed or diffed in
full) and deleted immediately after; same discipline as the first pass,
extended to not persist the raw JSON even temporarily in scratch space,
since a real operator's own `~/.codex/AGENTS.md` content is included in
what `codex debug prompt-input` renders.

**Not independently verified**: Codex Cloud's own environment/workspace
configuration is kept separate from local CLI/desktop clients per the
official docs (`Local OpenAI clients can share CODEX_HOME configuration
... Codex Cloud keeps its own environment and workspace configuration`) -
this adapter's entrypoint is project-scope content checked into the repo
itself, which should behave identically across all three surfaces, but
that has not been independently exercised against Cloud or the desktop
app's own `/init` flow (documented to "use the same initialization
workflow as the Codex CLI," not independently re-run here).

### Isolated-CODEX_HOME runtime probe (2026-07-18, post-merge correctness round)

The 2026-07-17 probe above ran against the operator's own `$CODEX_HOME`,
which is why its raw output could never be retained. This round instead
pointed `CODEX_HOME` at a freshly-created, empty temporary directory for
the entire probe, so no personal global Codex configuration could enter
the captured output even transiently - confirmed both
`codex debug prompt-input` and `codex -c <key>=<value> ... debug
prompt-input` (Codex's own per-invocation config override flag) work
authless against a fully empty, unauthenticated `CODEX_HOME`. Rebuilt the
wheel from the hotfix commit and reinstalled it into the probe
environment before running:

1. A git-free probe tree (`outer/` with a 40000-byte decoy `AGENTS.md`
   containing an unguessable marker string, `outer/nested/` as the actual
   `eifctl init --adapter codex` instance, no `.git` anywhere) -> the
   captured prompt input contained **zero** occurrences of the decoy
   marker and exactly one occurrence of the instance's own
   `--knowledge-root` token - directly confirming, against the real
   installed binary and not just this adapter's own simulator, that no
   marker anywhere means no ancestor content is read.
2. The same instance re-initialized with
   `project_doc_max_bytes=2000` (well below the generated file's real
   4089-byte size) -> the captured prompt input's project-doc-bearing
   message was found to contain the exact 2000-byte prefix of the
   on-disk `AGENTS.md`, verbatim and byte-for-byte, as a substring (and
   confirmed the 2001-byte prefix was *not* a substring, ruling out an
   off-by-one match) - proving `simulate_codex_budget()`'s predicted
   truncation point is exactly where the real Codex CLI cuts, not just
   plausible. The real message was 235 bytes longer than the predicted
   2000-byte content; that overhead is Codex's own prompt-envelope
   wrapper tags around the injected file content, unrelated to the
   byte-budget algorithm itself.

**No raw probe output was retained anywhere** - both captures were
searched only for the known-safe marker/token strings and the byte-length
comparison above, never displayed or diffed in full, and deleted
immediately after use, even though this round's isolated `CODEX_HOME` had
no personal content to begin with.

## Re-verification

If the Codex CLI version changes materially, re-run `codex --version`
and re-fetch the official AGENTS.md docs before relying on the
precedence/byte-limit details above. Root-discovery and size-budget
semantics were pinned against `github.com/openai/codex` commit
`3a067484584861606ad842de5bc4ac735a865ddf` and installed CLI `0.144.5` as
of 2026-07-18; the rest of this document is current as of `0.144.5` /
2026-07-17. Neither is assumed stable indefinitely.
