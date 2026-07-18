#!/usr/bin/env python3
"""The adapter registry: which agents EIF can generate an entrypoint for.

Single source of truth for adapter identity: entrypoint path, how that
entrypoint's content is produced/maintained (`entry_strategy`), any fixed
prefix required before the EIF-managed block (`entry_frontmatter`), and the
verified-evidence fields shown in each adapter's own docs. --adapter is
restricted to ADAPTERS.keys() so passing an unsupported name fails loudly
instead of silently generating the wrong (or a misleadingly-labeled)
entrypoint. Other modules (eif_init.py, eif_verify_runtime.py, ...) must read
adapter behavior from here - never hardcode a per-adapter branch elsewhere.

entry_strategy:
  "marker-merge" - the entrypoint may be a file the project already owns
    (CLAUDE.md is commonly hand-edited below the EIF:END marker). Content is
    computed via eif_markers.render_merged_content(), which preserves
    everything outside the EIF:BEGIN/EIF:END markers byte-for-byte.
  "full-regen" - the entrypoint is a dedicated, exclusively EIF-owned file
    (never shared with project-authored content). The whole file is
    regenerated every init/upgrade; there is nothing to merge or preserve.
  "dynamic-resolve" - there is no single fixed entrypoint filename; the
    agent itself picks ONE of several candidate filenames per its own
    documented precedence (Codex: AGENTS.override.md before AGENTS.md,
    same directory, plus any configured fallback filenames - see
    `entrypoint_candidates` and `fallback_option_key`). The actual filename
    to write MUST be computed per-instance by resolve_active_entrypoint()
    below, never assumed to be entrypoint_for(adapter)'s static default
    (that default is only the greenfield fallback, used when nothing at all
    already exists). Marker-merge safety (find_managed_block(),
    render_merged_content()) still applies to whichever file is resolved -
    this is an orthogonal axis to entry_strategy's other two values, not a
    replacement for marker-merge semantics.

Active-entrypoint resolution (resolve_active_entrypoint() below) reports one
of five states - a fixed vocabulary, not per-adapter ad hoc strings, because
"warn about a conflict but write anyway" (this registry's own previous
design) turned out to be the wrong default for more than one adapter:
  ACTIVE_MANAGEABLE   - a real, safely-writable marker-merge target was
                        found (or nothing exists yet and the greenfield
                        default applies) - proceed normally.
  ACTIVE_UNMANAGEABLE - the agent's real active governance source exists but
                        is not something EIF can marker-merge into (e.g. a
                        format EIF does not generate). Refuses by default.
  SHADOWED            - a real, would-be-manageable candidate is masked by a
                        higher-precedence source EIF must not silently
                        write past. Refuses by default.
  AMBIGUOUS           - cannot safely determine a single active target (e.g.
                        a higher-precedence candidate exists but cannot be
                        safely read as plain text). Always refuses; there is
                        no override for this one, unlike the two above.
  NOT_FOUND           - nothing exists yet; the registered greenfield
                        default entrypoint applies.
Callers (eif_init.py, eif_verify_runtime.py) must STOP on
ACTIVE_UNMANEAGABLE/SHADOWED/AMBIGUOUS rather than write the greenfield
default anyway with only a warning - "no active-target ambiguity may
degrade to a warn-and-write path" (round: Codex active-entrypoint
correctness, replacing this file's own previous same_dir_shadow_signals design,
which reported a Codex AGENTS.override.md as a WARN while still writing a
now-dead AGENTS.md).

entrypoint_candidates - for a "dynamic-resolve" adapter only: the ordered
  list of filenames the agent itself checks at the instance root, in its own
  first-match-wins precedence (highest priority first) - see
  resolve_active_entrypoint(). fallback_option_key, if set, names an
  adapter.options.<adapter> config key (see eif-config.schema.json) whose
  value is a list of ADDITIONAL filenames appended, in order, after the
  registered candidates - e.g. Codex's own project_doc_fallback_filenames,
  a real config.toml key (verified live 2026-07-17,
  learn.chatgpt.com/docs/agent-configuration/agents-md) EIF cannot read from
  the user's actual ~/.codex/config.toml (no authless effective-config
  command exposes it as of codex-cli 0.144.5 - see adapters/codex/README.md)
  - so it is instead asserted by the caller via this instance's own
  .eif/config.yaml.

size_limit - for a "dynamic-resolve" adapter only: the documented content
  budget this adapter's official contract enforces on whatever file(s) it
  actually reads, used by check_size_budget() below. `unit` is "bytes" or
  "chars"; `default_limit` is the adapter's own documented default (used
  when adapter_options does not override it); `config_key` names the
  adapter.options.<adapter> key a project may set to assert a different
  configured value (same "EIF cannot read the real config file" caveat as
  fallback_option_key above). For Codex specifically this is a COMBINED
  budget with per-file TRUNCATION (partial inclusion), not whole-file-only
  skip/include - verified 2026-07-18 directly against
  codex-rs/core/src/agents_md.rs (commit 3a067484584861606ad842de5bc4ac735a865ddf),
  correcting a real defect in this file's first version, which incorrectly
  modeled it as whole-file-only based on a paraphrased secondary source. See
  check_size_budget()/simulate_codex_budget() below.

root_marker_option_key - for a "dynamic-resolve" adapter only, when its
  chain-discovery is rooted at a discoverable ancestor rather than always
  the instance root: names the adapter.options.<adapter> key holding a
  configurable list of root-marker filenames (Codex:
  project_root_markers, default [".git"] - verified against
  codex-rs/config/src/project_root_markers.rs). An explicitly configured
  EMPTY list disables ancestor root discovery entirely (cwd-only) - this
  is a real, valid configuration, not an omission.

entry_ownership - the safety contract for what happens when the entrypoint
  path already has content with no EIF markers:
  "shared"    - legitimate: a project commonly owns this file already
    (CLAUDE.md). Existing unmarked content is preserved (marker-merge
    appends the block after it); adoption mode governs whether that's an
    OK/WARN/STOP per eif_preflight.py.
  "exclusive" - this path is EIF's own invention; nothing else has a
    legitimate reason to be there. Existing unmarked content STOPs
    unconditionally (regardless of adoption mode, size, or any content
    heuristic) - proven ownership (a single well-formed EIF block) is
    required before this path may ever be (re)written.

governance_discovery - read-only, deterministic, instance-relative
  discovery of OTHER pre-existing governance surfaces this adapter's own
  official contract is known to read, distinct from the entrypoint itself:
    glob_patterns  - project-owned rule files (this adapter's OWN candidate
                     filenames at the instance root are always excluded from
                     these matches - see discover_governance_surfaces()).
    legacy_signals - deprecated-but-still-read formats (existing-governance
                     signal only; EIF never generates into these).
    shared_signals - other official, adapter-confirmed-live mechanisms
                     (e.g. AGENTS.md) that count as existing governance if
                     present, without EIF ever writing to them.
  See discover_governance_surfaces() below - this is the ONLY place that
  walks these; eif_init.py/eif_preflight.py must not hardcode adapter paths.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from eif_markers import find_managed_block, MarkerConflict

ADAPTERS = {
    "claude-code": {
        "entrypoint": "CLAUDE.md",
        "entry_strategy": "marker-merge",
        "entry_ownership": "shared",
        "entry_frontmatter": "",
        # No other surfaces are known to compete with CLAUDE.md for Claude
        # Code's own governance - nothing to discover beyond the entrypoint
        # itself.
        "governance_discovery": {
            "glob_patterns": [],
            "legacy_signals": [],
            "shared_signals": [],
        },
        # Verified live 2026-07-15 against `claude --version` and the
        # official docs (code.claude.com/docs/en/memory): CLAUDE.md is loaded
        # as persistent context at session start - it is not enforced
        # configuration. See adapters/claude-code/README.md for the full
        # evidence, including what's carried over (hooks) vs re-verified.
        "verified_product_version": "2.1.169",
        "verified_date": "2026-07-15",
        "capabilities": [
            "persistent-instruction-autoload",
            "skill-discovery",
        ],
        "unsupported": [
            "hook-rewrite-re-verified-this-round",
        ],
        "fallback": (
            "CLAUDE.md is read as plain context by any agent pointed at it, "
            "even one with no Claude-Code-specific integration - core EIF "
            "does not depend on hooks or Claude-Code-specific behavior."
        ),
    },
    "cursor": {
        "entrypoint": ".cursor/rules/eif/governance.mdc",
        "entry_strategy": "full-regen",
        "entry_ownership": "exclusive",
        # Governance discovery, verified live 2026-07-16 against the
        # official docs (cursor.com/docs -> Rules): project rules live in
        # .cursor/rules/*.mdc (any filename, any depth) - the EIF target
        # itself is excluded by discover_governance_surfaces(). Legacy
        # .cursorrules is confirmed deprecated (not in current docs; active
        # migration discussed on the Cursor forum) - a signal that
        # governance already exists, never a generation target. AGENTS.md
        # is a SEPARATE, OFFICIAL, currently-documented mechanism Cursor
        # reads as project instructions (confirmed by the same fetch, not a
        # legacy fallback) - included as a shared_signal because its
        # presence is real pre-existing governance EIF must never silently
        # write over, even though EIF's own entrypoint stays the dedicated
        # .mdc file (see adapters/cursor/README.md).
        "governance_discovery": {
            "glob_patterns": [".cursor/rules/**/*.mdc"],
            "legacy_signals": [".cursorrules"],
            "shared_signals": ["AGENTS.md"],
        },
        # Frontmatter is always written fresh (never merged/preserved) - a
        # dedicated EIF-owned file has no legitimate hand-edited frontmatter
        # to protect. Field names/semantics verified live 2026-07-16 against
        # the official docs (cursor.com/docs -> Rules): alwaysApply: true
        # means the rule is always included in the model context and globs/
        # description are ignored - this is the closest match to CLAUDE.md's
        # unconditional autoload, so it is what this adapter uses for parity.
        # See adapters/cursor/README.md for the full evidence trail.
        "entry_frontmatter": (
            "---\n"
            "description: EIF governance - project rules, Knowledge Delta, and adoption policy\n"
            "alwaysApply: true\n"
            "---\n"
        ),
        "verified_product_version": "3.11.19",
        "verified_date": "2026-07-16",
        "capabilities": [
            "persistent-instruction-autoload",
        ],
        "unsupported": [
            "skill-discovery",
        ],
        "fallback": (
            "The .mdc file is read as plain markdown context by any agent "
            "pointed at it, even one with no Cursor-specific integration - "
            "core EIF does not depend on Cursor-specific behavior beyond the "
            "frontmatter Cursor itself requires to always-apply the rule."
        ),
    },
    "codex": {
        # Greenfield default only (used when NEITHER AGENTS.override.md NOR
        # AGENTS.md NOR any configured fallback already exists) - the actual
        # per-instance target always comes from resolve_active_entrypoint().
        "entrypoint": "AGENTS.md",
        "entry_strategy": "dynamic-resolve",
        "entry_ownership": "shared",
        "entry_frontmatter": "",
        # Verified 2026-07-18 directly against Codex's own Rust source,
        # pinned to commit 3a067484584861606ad842de5bc4ac735a865ddf on
        # github.com/openai/codex (post-merge correctness hotfix -
        # supersedes the 2026-07-17 doc-paraphrase-only verification, which
        # got the byte-budget model wrong - see below):
        #  - codex-rs/core/src/agents_md.rs (`read_agents_md`,
        #    `agents_md_paths`, `candidate_filenames`): per directory,
        #    AGENTS.override.md is checked first, else AGENTS.md, else any
        #    configured project_doc_fallback_filenames entry in order
        #    (de-duplicated, empty entries skipped) - at most one file per
        #    directory.
        #  - codex-rs/config/src/project_root_markers.rs +
        #    codex-rs/file-system/src/find_up.rs
        #    (`find_nearest_ancestor_with_markers`): the project root is
        #    the NEAREST ancestor (walking from the instance root upward)
        #    containing ANY configured `project_root_markers` entry
        #    (default [".git"] when unset). If NO marker is found anywhere
        #    - even after searching all the way to the real filesystem
        #    root - "only the current working directory is considered":
        #    the search_dirs chain becomes [instance_root] alone, NOT a
        #    walk that reads AGENTS.md from every ancestor up to the fs
        #    root. An explicitly configured EMPTY marker list disables root
        #    detection outright (same cwd-only result). This file's first
        #    version got this wrong (see _codex_search_dirs()'s docstring)
        #    when project_root_markers was unset/no root existed.
        #  - `read_agents_md`'s actual byte-budget algorithm: files are
        #    processed root-to-cwd in a single pass with a running
        #    `remaining` budget (default project_doc_max_bytes = 32768,
        #    minimum 0 - 0 means load nothing at all). Each file is
        #    included up to `min(file_size, remaining)` bytes - **a file
        #    that would exceed the remaining budget is TRUNCATED
        #    mid-content, not skipped whole** (`data.truncate(remaining)` in
        #    the real source) - this file's first version modeled the
        #    OPPOSITE (whole-file-only skip/include), sourced from an
        #    AI-paraphrased secondary doc page rather than the primary
        #    source, and was wrong; corrected here. Truncated bytes are
        #    lossy-UTF8-decoded (`String::from_utf8_lossy` - invalid
        #    sequences become U+FFFD, never a crash). A file whose
        #    (possibly-truncated) trimmed text is empty does not count
        #    against the budget and is skipped without decrementing
        #    `remaining`. Processing stops entirely once `remaining` hits 0.
        # Runtime-verified via `codex debug prompt-input` (no auth required,
        # both the 2026-07-17 and 2026-07-18 rounds, the latter from an
        # isolated CODEX_HOME) against disposable probe projects: a root
        # AGENTS.md's content confirmed present in the merged chain; a
        # nested subdirectory's own AGENTS.md confirmed appended after the
        # root's content when cwd was inside it; an AGENTS.override.md in
        # the SAME directory as AGENTS.md confirmed to make the base file's
        # content vanish from the merged chain entirely. See
        # adapters/codex/README.md for the full evidence trail, including
        # what is and is not independently verified (no authless
        # machine-readable command exposes project_doc_max_bytes/
        # project_doc_fallback_filenames/project_root_markers' live
        # configured values - `codex doctor --json` was checked and does
        # not report them).
        "entrypoint_candidates": ["AGENTS.override.md", "AGENTS.md"],
        "fallback_option_key": "project_doc_fallback_filenames",
        "root_marker_option_key": "project_root_markers",
        "default_root_markers": [".git"],
        "size_limit": {
            "unit": "bytes",
            "default_limit": 32768,
            "config_key": "project_doc_max_bytes",
            "granularity": "combined across the root-to-cwd chain, per-file truncation (partial inclusion), not whole-file skip",
        },
        "governance_discovery": {
            # Nested AGENTS.md/AGENTS.override.md files below the instance
            # root are part of Codex's OWN chain (unlike Cursor's AGENTS.md,
            # which is a separate mechanism) - reported as ordinary "other
            # governance" via the generic OK/WARN/STOP block (and, since
            # they are read BEFORE a deeper cwd's own file in the combined
            # byte budget, also as combined-chain-pressure contributors -
            # see check_size_budget()). This adapter's OWN same-directory
            # candidates (AGENTS.override.md/AGENTS.md themselves) are
            # excluded from this generic block by
            # discover_governance_surfaces() - a shadowed sibling candidate
            # is surfaced by resolve_active_entrypoint()'s own rationale,
            # never double-reported here.
            "glob_patterns": ["**/AGENTS.md", "**/AGENTS.override.md"],
            "legacy_signals": [],
            "shared_signals": [],
        },
        "verified_product_version": "0.144.5",
        "verified_date": "2026-07-17",
        "capabilities": [
            "persistent-instruction-autoload",
            "skill-discovery",
        ],
        "unsupported": [
            "codex-cloud-global-scope-parity-not-independently-verified",
        ],
        "fallback": (
            "AGENTS.md is a cross-tool convention (stewarded by the Agentic "
            "AI Foundation under the Linux Foundation) - it is read as plain "
            "context by any agent pointed at it, even one with no "
            "Codex-specific integration."
        ),
    },
    "hermes": {
        # Greenfield default only (used when NO candidate exists anywhere
        # relevant - see resolve_hermes_active_source(), which this adapter
        # uses INSTEAD of resolve_active_entrypoint() because its real
        # precedence needs an ancestor walk for tier 1 before even
        # considering tiers 2-4 at the instance root, a shape
        # resolve_active_entrypoint()'s single-directory model cannot
        # express).
        "entrypoint": ".hermes.md",
        "entry_strategy": "dynamic-resolve",
        "entry_ownership": "shared",
        "entry_frontmatter": "",
        # Verified 2026-07-18 directly against the installed Hermes Agent's
        # own Python source (git-installed, not a black-box wheel - local
        # HEAD 6142203bd7, +1 carried commit over upstream d59b79fa,
        # unrelated to context-file discovery). Primary files read:
        # agent/prompt_builder.py (startup discovery + transformation +
        # truncation), agent/subdirectory_hints.py (a SEPARATE, non-startup
        # mechanism - see below), tools/threat_patterns.py (security
        # scanning), agent/system_prompt.py (call-site/cache lifecycle).
        #
        # STARTUP discovery (agent/prompt_builder.py build_context_files_
        # prompt(), first match wins across exactly 4 tiers, checked in
        # this order):
        #  1. .hermes.md, then HERMES.md - _find_hermes_md(): nearest
        #     ancestor from cwd up to (and including) the git root, if a
        #     git root exists; if NO git root exists anywhere, cwd ONLY
        #     (deliberately, per the source's own comment: walking parents
        #     with no git root "could pick up a .hermes.md planted in
        #     /tmp, /home, etc."). NO depth cap of any kind - walks the
        #     FULL distance to the git root, however many levels that is.
        #  2. AGENTS.md, then agents.md - cwd only, no ancestor walk at all
        #     (not even to the git root).
        #  3. CLAUDE.md, then claude.md - cwd only, same as AGENTS.md.
        #  4. .cursorrules AND every immediate (non-recursive)
        #     .cursor/rules/*.mdc file, sorted by filename - cwd only.
        #     Within this tier ALL matching files are concatenated
        #     together (not first-match); the tier as a WHOLE is only
        #     reached if tiers 1-3 all produced nothing.
        # Only ONE tier's content is ever loaded per session - this is a
        # true first-match chain across tiers, unlike Codex's own
        # concatenating root-to-cwd chain.
        #
        # TRANSFORMATION (per file, in this exact order - see
        # _load_hermes_md/_load_agents_md/_load_claude_md/_load_cursorrules):
        #  tier 1 (.hermes.md/HERMES.md): read -> .strip() -> strip YAML
        #    frontmatter (_strip_yaml_frontmatter - "---"-delimited,
        #    stripped ONLY for this tier) -> security scan
        #    (_scan_context_content, see below) -> prepend "## <relpath>"
        #    heading -> truncate (see size_limit below).
        #  tiers 2-3 (AGENTS/CLAUDE): read -> .strip() -> security scan ->
        #    prepend "## <name>" heading -> truncate. NO frontmatter
        #    stripping for these tiers (the source simply never calls
        #    _strip_yaml_frontmatter for them) - if content here starts
        #    with "---" it is injected as-is, frontmatter and all.
        #  tier 4 (.cursorrules + *.mdc): each component (the flat
        #    .cursorrules file, then every sorted .mdc file) is
        #    independently read -> .strip() -> security-scanned -> given
        #    its own "## <name>" heading -> concatenated together -> the
        #    COMBINED tier is truncated ONCE at the end, not per
        #    component. No frontmatter stripping here either, even though
        #    real .mdc files normally have YAML frontmatter (description/
        #    globs/alwaysApply) - it is injected raw.
        #
        # SECURITY SCANNING (tools/threat_patterns.py, scope="context"):
        # every loaded file (all 4 tiers, plus subdirectory hints below) is
        # regex-scanned for prompt-injection/promptware/role-hijack
        # patterns BEFORE truncation. A match replaces the ENTIRE content
        # with "[BLOCKED: <name> contained potential prompt injection
        # (...)]." - not a partial redaction. EIF does not vendor this
        # pattern library (would drift silently from the pinned version) -
        # instead scripts/tests/test_hermes_adapter.py imports and calls
        # the REAL installed function directly against EIF's actual
        # generated EN/UK content, proving it is never blocked, plus one
        # deliberately-unsafe synthetic fixture proving the probe itself
        # can detect a real block (a control case, not just absence of
        # failure).
        #
        # SIZE LIMIT (_get_context_file_max_chars/_truncate_content):
        # per-tier, CHARACTER-based (not bytes - matters for non-ASCII
        # content, e.g. this framework's own Ukrainian locale), head+tail
        # preserving with the MIDDLE dropped (70% head / 20% tail of the
        # limit, ~10% consumed by the inserted truncation marker) -
        # fundamentally different from Codex's whole-chain running-budget
        # truncation. Resolution order: (1) explicit
        # adapter.options.hermes.context_file_max_chars if this instance's
        # own config asserts one; (2) otherwise the documented default of
        # 20,000 - the dynamic model-context-scaled cap
        # (_dynamic_context_file_max_chars: clamp(context_length x 4 x
        # 0.06, 20_000, 500_000)) requires knowing the live model's
        # context_length, and no authless, machine-readable command was
        # found that exposes the CURRENTLY EFFECTIVE value (`hermes config
        # show` has no --json mode and does not print context_file_max_chars
        # when unset; `hermes prompt-size --json` reports a "model" name
        # string, not a token-count context_length) - EIF does not invent
        # this value from a model-name lookup table, so the fallback used
        # here is always the conservative 20,000 floor unless explicitly
        # configured, and evidence is labeled accordingly (see
        # check_size_budget()'s rationale text).
        #
        # PROGRESSIVE SUBDIRECTORY DISCOVERY (agent/subdirectory_hints.py) -
        # explicitly NOT the same mechanism as the above, and not modeled
        # or generated for by this adapter: as the agent explores
        # subdirectories via tool calls (read_file/terminal/search_files),
        # SubdirectoryHintTracker independently discovers AGENTS.md/
        # agents.md/CLAUDE.md/claude.md/.cursorrules (NOT .hermes.md/
        # HERMES.md, and NOT .cursor/rules/*.mdc) in each newly-visited
        # directory and injects them into TOOL RESULTS (not the cached
        # system prompt), first-match-per-directory, flat-truncated at
        # 8,000 chars (no head/tail preservation), capped at 5 ancestor
        # levels walked from the referenced path back toward the working
        # directory (NOT toward a git root), and strictly confined inside
        # the session's working-directory tree. This is a real, separate,
        # always-on runtime behavior worth documenting honestly - EIF's own
        # write target is never chosen based on it, and it is never
        # described as "startup autoload" anywhere in this adapter's docs.
        #
        # PROMPT REBUILD/CACHE LIFECYCLE (agent/conversation_loop.py,
        # agent/system_prompt.py): context files are discovered and loaded
        # into the system prompt on the FIRST TURN of a NEW session only
        # (agent._cached_system_prompt is then reused for later turns in
        # that same session); a compression event can trigger a rebuild-
        # and-compare against the cached value. "persistent-instruction-
        # autoload" (this adapter's own capability tag, below) is accurate
        # for a session's first turn - it is not a continuously-refreshing,
        # every-turn re-scan of disk state.
        "entrypoint_candidates": [".hermes.md", "HERMES.md", "AGENTS.md", "agents.md", "CLAUDE.md", "claude.md"],
        "size_limit": {
            "unit": "chars",
            "default_limit": 20000,
            "config_key": "context_file_max_chars",
            "granularity": "per-tier independent head(70%)+tail(20%)-preserving truncation with the middle dropped, applied AFTER strip/frontmatter-strip/security-scan/heading-prepend - not a whole-chain running budget",
        },
        "governance_discovery": {
            # Nested copies of Hermes's own startup-tier candidates below
            # the instance root - genuinely different content from
            # progressive subdirectory hints (which read the SAME
            # filenames but are not something EIF writes for or tracks).
            # .cursorrules/.cursor/rules/*.mdc are deliberately NOT listed
            # here - resolve_hermes_active_source()'s own ACTIVE_UNMANAGEABLE
            # state already reports an active Cursor-tier source precisely;
            # listing it here too would double-report the same fact via the
            # generic OK/WARN/STOP channel (the same redundancy Codex's own
            # entry avoids for its same-directory candidates).
            "glob_patterns": ["**/.hermes.md", "**/HERMES.md", "**/AGENTS.md", "**/agents.md", "**/CLAUDE.md", "**/claude.md"],
            "legacy_signals": [],
            "shared_signals": [],
        },
        "verified_product_version": "0.18.2 (2026.7.7.2)",
        "verified_date": "2026-07-18",
        "capabilities": [
            "persistent-instruction-autoload",
            "skill-discovery",
        ],
        "unsupported": [
            "soul-md-out-of-scope-per-instruction",
            "hooks-not-verified",
            "progressive-subdirectory-hints-not-eif-managed",
        ],
        "fallback": (
            "Whichever candidate file is actually resolved (.hermes.md, "
            "HERMES.md, AGENTS.md/agents.md, or CLAUDE.md/claude.md) is "
            "read as plain context by any agent pointed at it, even one "
            "with no Hermes-specific integration."
        ),
    },
}

DEFAULT_ADAPTER = "claude-code"


def entrypoint_for(adapter: str) -> str:
    if adapter not in ADAPTERS:
        raise ValueError(
            f"eif-adapters: unsupported adapter '{adapter}'. Supported: "
            f"{', '.join(sorted(ADAPTERS))}. See adapters/README.md before "
            f"requesting a new one - each entry needs its own verified "
            f"evidence, not just an assumption it works like Claude Code."
        )
    return ADAPTERS[adapter]["entrypoint"]


def entry_strategy_for(adapter: str) -> str:
    return ADAPTERS[adapter].get("entry_strategy", "marker-merge")


def entry_frontmatter_for(adapter: str) -> str:
    return ADAPTERS[adapter].get("entry_frontmatter", "")


def entry_ownership_for(adapter: str) -> str:
    return ADAPTERS[adapter].get("entry_ownership", "shared")


def _own_candidate_paths(instance_path: Path, adapter: str) -> set[Path]:
    """Every filename this adapter's OWN entrypoint mechanism could resolve
    to at the instance root - for a dynamic-resolve adapter, EVERY
    registered candidate in precedence order, not just whichever one is
    currently active. A shadowed sibling candidate (e.g. a base AGENTS.md
    sitting next to a winning AGENTS.override.md) is still part of the
    entrypoint mechanism itself, never "other governance to coexist with" -
    that shadowing is surfaced by resolve_active_entrypoint()'s own
    rationale instead, so discover_governance_surfaces() must not
    double-report it. For a static (non-dynamic-resolve) adapter, just its
    one registered entrypoint, resolved directly from instance_path - which
    may itself be a nested relative path (Cursor's
    ".cursor/rules/eif/governance.mdc"), NOT necessarily a bare filename,
    so it must not be re-joined against its own parent directory the way
    entrypoint_candidates' bare filenames are below (a real bug: doing so
    built a nonexistent, doubled-up path that never matched the real
    entrypoint, silently breaking Cursor's own exclusion)."""
    resolved: set[Path] = set()
    candidates = ADAPTERS[adapter].get("entrypoint_candidates")
    if candidates is None:
        try:
            resolved.add((instance_path / entrypoint_for(adapter)).resolve())
        except OSError:
            pass
        return resolved
    # A real entrypoint_candidates list (dynamic-resolve adapters only,
    # e.g. Codex): every candidate is a bare filename checked at the same
    # directory as this adapter's own (greenfield-default) entrypoint.
    entry_dir = (instance_path / entrypoint_for(adapter)).parent
    for name in candidates:
        try:
            resolved.add((entry_dir / name).resolve())
        except OSError:
            continue
    return resolved


