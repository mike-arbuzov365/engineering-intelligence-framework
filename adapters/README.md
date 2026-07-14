# adapters/

Agent-specific glue: where each coding agent looks for instructions/skills,
and what its hook mechanism (if any) can and cannot do.

| Adapter | Status | Notes |
|---|---|---|
| `claude-code/` | evidence documented, no hook scripts | [`claude-code/README.md`](claude-code/README.md) - CLI `2.1.169` re-verified 2026-07-15; instructions/skill discovery OBSERVED live; hook behavior carried over from 2026-06-16 private evidence, not re-verified end-to-end this round |
| `codex/` | not ported | AGENTS.md loading, `hooks.json` PreToolUse hooks - hook `updatedInput` rewrite support varies by version, verify before relying on it |
| `cursor/` | not ported | `hooks.json` preToolUse + `updated_input` |
| `hermes/` | not ported | skill mirrors; terminal-tool guard hooks support block-only, not rewrite |

None of these are required - EIF's core (ontology, playbooks, templates) is
plain Markdown any agent can read if pointed at it. Adapters add
enforcement (hooks) and ergonomics (skill loading), not the methodology
itself.

## Recommended v0.1 priority

<!-- Knowledge source: hook-reliability testing on the private instance,
2026-07-14/15 (dated, single-instance measurement - not an independent or
multi-environment benchmark). -->

Not yet ratified (see [`core/policies/decisions.md`](../core/policies/decisions.md)
D-09) - a working recommendation based on the only reliability evidence
that exists so far:

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
