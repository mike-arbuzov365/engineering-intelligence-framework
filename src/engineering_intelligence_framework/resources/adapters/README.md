# adapters/

Agent-specific glue: where each coding agent looks for instructions/skills,
and what its hook mechanism (if any) can and cannot do.

| Adapter | Status | Notes |
|---|---|---|
| `claude-code/` | entrypoint ported; optional RTK fragment generated; no hook installed | [`claude-code/README.md`](claude-code/README.md) - CLI `2.1.169` re-verified 2026-07-15; instructions/skill discovery OBSERVED live; hook behavior carried over from 2026-06-16 private evidence, not re-verified end-to-end this round |
| `codex/` | entrypoint ported; optional RTK fragment generated; hook contract is block-only | [`codex/README.md`](codex/README.md) - Codex CLI `0.144.5` has real runtime entrypoint proof. `updatedInput` mutation remains unverified, so the generated RTK contract does not claim transparent rewrite support. |
| `cursor/` | rules ported; optional RTK fragment generated; no hook installed | [`cursor/README.md`](cursor/README.md) - Cursor CLI `3.11.19` was re-verified for Rules. The generated RTK hook contract is separate from the Rules entrypoint and remains an owner-reviewed template. |
| `hermes/` | active source ported; optional RTK fragment generated; hook contract is block-only | [`hermes/README.md`](hermes/README.md) - Hermes Agent `0.18.2` has installed-source and offline runtime evidence. `updatedInput` was not applied, so the generated contract preserves fail-loud blocking. |

None of these are required - EIF's core (ontology, playbooks, templates) is
plain Markdown any agent can read if pointed at it. Adapters add
enforcement (hooks) and ergonomics (skill loading), not the methodology
itself.

All four generated entrypoints share the same compact optional-integration
pointer: read `.eif/runtime/integrations/README.md`, treat doctor as the
behavioral capability gate, keep source files authoritative over graph output,
and use core-safe fallbacks for non-healthy providers. The smoke suite verifies
that this pointer is present after init for every supported adapter. No adapter
auto-installs Graphify, RTK or hooks.

## Session continuity

[`parity-matrix.json`](parity-matrix.json) тепер містить окремі capability
records для `same_chat`, `resume`, `create_new_chat`, `open_new_chat`,
`auto_submit`, `pre_compact` і `post_compact`. Кожен record розрізняє
`status`, `enforcement`, `evidence_status`, точну дію і `auto_action`.

Поточний verified boundary є навмисно консервативним:

- `same_chat` доступний для всіх adapters через model-free `eifctl session
  handoff`;
- Claude Code, Codex і Hermes мають локально observed CLI resume contracts;
- Cursor resume лишається `documentation_only`, бо `agent` CLI не був
  доступний на validation host;
- жоден adapter не має `auto_action: true` для створення, відкриття або
  надсилання нового chat;
- `eifctl session handoff --open` fail-closed, доки adapter canary не дасть
  observed evidence для видимого destination, правильного project/profile і
  послідовного control transfer.

Це не змінює product-level support adapters. Різняться лише механіки та
сила evidence для continuity.

The optional RTK fragments and non-installing hook contracts live under
[`../integrations/rtk/generated/`](../integrations/rtk/generated/). They are
generated from one route registry plus the provider capability matrix and
cannot modify an entrypoint or user configuration.

**Adapter scope is frozen as of this round** (2026-07-18): these four
adapters are the complete v0.1 set, and all four are supported (D-16,
2026-07-27, superseding the two-tier split D-09 recorded). The real
differences between them are per-adapter mechanics, stated in each
adapter's own README, not a tier: Cursor has no tool-call hook mechanism to
enforce through, and the Codex and Hermes hook contracts are block-only
because `updatedInput` mutation is unverified on both. See
[`parity-matrix.json`](parity-matrix.json) for per-adapter capabilities and
[`switch-matrix.json`](switch-matrix.json) for the full directed switching
matrix (every ordered pair, 12 total) - both machine-readable and each
backed by a drift test that fails loudly if either goes stale.

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