def discover_governance_surfaces(instance_path: Path, adapter: str) -> list[str]:
    """Read-only, deterministic, instance-relative scan for pre-existing
    governance surfaces this adapter's registry entry declares - project-
    owned rule files (excluding this adapter's own candidate filenames),
    legacy-format signals, and other official shared signals. Returns
    sorted paths relative to instance_path (posix separators), or [] if
    none found.

    Never writes anything. Guards against symlink/path escape: any match
    that resolves outside instance_path is silently excluded, never
    reported (there is nothing safe to say about content outside the
    instance root, so it is treated as absent rather than guessed at).
    """
    cfg = ADAPTERS[adapter].get("governance_discovery", {})
    instance_root = instance_path.resolve()
    if not instance_root.is_dir():
        return []
    own_paths = _own_candidate_paths(instance_path, adapter)

    def _safe_relative(p: Path) -> str | None:
        try:
            resolved = p.resolve()
            resolved.relative_to(instance_root)
        except (OSError, ValueError):
            return None  # escaped the instance root, or unreadable - never report
        if resolved in own_paths:
            return None  # this adapter's own entrypoint mechanism, not "other" governance
        if not resolved.is_file():
            return None
        return p.relative_to(instance_path).as_posix()

    found: set[str] = set()
    for pattern in cfg.get("glob_patterns", []):
        for p in instance_path.glob(pattern):
            rel = _safe_relative(p)
            if rel is not None:
                found.add(rel)
    for rel_name in [*cfg.get("legacy_signals", []), *cfg.get("shared_signals", [])]:
        rel = _safe_relative(instance_path / rel_name)
        if rel is not None:
            found.add(rel)
    return sorted(found)


