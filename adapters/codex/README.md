# Codex adapter

Status: entrypoint generated and tested (59 acceptance checks in
`scripts/tests/test_codex_adapter.py`), plus real, unauthenticated runtime
proof against the actual installed Codex CLI (see "Runtime-validation
status" below) - stronger evidence than a code-only adapter, since the
discovery mechanism itself was executed, not just documented.

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
2. **Project scope**: from the git root down to the current working
   directory, each directory is checked (in order) for
   `AGENTS.override.md`, then `AGENTS.md`, then any configured fallback
   filename (`project_doc_fallback_filenames`). At most one file per
   directory.
3. **Concatenation**: files are joined root-to-cwd with blank lines
   (root's content first, the directory closest to cwd last), up to a
   combined `project_doc_max_bytes` limit (default 32 KiB) - concatenation
   stops once the limit is reached, it does not error. Empty files are
   skipped.

This adapter's entrypoint is the **project-scope** `AGENTS.md` at the
instance root - `entry_strategy=marker-merge`, `entry_ownership=shared`,
the same contract as Claude Code's `CLAUDE.md` (a project may already
own this file; EIF preserves everything outside its own `EIF:BEGIN`/
`EIF:END` markers byte-for-byte). It is a **flat file**, not a nested
dedicated path like Cursor's `.mdc` - there are no parent directories to
create or roll back.

### The central risk: `AGENTS.override.md` shadows `AGENTS.md` entirely

Verified **empirically**, not just read from documentation: a disposable
probe project (a fresh git repo with a root `AGENTS.md` containing a
random unguessable marker string) was queried via `codex debug
prompt-input` (renders the exact model-visible prompt input as JSON,
without needing to authenticate or spend a real model call). With only
`AGENTS.md` present, its content appeared in the merged chain as
expected. Adding an `AGENTS.override.md` in the **same directory** and
re-running the identical command made the base file's content **vanish
from the merged chain entirely** - not merged, not appended, not
present in any form. This is a real, previously-undocumented-in-detail
risk for any tool (including EIF) that writes to `AGENTS.md`: the write
succeeds, but Codex will never read it while a same-directory override
file exists.

This adapter's registry entry
(`scripts/eif_adapters.py:ADAPTERS["codex"]["governance_discovery"]
["same_dir_shadow_signals"]`) declares `AGENTS.override.md` as exactly
this kind of signal. `discover_shadow_signals()` detects it read-only,
and `eif_preflight.py` reports it as an **always-shown WARN, independent
of adoption mode** (never a STOP - the write itself is still safe, only
pointless at that cwd until resolved). See
`scripts/tests/test_codex_adapter.py` scenarios 9/10.

A nested subdirectory's own `AGENTS.md` or `AGENTS.override.md` (below
the instance root, not sitting next to EIF's own entrypoint) is a
genuinely different case - it is part of Codex's own chain the same way
the root file is, so it is reported via the ordinary "other governance
surface" OK/WARN/STOP channel like any other adapter's sibling files
(scenarios 11/12), not the shadow-specific one.

Also verified in the same probe: a nested subdirectory's own `AGENTS.md`
is appended **after** the root file's content when the working directory
is inside that subdirectory (root-first, closest-to-cwd-last, exactly as
documented) - confirming the discovery order, not just its existence.

**Raw probe output was not committed or reproduced anywhere.** The
`codex debug prompt-input` command dumps the *entire* merged prompt,
which on the machine this was verified from also included that
operator's own real, personal global `~/.codex/AGENTS.md` content
(unrelated project workflow notes). Only the structural facts above -
never that content - are recorded here or in any commit.

## Skill discovery

**Supported.** The same probe's raw output included a live
`<skills_instructions>` block enumerating real installed Codex skills
(`SKILL.md`-sourced, analogous in shape to Claude Code's Skills
mechanism). EIF does not currently generate or manage any
Codex-specific skill files - this only confirms the mechanism exists,
the same standard this repo applies to Claude Code's own "skill-
discovery" capability entry.

## Adapter switching

`claude-code -> codex` and `codex -> claude-code` are both supported via
`eif_init.py --force --adapter <name>`, in the same transaction as
everything else. Both are `entry_strategy=marker-merge`, so switching
away from either one **strips** the old entrypoint's EIF block but does
**not** delete the file - eif_init.py only deletes a marker-merge
entrypoint if nothing but whitespace remains once the block is removed,
and the generated "Project-specific rules" placeholder footer is never
empty. This is a real difference from Cursor's dedicated, full-regen
file, which has no legitimate content outside the block by contract and
so is always deleted outright on switch-away - verified explicitly (not
assumed) in `scripts/tests/test_codex_adapter.py` scenario 4. Malformed
markers on the OLD entrypoint STOP the entire run before any file is
written (scenario 5).

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

## Runtime-validation status

Everything is testable and tested without any authenticated Codex
session - file generation, marker-merge preservation, adapter switching,
shadow/nested discovery, and `eif_verify_runtime.py` doctor checks, all
in `scripts/tests/test_codex_adapter.py` (59/59) plus the unchanged
existing suites (no regressions - `run_all.py` still green).

**Beyond that**: the actual discovery/precedence/concatenation mechanism
itself was executed against a real, currently-installed Codex CLI
(`0.144.5`) via `codex debug prompt-input`, which requires no
authentication and performs no model call - this is a stronger form of
evidence than "opened the app and it didn't reject the files" (the
current state of the Cursor adapter's own manual-gate probe), since it
directly proves what Codex would load, not just that it tolerates the
files existing.

**Not independently verified**: Codex Cloud's own environment/workspace
configuration is kept separate from local CLI/desktop clients per the
official docs (`Local OpenAI clients can share CODEX_HOME configuration
... Codex Cloud keeps its own environment and workspace configuration`) -
this adapter's entrypoint is project-scope content checked into the repo
itself, which should behave identically across all three surfaces, but
that has not been independently exercised against Cloud or the desktop
app's own `/init` flow (documented to "use the same initialization
workflow as the Codex CLI," not independently re-run here).

## Re-verification

If the Codex CLI version changes materially, re-run `codex --version`
and re-fetch the official AGENTS.md docs before relying on the
precedence/byte-limit details above - current as of `0.144.5` /
2026-07-17, not assumed stable indefinitely.
