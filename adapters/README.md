# adapters/

Agent-specific glue: where each coding agent looks for instructions/skills,
and what its hook mechanism (if any) can and cannot do.

| Adapter | Status | Notes |
|---|---|---|
| `claude-code/` | evidence documented, no hook scripts | [`claude-code/README.md`](claude-code/README.md) - CLI `2.1.169` re-verified 2026-07-15; instructions/skill discovery OBSERVED live; hook behavior carried over from 2026-06-16 private evidence, not re-verified end-to-end this round |
| `codex/` | **entrypoint ported** (`eif_init` resolves and marker-merges into whichever of `AGENTS.override.md`/`AGENTS.md`/a configured fallback is actually active - `entry_strategy=dynamic-resolve`), hooks not ported | [`codex/README.md`](codex/README.md) - Codex CLI `0.144.5` verified live 2026-07-17 against the official docs and, uniquely among these adapters, real runtime proof via `codex debug prompt-input` (no auth required) - confirmed root/nested `AGENTS.md` discovery order and, critically, that a same-directory `AGENTS.override.md` makes `AGENTS.md`'s content vanish from the merged chain entirely. EIF's own write correctly follows that precedence (merges into the override file itself when one is present, never a now-dead `AGENTS.md` alongside it) - a real defect in the first version, found and fixed before merge. `hooks.json` PreToolUse hooks are a DIFFERENT, unported mechanism - hook `updatedInput` rewrite support varies by version, verify before relying on it. |
| `cursor/` | **rules ported** (`eif_init` generates `.cursor/rules/eif/governance.mdc`), hooks not ported | [`cursor/README.md`](cursor/README.md) - Cursor CLI `3.11.19` re-verified live 2026-07-16 against the official docs (`.cursor/rules/*.mdc`, `.mdc` frontmatter: `description`/`globs`/`alwaysApply`); `.cursorrules` confirmed legacy/deprecated, not used. The `hooks.json`/`updated_input` claim below is about a DIFFERENT Cursor mechanism (tool-call hooks) than Rules, carried over from 2026-07-14/15 private evidence and NOT re-verified this round - do not read it as evidence for the Rules adapter. |
| `hermes/` | **dynamic active-source ported** (`eif_init` resolves and marker-merges into whichever of `.hermes.md`/`HERMES.md`/`AGENTS.md`/`agents.md`/`CLAUDE.md`/`claude.md` is actually active, or STOPs if the real active source is a parent directory's file or the Cursor-format fallback - `entry_strategy=dynamic-resolve` via a Hermes-specific resolver), hooks not ported | [`hermes/README.md`](hermes/README.md) - Hermes Agent `0.18.2` verified 2026-07-18 directly against the installed Python source (a git install, not a black-box wheel) and real runtime proof via `hermes prompt-size --json` (no auth required) - confirmed the real CLI's ancestor walk has no depth cap (7 levels deep, still finds the ancestor file) and that its truncation matches this adapter's own simulator exactly. Supersedes closed, unmerged PR #12, whose own "verified" evidence (a fabricated 5-level cap, missing lowercase fallbacks, an unmodeled Cursor-format tier) is not reused - see `hermes/README.md` "What PR #12 got wrong". Terminal-tool guard hooks (block-only, not rewrite) are a DIFFERENT, unported mechanism. |

None of these are required - EIF's core (ontology, playbooks, templates) is
plain Markdown any agent can read if pointed at it. Adapters add
enforcement (hooks) and ergonomics (skill loading), not the methodology
itself.

## Recommended v0.1 priority

<!-- Knowledge source: hook-reliability testing on the private instance,
2026-07-14/15 (dated, single-instance measurement - not an independent or
multi-environment benchmark). -->

**Ratified 2026-07-16** (see [`core/policies/decisions.md`](../core/policies/decisions.md)
D-09) for the current v0.1 scope: Claude Code and Cursor are the required
tested adapters. The ordering below predates ratification and is about
**hook** reliability specifically (a different Cursor mechanism than the
Rules adapter this repository actually ports) - kept for its original
evidence value, not as the rationale for the ratified adapter list itself:

1. **Claude Code first.** Its `PreToolUse` hook rewrite (`updatedInput`)
   was verified end-to-end and applied reliably across dozens of test
   cases while building the private instance's tooling.
2. **Cursor second.** Its hook protocol (`updated_input`, plain JSON) was
   also verified end-to-end and applied reliably in the same testing
   round, with a simpler response shape than Claude Code's.
3. **Codex and Hermes deferred**, not because they're unsupportable but
   because the evidence available says something specific: Codex's hook
   rewrite output was measured as *not applied* in roughly half of
   observed cases over several days on the private instance, meaning its
   persistent instruction file - not the hook - was doing the actual
   enforcement work. Hermes's terminal-tool guard only supports block, not
   rewrite, which is a different (more limited, but at least
   unambiguous) integration shape. Both need their own from-scratch
   verification before being trusted the same way.

This ordering is about **measured hook reliability**, not agent quality or
popularity - it should be revisited if a newer agent version changes the
picture, and the evidence behind it should be re-verified against this
framework's own adapters once they're actually ported, not assumed to
transfer unchanged from the private instance's numbers.