class EntrypointState(str, Enum):
    """See the module docstring's "Active-entrypoint resolution" section for
    what each state means and how callers must react to it."""
    ACTIVE_MANAGEABLE = "active_manageable"
    ACTIVE_UNMANAGEABLE = "active_unmanageable"
    SHADOWED = "shadowed"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"


@dataclass
class EntrypointResolution:
    state: EntrypointState
    # The marker-merge target to write, when state is ACTIVE_MANAGEABLE or
    # NOT_FOUND (the greenfield default). None for ACTIVE_UNMANAGEABLE/
    # SHADOWED/AMBIGUOUS - there is nothing safe to write in those states;
    # the caller must STOP, not fall back to the greenfield default anyway.
    entrypoint: str | None
    dynamic: bool
    rationale: str


def resolve_active_entrypoint(
    instance_path: Path, adapter: str, adapter_options: dict | None = None,
) -> EntrypointResolution:
    """Determine which file this adapter would actually treat as its active
    project-doc/context source, for adapters whose entry_strategy is
    "dynamic-resolve" (a "marker-merge"/"full-regen" adapter gets its single
    static entrypoint back unchanged: state=ACTIVE_MANAGEABLE, dynamic=False).
    Read-only - never writes anything.

    `adapter_options` is this adapter's own options sub-dict from
    .eif/config.yaml's adapter.options.<adapter> (see
    core/schemas/eif-config.schema.json) - e.g. Codex's
    project_doc_fallback_filenames. Pass {} (or None) when nothing is
    configured; the adapter's own documented defaults apply.

    Resolution order (mirrors the agent's OWN precedence, not an EIF
    invention - see the "codex" registry entry's own evidence comment):
    every name in entrypoint_candidates, in order, then every name in
    adapter_options[fallback_option_key] (if the adapter declares one), in
    the order given. The first candidate present AT THE INSTANCE ROOT wins
    (Codex's own precedence has no ancestor-directory shadow risk for THIS
    decision - see below). The first candidate that exists but cannot be
    safely read as plain text (state=AMBIGUOUS) stops resolution outright,
    even if a later candidate would otherwise have been readable - refusing
    to silently skip past a candidate the agent's own contract says takes
    precedence.

    Codex's own contract CONCATENATES the root-to-cwd chain rather than
    letting a closer file hide a farther one (confirmed live - see the
    registry entry) - so, unlike an adapter with real cross-directory
    shadow risk, there is no SHADOWED state reachable here: an ancestor
    directory's own AGENTS.md/AGENTS.override.md is additional chain content
    (surfaced by discover_governance_surfaces() and check_size_budget()'s
    combined-pressure reporting), never something that hides EIF's own
    instance-root write. Likewise there is no ACTIVE_UNMANAGEABLE case for
    Codex today (no non-Markdown mechanism competes with AGENTS.md-shaped
    files) - both states are still part of the returned vocabulary because
    resolve_active_entrypoint() is adapter-generic infrastructure, not
    because Codex itself exercises every state.
    """
    adapter_options = adapter_options or {}
    if entry_strategy_for(adapter) != "dynamic-resolve":
        default = entrypoint_for(adapter)
        return EntrypointResolution(
            state=EntrypointState.ACTIVE_MANAGEABLE, entrypoint=default, dynamic=False,
            rationale="static entrypoint, no resolution needed",
        )

    root = instance_path.resolve()
    default = entrypoint_for(adapter)
    if not root.is_dir():
        return EntrypointResolution(
            state=EntrypointState.NOT_FOUND, entrypoint=default, dynamic=True,
            rationale=f"instance path does not exist yet - greenfield default {default!r} will apply",
        )

    candidates: list[str] = list(ADAPTERS[adapter].get("entrypoint_candidates", [default]))
    fallback_key = ADAPTERS[adapter].get("fallback_option_key")
    if fallback_key:
        # De-duplicated, empty entries skipped - mirrors
        # codex-rs/core/src/agents_md.rs's candidate_filenames() exactly
        # (verified 2026-07-18), not an approximation.
        for fb in adapter_options.get(fallback_key, []):
            if fb and fb not in candidates:
                candidates.append(fb)

    for name in candidates:
        candidate_path = root / name
        if not candidate_path.is_file():
            continue
        try:
            candidate_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            return EntrypointResolution(
                state=EntrypointState.AMBIGUOUS, entrypoint=None, dynamic=True,
                rationale=(
                    f"{name!r} exists at the instance root and takes precedence over any lower-"
                    f"priority candidate per {adapter!r}'s configured order, but could not be safely "
                    f"read as plain text ({type(e).__name__}: {e}) - refusing to guess whether it is "
                    f"the real active source or to silently skip past it. Resolve the file by hand, "
                    f"then retry."
                ),
            )
        shadowed = [c for c in candidates[candidates.index(name) + 1:] if (root / c).is_file()]
        shadow_note = (
            f" ({', '.join(shadowed)} also present at the instance root, but {name!r} takes "
            f"precedence over {'them' if len(shadowed) > 1 else 'it'} per {adapter!r}'s documented "
            f"per-directory precedence - {'they are' if len(shadowed) > 1 else 'it is'} not read at "
            f"all while {name!r} is present, not merely overridden)"
            if shadowed else ""
        )
        return EntrypointResolution(
            state=EntrypointState.ACTIVE_MANAGEABLE, entrypoint=name, dynamic=True,
            rationale=f"existing {name!r} found at the instance root - adopting it as the active target{shadow_note}",
        )

    return EntrypointResolution(
        state=EntrypointState.NOT_FOUND, entrypoint=default, dynamic=True,
        rationale=f"no existing candidate found at the instance root - defaulting to {default!r} (greenfield)",
    )


