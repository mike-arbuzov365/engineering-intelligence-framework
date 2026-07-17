# Hermes adapter

Status: dynamic entrypoint resolver implemented and tested (74 acceptance
checks in `scripts/tests/test_hermes_adapter.py`), plus real, offline
runtime proof against the actual installed Hermes Agent CLI (see "Runtime-
validation status" below). Marked **experimental, supported** - does not
change EIF's v0.1 required-adapter set (`core/policies/decisions.md` D-09;
Claude Code and Cursor remain the only required pair). `SOUL.md` is
explicitly out of scope for this adapter, per this round's instruction - a
separate personality/identity mechanism, unrelated to project context.

## Verified evidence

| Field | Value |
|---|---|
| Product/version tested | Hermes Agent `0.18.2` (`2026.7.7.2`), installed via `pip install hermes-agent` from PyPI, `hermes --version` |
| Date tested | 2026-07-17 |
| Verification command | `hermes prompt-size` (offline, no API call - reports byte-count breakdowns by prompt tier, never raw content) |
| Documentation source | `hermes-agent.nousresearch.com/docs/user-guide/features/context-files` |

## Why this adapter has no single fixed entrypoint

Unlike Claude Code, Cursor, or Codex, Hermes has no one filename EIF can
just always write to. Per the official docs, verbatim: "Only **one**
project context type is loaded per session (first match wins):
`.hermes.md` -> `AGENTS.md` -> `CLAUDE.md` -> `.cursorrules`." `.hermes.md`
and `HERMES.md` share the top tier - the docs do not define their relative
order if BOTH exist in the same directory, an open, undocumented ambiguity
this adapter does not attempt to resolve by assumption.

Critically, the docs also describe two DIFFERENT discovery scopes within
that single chain:

- `.hermes.md` / `HERMES.md`: "Walks to git root" - a hierarchical
  ancestor-directory walk (confirmed empirically as up to 5 parent
  directories or the git root, whichever is nearer).
- `AGENTS.md` / `CLAUDE.md`: checked at the current working directory
  only - **no parent walk**.

`scripts/eif_adapters.py`'s new `entry_strategy: "dynamic-resolve"` and
`resolve_dynamic_entrypoint()` mirror this exactly (`ANCESTOR_WALK_TIER`
vs. the cwd-only remainder of `entrypoint_candidates`), rather than
hardcoding a Hermes-only branch spread through `eif_init.py`'s bootstrap
logic - a future adapter with a similar "agent resolves its own context
file" shape can reuse the same mechanism.

## Real runtime proof (not just documentation)

Hermes Agent was already installed on the machine this was verified from
(the operator's own real setup, same situation as the Codex adapter's
verification). `hermes prompt-size` reports byte-count breakdowns by
prompt tier - crucially, **never raw content** - which made it possible to
prove file-discovery behavior with zero risk of capturing anything
sensitive, unlike Codex's `debug prompt-input` (which dumps the entire
merged prompt and required careful sanitization). Against a disposable
probe project:

1. Baseline (no context file anywhere): `context (AGENTS.md/cwd files):
   0 B`.
2. Adding a root `.hermes.md`: the same command reports `137 B` -
   confirms discovery.
3. Adding an `AGENTS.md` alongside it (deliberately much longer than the
   `.hermes.md` probe, so their sizes are unmistakably different): the
   reported figure stayed at exactly `137 B` - confirms `.hermes.md` wins
   over `AGENTS.md`, not just documented but observed.
4. Removing `.hermes.md`, keeping only `AGENTS.md`: the figure changed to
   match `AGENTS.md`'s own size - confirms the second-tier fallback works.
5. **The central limitation, confirmed empirically**: running the identical
   command from a NESTED subdirectory (with the real root `AGENTS.md`
   still present, untouched, one level up) reported `0 B` - the parent
   directory's `AGENTS.md` is invisible from cwd one level down. Re-adding
   a root `.hermes.md` and repeating the exact same nested-cwd query
   reported the full `137 B` again - the ancestor walk genuinely reaches
   the git root for this tier, while `AGENTS.md`/`CLAUDE.md` genuinely do
   not extend beyond the current working directory. This is not assumed
   from the docs' prose; it was independently reproduced.

## Shadow-prevention (the central design requirement)

Two distinct risks, both real, both handled:

