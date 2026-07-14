# adapters/

Agent-specific glue: where each coding agent looks for instructions/skills,
and what its hook mechanism (if any) can and cannot do.

| Adapter | Status | Notes |
|---|---|---|
| `claude-code/` | not ported | CLAUDE.md loading, Skill tool, PreToolUse hooks |
| `codex/` | not ported | AGENTS.md loading, `hooks.json` PreToolUse hooks - hook `updatedInput` rewrite support varies by version, verify before relying on it |
| `cursor/` | not ported | `hooks.json` preToolUse + `updated_input` |
| `hermes/` | not ported | skill mirrors; terminal-tool guard hooks support block-only, not rewrite |

None of these are required - EIF's core (ontology, playbooks, templates) is
plain Markdown any agent can read if pointed at it. Adapters add
enforcement (hooks) and ergonomics (skill loading), not the methodology
itself.