_HERMES_TIER1_NAMES = [".hermes.md", "HERMES.md"]
_HERMES_TIER2_NAMES = ["AGENTS.md", "agents.md"]
_HERMES_TIER3_NAMES = ["CLAUDE.md", "claude.md"]


def _find_git_root_upward(start: Path) -> Path | None:
    """Mirrors Hermes's own agent/prompt_builder.py::_find_git_root() exactly:
    the nearest ancestor of `start` (inclusive) containing `.git`, or None."""
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _read_tier_candidate(path: Path) -> tuple[bool, bool, str | None]:
    """Returns (exists, readable_and_nonempty, error_repr). Mirrors Hermes's
    own two-phase discover-then-load split: existence alone terminates a
    tier's SEARCH (matching _find_hermes_md's plain .is_file() check, no
    content inspection), but an existing, empty (whitespace-only) file is
    functionally invisible for content purposes - Hermes's own
    _load_hermes_md/_load_agents_md/_load_claude_md return "" for it, and
    the caller's `or`-chain falls through to the next tier. An unreadable
    file (bad UTF-8) is a distinct, AMBIGUOUS-triggering outcome - never
    silently treated as either empty or absent."""
    if not path.is_file():
        return False, False, None
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        return True, False, f"{type(e).__name__}: {e}"
    return True, bool(content.strip()), None