1. **Intra-instance**: never create a NEW, higher-priority file
   (`.hermes.md`) when a lower-priority one (`AGENTS.md`/`CLAUDE.md`)
   already exists at the instance root and is presumably already the
   project's active Hermes context. `resolve_dynamic_entrypoint()` checks
   candidates in precedence order and adopts the first one already
   present - it only ever defaults to creating `.hermes.md` when NOTHING
   exists anywhere relevant. See `test_hermes_adapter.py` scenario 4
   (existing `AGENTS.md` adopted, no `.hermes.md` created alongside it).
2. **Cross-directory**: a `.hermes.md`/`HERMES.md` in a PARENT directory
   (not the instance root) already governs Hermes sessions run at the
   instance root, per the ancestor walk. Creating a new ancestor-tier file
   AT the instance root would immediately start shadowing that parent file
   for the whole subtree - a real behavior change, not something to do
   silently. Reported via the same mechanism already built for Codex's
   `AGENTS.override.md` shadow signal (`discover_shadow_signals()`/
   `eif_preflight.py`'s always-shown WARN, independent of adoption mode):
   the write still proceeds (it is safe, just possibly redundant with what
   the parent file already provides), but the WARN names the exact parent
   file and explains the consequence. See scenario 8 (one level up) and
   scenario 10b (found exactly at the git root, several levels up).

## A real bug found and fixed while building this: same-path adapter switch

`CLAUDE.md` is both Claude Code's own fixed entrypoint AND one of Hermes's
own candidates. Switching `claude-code -> hermes` when `CLAUDE.md` already
exists means Hermes's resolver correctly adopts that same file - but the
OLD adapter-switch logic in `eif_init.py` independently staged a SEPARATE
"strip the old entrypoint's EIF block" operation targeting the identical
path, double-staging the same `<path>.next` file for two different
transaction stages. The second stage to commit crashed with `staged
artifact missing` once the first had already consumed it - a real,
reproducible bug, not a hypothetical. Fixed by detecting when the OLD and
NEW entrypoint resolve to the same path and skipping the redundant
old-entrypoint stage entirely: the entrypoint stage's own marker-merge
already replaces the old EIF block with the new one on that single file,
preserving project content outside the markers exactly like any other
marker-merge. See `test_hermes_adapter.py` scenario 13 (the collision
case, now handled) and 13b (the genuinely-distinct-path case, switching
from Cursor, confirming the old full-regen file is still deleted outright
as expected when there is no collision).

## `.cursor/rules/*.mdc` and `.cursorrules`

Hermes's own docs place `.cursorrules` as the last link in the same
first-match chain, and separately note it also recognizes
`.cursor/rules/*.mdc` rule modules. Neither is a marker-merge target for
this adapter: `.cursor/rules/*.mdc` is YAML-frontmattered, per-file
granularity, structurally unlike a flat markdown context file; `.cursorrules`
is Cursor's own already-deprecated legacy format (see
`adapters/cursor/README.md`). Both are discovery-only signals - existing
governance EIF must never silently write over, reported via the same
generic OK/WARN/STOP channel as any other adapter's sibling files (see
scenario 7).

## Skill discovery

**Supported.** Hermes has its own skills mechanism (bundled and
user-installed `SKILL.md` sources, confirmed present in this operator's
own real installation). EIF does not currently generate or manage any
Hermes-specific skill files - this only confirms the mechanism exists,
the same standard this repo applies to the other adapters' "skill-
discovery" capability entries.

## Runtime-validation status

Everything is testable and tested without any live Hermes session -
dynamic resolution across every candidate and discovery-scope
combination, adapter switching (including the same-path collision fix),
malformed-marker STOPs, doctor pass/fail against a candidate-set-aware
lock check, and rollback, all in `scripts/tests/test_hermes_adapter.py`
(74/74) plus the unchanged existing suites (no regressions).

**Beyond that**: the actual discovery-scope split (ancestor walk vs.
cwd-only) was independently reproduced against the real installed Hermes
CLI (`0.18.2`) via `hermes prompt-size`, which requires no authentication
and makes no model call, and - unlike Codex's introspection command -
never risks exposing raw context content, only byte-count breakdowns.

**Not independently verified**: hook-based integrations (terminal-tool
guard hooks, which support block-only, not rewrite, per prior private
evidence carried over from an earlier round and not re-verified here);
Hermes's own messaging-platform surfaces (Telegram, Discord, Slack, ~20
others) and its Electron desktop app, which the project-scope context
file mechanism verified above should behave identically on (it is part of
the repository content itself), but that has not been independently
exercised on those surfaces.

## Re-verification

If the Hermes Agent version changes materially, re-run `hermes --version`
and re-fetch the official context-files docs before relying on the
precedence/discovery-scope details above - current as of `0.18.2` /
2026-07-17, not assumed stable indefinitely.
