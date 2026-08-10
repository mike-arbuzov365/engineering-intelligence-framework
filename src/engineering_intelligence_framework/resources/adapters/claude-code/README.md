# Claude Code adapter

<!-- Knowledge source: GENERALIZE of the private EI's
30-templates/claude-code-hooks/README.md (dated 2026-06-16) + live
re-verification during this vertical slice, 2026-07-15. The private
source's RTK-specific PreToolUse wrapper script is intentionally NOT
ported here. RTK is now a public optional behavioral adapter, but hooks remain
an explicit maintainer-owned installation step (see `integrations/rtk/`). What's kept is the
*mechanism description*: where Claude Code looks for instructions and
skills, how hooks are layered, and - most load-bearing for EIF's own
design - the verified evidence that hooks are local-machine state CI
cannot see, which is exactly why EIF's core must not depend on them. -->

Status: entrypoint generated, hooks evidence-only. `scripts/eif_init.py`
generates the correct `CLAUDE.md` entrypoint for this adapter (see below);
no hook scripts are shipped yet - see "What this adapter does not include."

## Verified evidence

| Field | Value |
|---|---|
| Product/version tested | Claude Code CLI `2.1.169` |
| Date tested | 2026-07-15 |
| Verification command | `claude --version` |

## Статус session continuity (2026-08-09)

- Local `claude --help` для Claude Code `2.1.169` підтвердив
  `--continue`, `--resume`, `--fork-session`, positional initial prompt і
  `--name`. Current official
  [CLI reference](https://code.claude.com/docs/en/cli-reference) підтверджує
  той самий contract.
- `resume` класифіковано `verified`, але `instruction_only`: команда може
  відновити session, проте EIF не виконує її автоматично.
- `create_new_chat` є `documented`; `open_new_chat` лишається
  `not_verified`, бо немає no-submit canary, який довів би self-open і
  control transfer у current host.
- Fallback: створити named session вручну у verified project root, вставити
  handoff prompt, перевірити checkpoint і лише потім підтвердити send.
- `pre_compact` і `post_compact` не верифіковані end-to-end. Native
  compaction не є canonical memory.

## Persistent instruction discovery

OBSERVED directly in this session: Claude Code auto-loads a project-root
`CLAUDE.md` (and a user-level `~/.claude/CLAUDE.md`, if present) into the
agent's context at session start, without any explicit instruction to do
so. This is the mechanism `templates/agent-instructions.md` in this
framework is designed to be copied/generated into (as `AGENTS.md` or
`CLAUDE.md`, depending on project convention - both this repository's own
`AGENTS.md` and `CLAUDE.md`-shaped files are read by different agents; see
each adapter's own discovery rule).

## Skill discovery

OBSERVED directly in this session: Claude Code discovers skills as
`.claude/skills/<name>/SKILL.md` (YAML frontmatter with `name`/
`description`), invocable as `/<name>`. This matches the private
instance's own skill layout exactly (`.claude/skills/knowledge-search/SKILL.md`,
etc.) - no adaptation needed for this part of the mechanism, it already
generalizes as-is.

## Hook support

Not independently re-verified end-to-end in this session (would require
installing a hook and triggering it, which is out of scope for this
slice). Carried over from the private instance's dated evidence
(`claude-code-hooks/README.md`, 2026-06-16), stated here with its original
confidence level, not upgraded:

- Claude Code reads hooks from layered `settings.json` files: user-level
  (`~/.claude/settings.json`), project-level (`.claude/settings.json`,
  committed), and project-local (`.claude/settings.local.json`, not
  committed).
- `PreToolUse` hooks can rewrite a tool call's input (`updatedInput`) or
  block it outright. The private instance's evidence: this rewrite path
  was "verified end-to-end and applied reliably across dozens of test
  cases" while building its own tooling - a real, if single-instance,
  reliability data point, not a vendor claim.
- `Stop` hooks fire at the end of a turn/session and can act as a
  non-blocking reminder (the private instance uses this for a
  session-context cleanup nudge).

## Fallback behavior (the load-bearing finding)

OBSERVED in the private instance and structurally true regardless of hook
reliability: **hooks are local, per-machine configuration.** A
project-level `.claude/settings.json` can be committed, but a
user-level `~/.claude/settings.json` cannot be, and GitHub Actions CI has
no access to either at merge time. This means:

- CI can verify the *artifacts* a hook would enforce (this repository's
  own `scripts/` + CI jobs do exactly that - schema validation, privacy
  scanning, Knowledge Delta completeness), but it cannot verify that a
  hook actually ran during the session that produced a given PR.
- This is exactly why this framework's own agent-execution authority
  model (`core/ontology/authority-model.md#axis-c`) puts hook-based
  enforcement below the persistent instruction file as the "fallback of
  record," not treated as a separate, more-authoritative tier - a hook is
  a best-effort assist, not something the core workflow can require.

## What this adapter does not include

- No hook scripts (`settings.json`, `PreToolUse`/`Stop` wrapper scripts).
  The private instance's hook scripts are tightly coupled to its RTK
  integration and are not portable evidence. The public RTK adapter provides
  version/correctness health and generated guidance without installing those
  hooks. A generic hook example remains a separate, owner-reviewed follow-up.
- No claim that this vertical slice's own workflow depends on hooks in
  any way - every step in `examples/demo-workspace/README.md` is a plain
  command, runnable with or without Claude Code hooks configured.

## Re-verification

If the Claude Code CLI version changes materially, re-run
`claude --version` and update the table above; re-verify hook behavior
end-to-end (install a minimal `PreToolUse` hook, trigger it, confirm
`updatedInput` is applied) before relying on the carried-over 2026-06-16
evidence for anything load-bearing.

## Optional RTK portability fragment

EIF generates a compact
[`claude-code` RTK fragment](../../integrations/rtk/generated/adapters/rtk-claude-code.md)
and a non-installing
[`PreToolUse` contract](../../integrations/rtk/generated/hooks/claude-code.json).
The contract records carried rewrite evidence but does not install a script or
modify Claude Code settings. Active use still requires owner review and a
version-specific behavioral canary.