def _resolve_hermes_tier1(root: Path, adapter_options: dict) -> EntrypointResolution | None:
    """Tier 1 only: .hermes.md / HERMES.md, nearest ancestor from `root` up
    to (and including) the git root; cwd-only if no git root exists anywhere
    (mirrors _find_hermes_md() exactly - see the registry entry comment).
    Returns None to mean "tier 1 found nothing usable - fall through to
    tier 2", never a bare fall-through inside a shared loop."""
    git_root = _find_git_root_upward(root)
    search_dirs = [root]
    if git_root:
        cursor = root
        while cursor != git_root:
            cursor = cursor.parent
            search_dirs.append(cursor)

    for d in search_dirs:
        for name in _HERMES_TIER1_NAMES:
            exists, nonempty, err = _read_tier_candidate(d / name)
            if not exists:
                continue
            if err is not None:
                return EntrypointResolution(
                    state=EntrypointState.AMBIGUOUS, entrypoint=None, dynamic=True,
                    rationale=(
                        f"{name!r} exists at {d} and would take precedence per Hermes's own tier-1 "
                        f"(.hermes.md/HERMES.md) resolution, but could not be safely read as plain text "
                        f"({err}) - refusing to guess whether it is the real active source or to silently "
                        f"skip past it. Resolve the file by hand, then retry."
                    ),
                )
            if not nonempty:
                # Matches Hermes's own behavior: an existing-but-empty tier-1
                # file still terminates _find_hermes_md's SEARCH (no farther
                # ancestor is ever consulted), but _load_hermes_md then
                # returns "" for it, so the real session falls through to
                # tier 2 at cwd. Stop the whole tier-1 search here (not just
                # this directory) - searching a farther ancestor would be
                # wrong, since Hermes itself never gets that far either.
                return None
            if d == root:
                return EntrypointResolution(
                    state=EntrypointState.ACTIVE_MANAGEABLE, entrypoint=name, dynamic=True,
                    rationale=f"existing {name!r} found at the instance root - adopting it as the active target (Hermes tier 1)",
                )
            # A real, non-empty tier-1 file in an ANCESTOR (not the instance
            # root) is the actual active source today - EIF must not write
            # outside instance_path, and creating a new LOCAL tier-1 file
            # would immediately shadow the parent (nearest-wins), changing
            # effective governance for the whole subtree - a real behavior
            # change, never done silently.
            override = adapter_options.get("parent_context_action") == "override-with-local"
            if not override:
                return EntrypointResolution(
                    state=EntrypointState.SHADOWED, entrypoint=None, dynamic=True,
                    rationale=(
                        f"a parent directory ({d}) already has a non-empty {name!r} - per Hermes's own "
                        f"ancestor walk (nearest match wins, no depth cap), that file is this instance's "
                        f"REAL active source today, even though nothing exists locally. Creating a local "
                        f".hermes.md would silently shadow it and change effective governance for the "
                        f"whole subtree. STOPping - set adapter.options.hermes.parent_context_action: "
                        f"override-with-local to explicitly create a local file instead (generic coexist "
                        f"mode does not authorize this on its own)."
                    ),
                )
            return EntrypointResolution(
                state=EntrypointState.NOT_FOUND, entrypoint=".hermes.md", dynamic=True,
                rationale=(
                    f"parent_context_action=override-with-local is explicitly configured - ignoring the "
                    f"parent {name!r} at {d} and creating a local .hermes.md at the instance root instead, "
                    f"which will correctly take precedence over the parent (nearest-wins) from now on."
                ),
            )
    return None


