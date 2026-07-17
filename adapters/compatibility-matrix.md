# Adapter compatibility matrix

Companion to [`parity-matrix.json`](parity-matrix.json) (the machine-checked
per-dimension evidence table). This document answers four narrower,
human-readable questions for each of the four registered adapters: which
files the agent itself actually reads, which one of those EIF manages,
which OTHER existing files could silently shadow what EIF writes, and
whether the current working directory changes any of this. Nothing here
is asserted without the executable evidence `parity-matrix.json` and each
adapter's own `scripts/tests/test_*_adapter.py` suite already back.

## The four adapters

| | Claude Code | Cursor | Codex | Hermes |
|---|---|---|---|---|
| **Files the agent reads** | `CLAUDE.md` only (single fixed file) | `.cursor/rules/*.mdc` (any file, any depth); legacy `.cursorrules` (deprecated); `AGENTS.md` (separate official mechanism) | Global: `$CODEX_HOME/AGENTS.override.md` or `AGENTS.md`. Project: **every** `AGENTS.md`/`AGENTS.override.md` from the git root down to cwd (concatenated, not first-match) | `.hermes.md`/`HERMES.md` (ancestor walk to git root) → `AGENTS.md` → `CLAUDE.md` → `.cursorrules` (first match wins, only one loaded) |
| **File EIF manages** | `CLAUDE.md` (marker-merge) | `.cursor/rules/eif/governance.mdc` (dedicated, full-regen) | `AGENTS.md` at the instance root (marker-merge) | Whichever candidate `resolve_dynamic_entrypoint()` selects (marker-merge once resolved) |
| **Existing files that can shadow EIF's write** | None known - CLAUDE.md is the only surface Claude Code reads | None known for the dedicated `.mdc` path (nothing else competes for that exact file) | `AGENTS.override.md` in the **same directory** - confirmed empirically to make `AGENTS.md`'s content vanish from the merged chain entirely | A `.hermes.md`/`HERMES.md` in a **parent directory** (ancestor tier always wins over anything EIF writes in a lower tier at the instance root); an `AGENTS.md`/`CLAUDE.md` already at the instance root, if EIF naively defaulted to creating `.hermes.md` instead of adopting it (structurally prevented, not just warned about) |
| **Does cwd change semantics?** | No - CLAUDE.md is read at a fixed location regardless of cwd | Not for EIF's dedicated file; Cursor's own broader Rules discovery is glob-based, not cwd-relative | Yes - the *set* of files concatenated depends on which directory a session is started from (root-to-cwd walk) | Yes, and unevenly: the `.hermes.md`/`HERMES.md` tier extends up to 5 parent directories or the git root; the `AGENTS.md`/`CLAUDE.md` tier does **not** extend past the exact cwd at all (empirically confirmed, not assumed) |

## Why the shadow risk points in opposite directions for Codex and Hermes

- **Codex**: the risk is that *someone else's* file (`AGENTS.override.md`)
  silently shadows the entrypoint *EIF already wrote*. EIF cannot prevent
  a project from adding an override file later; the best it can do is
  detect and warn (`discover_shadow_signals()`), which it does,
  unconditionally, independent of adoption mode.
- **Hermes**: the risk is the reverse - that *EIF's own write* would
  silently shadow a file the project (or a parent directory) *already
  relies on*, if EIF naively always created its most-preferred format
  (`.hermes.md`). `resolve_dynamic_entrypoint()` prevents the
  intra-instance case structurally (it adopts whatever already exists,
  never defaults over it) and reports the cross-directory case via the
  same `shadow_signals` mechanism Codex uses - so the two adapters end up
  sharing infrastructure despite the risk running in opposite directions.

## Verification method per adapter (headless runtime validation)

Not every adapter has an equally strong runtime-validation story - this
is stated plainly rather than smoothed over:

1. **Codex** - `codex debug prompt-input`: dumps the *entire* merged
   prompt as JSON. Strongest single-command proof, but required careful
   sanitization since it also reveals the operator's real global-scope
   configuration.
2. **Hermes** - `hermes prompt-size`: reports byte-count breakdowns per
   prompt tier, never raw content. Slightly less direct than Codex's
   command (you observe byte-count deltas, not the text itself) but
   carries zero disclosure risk by design.
3. **Claude Code** - no dedicated authless introspection command is known
   to exist; verified via `claude --version` plus the documented
   session-start behavior in the official docs.
4. **Cursor** - no authless CLI introspection command exists (Cursor is
   GUI-first). The only runtime step performed was launching the real
   installed app via computer-use (restricted to click-tier: no typing,
   unreliable screenshot content) and confirming the file Explorer shows
   the generated files without rejecting them. Whether Cursor's Agent
   chat actually incorporates the rule content in a response has **not**
   been confirmed - it needs a human at the keyboard, named as an open
   item in `adapters/cursor/README.md`, not silently assumed.

## Package inclusion

All four adapters are now proven to work from the actual installed wheel
(`pip install`-distributed `eifctl`), not only the dev checkout -
`scripts/tests/test_package_build.py` runs a dedicated
`eifctl init --adapter <name>` check for each one. The Cursor check was
the last one added (during this Stage 5 pass, having been missed when
Cursor's own adapter was originally built, before the installable-package
work existed) - closed immediately rather than left as a documented gap,
since it directly mirrored the existing Codex/Hermes checks.

## What this document does not claim

- Full pairwise adapter-switching coverage. Every adapter has been tested
  switching to/from **claude-code** specifically (the default adapter),
  in both directions, including fault-injection rollback. The underlying
  mechanism (`entry_strategy`-driven strip/delete decision,
  `old_entry_path`/`entrypoint` collision detection) is generic and does
  not branch on which two adapters are involved - but the remaining
  pairwise combinations (cursor↔codex, cursor↔hermes, codex↔hermes) have
  not been independently exercised by their own test scenarios.
- Any promotion of Codex or Hermes to a required v0.1 adapter. Both stay
  "supported, experimental" per this round's explicit instruction; D-09
  (`core/policies/decisions.md`) is untouched.
- Full parity on hook-based integrations. This document and
  `parity-matrix.json` are both scoped to the instruction/context-file
  discovery mechanism each adapter's own generated entrypoint depends on,
  not to tool-call hook protocols (`PreToolUse`/`updatedInput`/etc.),
  which are tracked separately in `adapters/README.md`'s "Recommended v0.1
  priority" section and were not re-verified this round.