def resolve_hermes_active_source(
    instance_path: Path, adapter_options: dict | None = None,
) -> EntrypointResolution:
    """Hermes-specific replacement for resolve_active_entrypoint() - used
    INSTEAD of it (never alongside) for adapter="hermes". Hermes's real
    precedence needs an ancestor walk for tier 1 (.hermes.md/HERMES.md)
    evaluated BEFORE tiers 2-4 are even considered at the instance root,
    which resolve_active_entrypoint()'s single-directory-only model cannot
    express - see the "hermes" registry entry's own evidence comment for
    the full, primary-source-verified precedence/transformation contract.
    Read-only - never writes anything.
    """
    adapter_options = adapter_options or {}
    root = instance_path.resolve()
    if not root.is_dir():
        return EntrypointResolution(
            state=EntrypointState.NOT_FOUND, entrypoint=".hermes.md", dynamic=True,
            rationale="instance path does not exist yet - greenfield default '.hermes.md' will apply",
        )

    tier1 = _resolve_hermes_tier1(root, adapter_options)
    if tier1 is not None:
        return tier1

    # --- Tiers 2-3: AGENTS.md/agents.md, then CLAUDE.md/claude.md - cwd
    # (instance root) only, no ancestor walk at all for either tier.
    for name in [*_HERMES_TIER2_NAMES, *_HERMES_TIER3_NAMES]:
        exists, nonempty, err = _read_tier_candidate(root / name)
        if not exists:
            continue
        if err is not None:
            return EntrypointResolution(
                state=EntrypointState.AMBIGUOUS, entrypoint=None, dynamic=True,
                rationale=(
                    f"{name!r} exists at the instance root and would take precedence per Hermes's own "
                    f"tier ordering, but could not be safely read as plain text ({err}) - refusing to "
                    f"guess whether it is the real active source or to silently skip past it. Resolve "
                    f"the file by hand, then retry."
                ),
            )
        if not nonempty:
            continue
        return EntrypointResolution(
            state=EntrypointState.ACTIVE_MANAGEABLE, entrypoint=name, dynamic=True,
            rationale=f"existing {name!r} found at the instance root - adopting it as the active target (Hermes tier {'2' if name in _HERMES_TIER2_NAMES else '3'})",
        )

    # --- Tier 4: .cursorrules and/or .cursor/rules/*.mdc - cwd only. Real
    # active source if present, but EIF never marker-merges into either
    # format for this adapter (no dedicated candidate, no override option
    # exists yet) - ACTIVE_UNMANAGEABLE, unconditional STOP.
    cursorrules_path = root / ".cursorrules"
    mdc_dir = root / ".cursor" / "rules"
    has_cursorrules = cursorrules_path.is_file()
    has_mdc = mdc_dir.is_dir() and any(mdc_dir.glob("*.mdc"))
    if has_cursorrules or has_mdc:
        which = ", ".join(n for n, present in ((".cursorrules", has_cursorrules), (".cursor/rules/*.mdc", has_mdc)) if present)
        return EntrypointResolution(
            state=EntrypointState.ACTIVE_UNMANAGEABLE, entrypoint=None, dynamic=True,
            rationale=(
                f"{which} present at the instance root with no higher-precedence tier found - this IS "
                f"Hermes's real active context source today (tier 4, Cursor-format fallback), and it is "
                f"active and valid on its own terms. EIF cannot marker-merge this format (YAML-"
                f"frontmattered, per-file granularity, structurally unlike a flat markdown context file), "
                f"and creating a new .hermes.md here would change precedence rather than adopt what's "
                f"already governing - no such semantic-override decision exists for this adapter. STOPping "
                f"rather than either silently ignoring the active source or silently overriding it."
            ),
        )

    return EntrypointResolution(
        state=EntrypointState.NOT_FOUND, entrypoint=".hermes.md", dynamic=True,
        rationale="no existing candidate found anywhere in Hermes's own precedence (tiers 1-4) - defaulting to '.hermes.md' (greenfield)",
    )


DEFAULT_CODEX_PROJECT_ROOT_MARKERS = [".git"]


@dataclass
class CodexDocEntry:
    """One file in Codex's simulated root-to-cwd read order - see
    simulate_codex_budget()."""
    path: str
    candidate_name: str
    is_active: bool
    read_order: int
    original_size: int
    included_bytes: int
    truncated_bytes: int
    remaining_before: int
    remaining_after: int
    counted: bool  # False when the (possibly-truncated) trimmed text was empty - matches Codex's own "skip empty, don't charge the budget" rule


@dataclass
class SizeBudgetCheck:
    fits: bool
    limit: int
    unit: str
    # Every file in the simulated root-to-cwd chain, in read order -
    # includes ancestor docs EIF does not control as well as the active
    # (about-to-be-written) entry.
    entries: list[CodexDocEntry]
    active_entry: CodexDocEntry | None
    managed_block_start: int | None  # byte offset of EIF:BEGIN within the active file's own bytes
    managed_block_end: int | None  # byte offset immediately after EIF:END
    begin_survives: bool
    end_survives: bool
    block_survives: bool
    # None when the active file was not truncated at all (nothing to check);
    # True/False when it was - see check_size_budget()'s docstring for why
    # this never independently flips `fits` given EIF's own markers are
    # pure ASCII.
    truncation_boundary_valid_utf8: bool | None
    rationale: str


def _codex_project_root_markers(adapter_options: dict) -> list[str]:
    """adapter.options.codex.project_root_markers - verified 2026-07-18
    against codex-rs/config/src/project_root_markers.rs: absent -> Codex's
    own documented default (['.git']); present-but-EMPTY is a deliberate,
    valid configuration meaning "disable parent-directory root detection
    entirely", not the same as "absent" - must not be conflated the way a
    plain `dict.get(key, default)` would (an empty configured list must not
    silently fall back to the default)."""
    if "project_root_markers" in adapter_options:
        return list(adapter_options["project_root_markers"])
    return list(DEFAULT_CODEX_PROJECT_ROOT_MARKERS)


def _find_codex_project_root(start: Path, markers: list[str]) -> Path | None:
    """Nearest ancestor (including `start` itself) containing ANY of
    `markers` - verified 2026-07-18 against
    codex-rs/file-system/src/find_up.rs's find_nearest_ancestor_with_markers:
    walks start -> parent -> parent ... checking every marker at the
    current level before moving up, terminating naturally at the real
    filesystem root. An empty marker list returns None immediately (root
    detection disabled). Returns None if the walk reaches the filesystem
    root without finding any marker - this is NOT "found a root at the
    filesystem root": callers must then treat discovery as cwd-only (see
    _codex_search_dirs), never keep walking and reading ancestor content up
    to the fs root (the real defect in this file's first version)."""
    if not markers:
        return None
    current = start
    while True:
        if any((current / m).exists() for m in markers):
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _codex_search_dirs(instance_path: Path, markers: list[str]) -> list[Path]:
    """Directories Codex would actually read project-doc candidates from,
    root-first, for a session starting at instance_path - verified
    2026-07-18 against codex-rs/core/src/agents_md.rs's own doc comment:
    "Determine the project root by walking upwards ... If no marker is
    found, only the current working directory is considered." When a
    marker IS found: root-to-instance_path inclusive. When NO marker is
    found anywhere (or the marker list is empty): `[instance_path]` alone -
    critically, NOT a walk to the filesystem root reading every ancestor's
    AGENTS.md along the way (the real defect this replaces: the previous
    _codex_ancestor_chain_bytes() only short-circuited when instance_path
    itself had `.git`, and otherwise walked all the way to the drive root
    collecting ancestor content whenever no `.git` existed anywhere)."""
    root = instance_path.resolve()
    project_root = _find_codex_project_root(root, markers)
    if project_root is None:
        return [root]
    dirs: list[Path] = []
    cursor = root
    while True:
        dirs.append(cursor)
        if cursor == project_root:
            break
        cursor = cursor.parent
    dirs.reverse()
    return dirs


def _codex_candidate_filenames(adapter_options: dict) -> list[str]:
    """Per-directory candidate precedence - verified 2026-07-18 against
    codex-rs/core/src/agents_md.rs's candidate_filenames(): AGENTS.override.md,
    then AGENTS.md, then configured project_doc_fallback_filenames in order
    (de-duplicated, empty entries skipped) - the exact same list
    resolve_active_entrypoint() builds via the generic entrypoint_candidates
    + fallback_option_key mechanism, duplicated here as a plain filename
    list because the simulator below needs it per-directory, not just at
    the instance root."""
    names = ["AGENTS.override.md", "AGENTS.md"]
    for candidate in adapter_options.get("project_doc_fallback_filenames", []):
        if candidate and candidate not in names:
            names.append(candidate)
    return names


def _codex_discover_chain(
    instance_path: Path, adapter_options: dict, active_entrypoint: str,
) -> list[tuple[Path, str, bool]]:
    """Every file Codex would actually attempt to read for a session
    starting at instance_path, root-first, one candidate per directory
    (first existing name wins) - EXCEPT at instance_path itself, where the
    ACTIVE entrypoint EIF is about to (re)write always takes that slot,
    using its post-write identity rather than whatever pre-write discovery
    would have found there (this models state immediately AFTER EIF's own
    write, including a brand-new greenfield file that does not exist on
    disk yet). Returns (path, candidate_name, is_active) tuples, read-only."""
    root = instance_path.resolve()
    markers = _codex_project_root_markers(adapter_options)
    names = _codex_candidate_filenames(adapter_options)
    chain: list[tuple[Path, str, bool]] = []
    for d in _codex_search_dirs(root, markers):
        if d == root:
            chain.append((d / active_entrypoint, active_entrypoint, True))
            continue
        for name in names:
            p = d / name
            if p.is_file():
                chain.append((p, name, False))
                break
    return chain


def simulate_codex_budget(
    instance_path: Path, adapter_options: dict, active_entrypoint: str,
    rendered_text: str, limit: int,
) -> tuple[list[CodexDocEntry], int | None]:
    """Deterministic simulation of codex-rs/core/src/agents_md.rs's
    read_agents_md(), verified 2026-07-18 directly against that function's
    source: process the discovered chain root-to-cwd, tracking a single
    `remaining` byte budget; each file is included up to
    `min(file_size, remaining)` bytes - TRUNCATED, not skipped whole, when
    it would exceed what is left (`data.truncate(remaining)` in the real
    source - the real defect this replaces: this file's first version
    assumed whole-file-only skip/include). Lossy-UTF8-decoded
    (`errors="replace"`, mirroring Rust's `String::from_utf8_lossy`). A file
    whose resulting trimmed text is empty is NOT counted against the budget
    (`remaining` is not decremented) and does not appear as an "included"
    entry, matching the real source exactly - this can legitimately happen
    for a blank ancestor AGENTS.md. Processing stops entirely (not just for
    this file) the instant `remaining` reaches 0. `limit <= 0` loads
    nothing at all (`max_total == 0` returns `Ok(None)` in the real source).
    Any `OSError` reading a real (non-active) file is treated as absent and
    skipped - a permissions/race condition on content EIF does not own and
    did not write should not block EIF's own operation.

    Returns (entries, active_entry_index) - `active_entry_index` is `None`
    when the active file's turn never comes (an earlier ancestor's own
    content already exhausted the budget)."""
    chain = _codex_discover_chain(instance_path, adapter_options, active_entrypoint)
    entries: list[CodexDocEntry] = []
    active_index: int | None = None
    if limit <= 0:
        return entries, None
    remaining = limit
    for i, (path, name, is_active) in enumerate(chain):
        if remaining == 0:
            break
        if is_active:
            data = rendered_text.encode("utf-8")
        else:
            try:
                data = path.read_bytes()
            except OSError:
                continue
        size = len(data)
        included = min(size, remaining)
        truncated = size - included
        text = data[:included].decode("utf-8", errors="replace")
        counted = bool(text.strip())
        entry = CodexDocEntry(
            path=str(path), candidate_name=name, is_active=is_active, read_order=i,
            original_size=size, included_bytes=(included if counted else 0),
            truncated_bytes=truncated, remaining_before=remaining,
            remaining_after=(remaining - included) if counted else remaining,
            counted=counted,
        )
        entries.append(entry)
        if is_active:
            active_index = len(entries) - 1
        if counted:
            remaining -= included
    return entries, active_index


def _hermes_tier_for_name(name: str) -> int:
    if name in _HERMES_TIER1_NAMES:
        return 1
    if name in _HERMES_TIER2_NAMES:
        return 2
    if name in _HERMES_TIER3_NAMES:
        return 3
    raise ValueError(f"_hermes_tier_for_name: {name!r} is not one of Hermes's registered entrypoint_candidates")


@dataclass
class HermesContextCheck:
    """Result of simulating Hermes's own per-tier transformation + head/tail
    truncation pipeline against the active tier's content - see
    simulate_hermes_context()."""
    fits: bool
    tier: int | None  # 1-4, or None when no tier resolved (nothing to check)
    source_chars: int
    limit: int
    limit_source: str  # "explicit-config" | "default-fallback"
    frontmatter_stripped: bool
    head_chars: int
    tail_chars: int
    transformed_chars: int
    truncated: bool
    begin_survives: bool
    end_survives: bool
    block_survives: bool
    scanner_checked: bool
    scanner_blocked: bool | None
    rationale: str


def _hermes_strip_yaml_frontmatter(content: str) -> str:
    """Mirrors Hermes's own agent/prompt_builder.py::_strip_yaml_frontmatter()
    exactly - used ONLY for tier-1 (.hermes.md/HERMES.md) content, per the
    pinned source (AGENTS/CLAUDE/.cursorrules tiers never call this)."""
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            body = content[end + 4:].lstrip("\n")
            return body if body else content
    return content


def simulate_hermes_context(
    active_tier: int, rel_name: str, rendered_text: str, limit: int, limit_source: str,
    begin_marker: str, end_marker: str, scan_fn=None,
) -> HermesContextCheck:
    """Simulate Hermes's own real transformation pipeline for the ACTIVE
    tier's content (`rendered_text` - the full file EIF is about to write,
    existing preserved content plus the managed block) and determine
    whether the EIF-managed block survives, exactly as check_size_budget()
    does for Codex, but against a completely different real algorithm (see
    the "hermes" registry entry's evidence comment): per-file strip() ->
    frontmatter-strip (tier 1 only) -> [security scan] -> "## <name>"
    heading prepend -> head(70%)+tail(20%)-of-limit truncation with the
    middle dropped, CHARACTER-counted throughout (not bytes).

    `scan_fn`, when provided, must match tools.threat_patterns.
    scan_for_threats's real (content, filename) -> sanitized_content
    signature (imported from the actual installed Hermes source by the
    caller - see scripts/tests/test_hermes_adapter.py). Left as None by
    default so this function (and everything that calls it from
    eif_init.py/eif_verify_runtime.py) never hard-depends on Hermes being
    installed - the returned scanner_checked=False in that case is itself
    part of the honest evidence, not a silent "assumed safe".

    Safety rule (matches the Codex simulator's own rule, verified
    separately for Hermes): `fits` requires the COMPLETE EIF-managed block
    (EIF:BEGIN through EIF:END, contiguous) to survive in the FINAL
    (post-transformation, post-truncation) text - checked by substring
    containment of the exact managed-block text, not independent marker-
    token presence (a head/tail split can keep both marker TOKENS while
    dropping everything between them - "the block is split by truncation",
    a real STOP condition, not proven safe just because both tokens
    happen to survive on their own)."""
    content = rendered_text.strip()
    frontmatter_stripped = False
    if active_tier == 1:
        stripped = _hermes_strip_yaml_frontmatter(content)
        frontmatter_stripped = stripped is not content
        content = stripped

    scanner_checked = scan_fn is not None
    scanner_blocked = None
    if scan_fn is not None:
        scanned = scan_fn(content, rel_name)
        scanner_blocked = scanned != content
        content = scanned

    source_chars = len(content)
    transformed = f"## {rel_name}\n\n{content}"

    try:
        block_start, block_end = _find_managed_block_or_none(transformed, begin_marker, end_marker)
    except MarkerConflict as e:
        return HermesContextCheck(
            fits=False, tier=active_tier, source_chars=source_chars, limit=limit, limit_source=limit_source,
            frontmatter_stripped=frontmatter_stripped, head_chars=0, tail_chars=0,
            transformed_chars=len(transformed), truncated=False,
            begin_survives=False, end_survives=False, block_survives=False,
            scanner_checked=scanner_checked, scanner_blocked=scanner_blocked,
            rationale=f"malformed markers in the transformed content: {e}",
        )
    managed_block_text = transformed[block_start:block_end] if block_start is not None else None

    if len(transformed) <= limit:
        final_text = transformed
        head_chars = tail_chars = 0
        truncated = False
    else:
        truncated = True
        head_chars = int(limit * 0.7)
        tail_chars = int(limit * 0.2)
        head = transformed[:head_chars]
        tail = transformed[-tail_chars:] if tail_chars else ""
        marker = f"\n\n[...truncated {rel_name}: kept {head_chars}+{tail_chars} of {len(transformed)} chars...]\n\n"
        final_text = head + marker + tail

    if scanner_blocked:
        block_survives = False
        rationale = (
            f"Hermes's own security scanner replaced {rel_name}'s content with a [BLOCKED: ...] "
            f"placeholder before it would ever reach the model - the generated EIF content itself "
            f"triggered a prompt-injection/promptware pattern match. This is never safe to proceed "
            f"past, regardless of size."
        )
    elif managed_block_text is None:
        block_survives = False
        rationale = "no EIF-managed block found in the transformed content (no EIF:BEGIN/EIF:END pair) - nothing to check"
    else:
        block_survives = managed_block_text in final_text
        if block_survives:
            rationale = (
                f"the EIF-managed block ({len(managed_block_text)} chars) survives intact in the "
                f"transformed{'  (truncated)' if truncated else ''} tier-{active_tier} content "
                f"({len(final_text)} of {len(transformed)} transformed chars, limit={limit} "
                f"chars, source={limit_source})"
            )
        else:
            rationale = (
                f"the EIF-managed block does NOT survive intact: the transformed tier-{active_tier} "
                f"content is {len(transformed)} chars, exceeding the {limit}-char limit ({limit_source}), "
                f"so Hermes truncates to head={head_chars}+tail={tail_chars} chars with the middle "
                f"dropped - the managed block is truncated mid-content or falls entirely in the "
                f"dropped middle. Raise context_file_max_chars, reduce content size, or split "
                f"instructions."
            )
    if not scanner_checked:
        rationale += " (security-scanner check not run in this pass - see test_hermes_adapter.py for the pinned-version proof against the real installed scanner)"

    return HermesContextCheck(
        fits=block_survives, tier=active_tier, source_chars=source_chars, limit=limit, limit_source=limit_source,
        frontmatter_stripped=frontmatter_stripped, head_chars=head_chars, tail_chars=tail_chars,
        transformed_chars=len(transformed), truncated=truncated,
        begin_survives=(managed_block_text is not None and not scanner_blocked and (transformed[block_start:block_start + len(begin_marker)] in final_text)),
        end_survives=(managed_block_text is not None and not scanner_blocked and (end_marker in final_text)),
        block_survives=block_survives,
        scanner_checked=scanner_checked, scanner_blocked=scanner_blocked,
        rationale=rationale,
    )


def _find_managed_block_or_none(text: str, begin_marker: str, end_marker: str) -> tuple[int | None, int | None]:
    result = find_managed_block(text, begin_marker, end_marker)
    if result is None:
        return None, None
    return result


def check_size_budget(
    instance_path: Path, adapter: str, active_entrypoint: str, rendered_text: str,
    begin_marker: str, end_marker: str, adapter_options: dict | None = None,
    hermes_scan_fn=None,
) -> SizeBudgetCheck | HermesContextCheck:
    """Would this adapter's own documented content-size contract actually
    load the EIF-managed block inside `rendered_text` (the full file EIF is
    about to write - existing preserved content plus the managed block)
    once it is written? Read-only; callers (eif_init.py before writing,
    eif_verify_runtime.py's doctor after the fact) decide what to do with
    the answer - this function never writes anything and never STOPs
    anything itself.

    Safety rule (matches this round's owner instruction exactly): proceed
    only when the ENTIRE EIF-managed block (EIF:BEGIN through EIF:END) is
    guaranteed to load. Do NOT require the whole project-owned file to fit
    when the complete EIF block is earlier in the surviving prefix - a
    truncated PROJECT-OWNED tail after an intact managed block is fine and
    does not flip `fits` to False.

    `truncation_boundary_valid_utf8` is computed and reported for evidence
    (a truncation cut splitting a multibyte UTF-8 character) but never
    independently flips `fits`: EIF's own EIF:BEGIN/EIF:END marker text is
    pure ASCII, so `managed_block_end` (computed from it) always lands on a
    valid UTF-8 boundary by construction - an invalid split can only occur
    at or after that point, i.e. inside the already-excluded tail once
    `fits` is already True, or inside the block's own (possibly non-ASCII,
    e.g. Ukrainian-locale) content once `fits` is already False from
    `block_survives` alone. Both cases are already correctly decided
    without this field; it is reported for transparency, not as a second
    gate.

    Codex and Hermes each declare a size_limit today - via two DIFFERENT
    real simulators (simulate_codex_budget() / simulate_hermes_context()),
    since their actual algorithms share no common shape (byte-chain-with-
    truncation vs. char-per-tier-head/tail-preserving). An adapter with no
    registered size_limit always fits trivially (fits=True, limit=-1) -
    there is no documented contract to check it against.

    For Hermes specifically: `hermes_scan_fn`, when the caller supplies one
    (a best-effort optional import of the real installed
    tools.threat_patterns.scan_for_threats-backed scanner - see
    eif_init.py/eif_verify_runtime.py's _try_import_hermes_scanner()), is
    passed straight through to simulate_hermes_context() so `fits` can
    reflect a real scanner block, not just size. When no scanner function
    is available (Hermes not installed in the current environment, or the
    caller passed nothing), `HermesContextCheck.scanner_checked` is False -
    an honest, reported limitation, never a silent "assumed safe". See
    scripts/tests/test_hermes_adapter.py for the pinned-version proof
    against the real installed scanner, which is the authoritative check.
    """
    adapter_options = adapter_options or {}
    limit_cfg = ADAPTERS[adapter].get("size_limit")
    if limit_cfg is None:
        return SizeBudgetCheck(
            fits=True, limit=-1, unit="n/a", entries=[], active_entry=None,
            managed_block_start=None, managed_block_end=None,
            begin_survives=True, end_survives=True, block_survives=True,
            truncation_boundary_valid_utf8=None,
            rationale=f"{adapter!r} declares no size_limit contract - nothing to check",
        )
    if adapter == "hermes":
        limit_key = limit_cfg["config_key"]
        if limit_key in adapter_options:
            limit = int(adapter_options[limit_key])
            limit_source = "explicit-config"
        else:
            limit = limit_cfg["default_limit"]
            limit_source = "default-fallback"
        tier = _hermes_tier_for_name(active_entrypoint)
        return simulate_hermes_context(
            tier, active_entrypoint, rendered_text, limit, limit_source, begin_marker, end_marker,
            scan_fn=hermes_scan_fn,
        )
    if adapter != "codex":
        raise NotImplementedError(
            f"check_size_budget: {adapter!r} declares a size_limit but has no chain simulation "
            f"implemented - simulate_codex_budget() is specific to Codex's own verified "
            f"root-to-cwd/truncating-budget contract, not a generic mechanism yet"
        )

    limit = int(adapter_options.get(limit_cfg["config_key"], limit_cfg["default_limit"]))

    rendered_bytes = rendered_text.encode("utf-8")
    begin_char_idx = rendered_text.find(begin_marker)
    end_char_idx = rendered_text.find(end_marker)
    managed_block_start = len(rendered_text[:begin_char_idx].encode("utf-8")) if begin_char_idx != -1 else None
    managed_block_end = (
        len(rendered_text[:end_char_idx].encode("utf-8")) + len(end_marker.encode("utf-8"))
        if end_char_idx != -1 else None
    )

    entries, active_index = simulate_codex_budget(instance_path, adapter_options, active_entrypoint, rendered_text, limit)
    active_entry = entries[active_index] if active_index is not None else None

    if active_entry is None:
        rationale = (
            f"{limit_cfg['config_key']} is configured as {limit} - Codex loads no project docs at all "
            f"in that state"
            if limit <= 0 else
            f"the ancestor chain ahead of {active_entrypoint!r} in the root-to-cwd read order already "
            f"exhausts the {limit} {limit_cfg['unit']}(s) {limit_cfg['config_key']} budget before Codex "
            f"would even attempt to read it - the write would never be loaded at all"
        )
        return SizeBudgetCheck(
            fits=False, limit=limit, unit=limit_cfg["unit"], entries=entries, active_entry=None,
            managed_block_start=managed_block_start, managed_block_end=managed_block_end,
            begin_survives=False, end_survives=False, block_survives=False,
            truncation_boundary_valid_utf8=None, rationale=rationale,
        )

    included = active_entry.included_bytes
    begin_survives = managed_block_start is not None and included >= managed_block_start
    end_survives = managed_block_end is not None and included >= managed_block_end
    block_survives = begin_survives and end_survives

    truncation_valid_utf8 = None
    if active_entry.truncated_bytes > 0:
        try:
            rendered_bytes[:included].decode("utf-8", errors="strict")
            truncation_valid_utf8 = True
        except UnicodeDecodeError:
            truncation_valid_utf8 = False

    fits = block_survives

    if fits:
        rationale = (
            f"the EIF-managed block ({managed_block_start}-{managed_block_end} bytes within "
            f"{active_entrypoint}) is fully included: {included}/{active_entry.original_size} bytes of "
            f"{active_entrypoint} survive after {len(entries)} file(s) processed root-to-cwd (budget "
            f"remaining before this file: {active_entry.remaining_before} of {limit} "
            f"{limit_cfg['unit']}(s))"
        )
    else:
        which = "not even EIF:BEGIN survives" if not begin_survives else "EIF:END does not survive (truncated mid-block)"
        rationale = (
            f"the EIF-managed block in {active_entrypoint} does NOT fully survive ({which}): only "
            f"{included} of {active_entry.original_size} bytes would be included after {len(entries)} "
            f"file(s) processed root-to-cwd (budget remaining before this file: "
            f"{active_entry.remaining_before} of {limit_cfg['config_key']}={limit} "
            f"{limit_cfg['unit']}(s)) - Codex truncates a file that exceeds the remaining budget rather "
            f"than skipping it whole, and emits no warning of its own when it does"
        )

    return SizeBudgetCheck(
        fits=fits, limit=limit, unit=limit_cfg["unit"], entries=entries, active_entry=active_entry,
        managed_block_start=managed_block_start, managed_block_end=managed_block_end,
        begin_survives=begin_survives, end_survives=end_survives, block_survives=block_survives,
        truncation_boundary_valid_utf8=truncation_valid_utf8, rationale=rationale,
    )
