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
    first-match precedence (Hermes: .hermes.md/HERMES.md, then AGENTS.md,
    then CLAUDE.md - see `entrypoint_candidates`). The actual filename to
    write MUST be computed per-instance by resolve_dynamic_entrypoint()
    below, never assumed to be entrypoint_for(adapter)'s static default
    (that default is only the greenfield fallback, used when nothing at
    all already exists). Marker-merge safety (find_managed_block(),
    render_merged_content()) still applies to whichever file is resolved -
    this is an orthogonal axis to entry_strategy's existing two values,
    not a replacement for marker-merge semantics.

entrypoint_candidates - for a "dynamic-resolve" adapter only: the ordered
  list of filenames the agent itself checks, in its own first-match-wins
  precedence (highest priority first). Some tiers may have a wider
  discovery scope than others (e.g. Hermes's .hermes.md/HERMES.md walk up
  to the git root; AGENTS.md/CLAUDE.md are checked at the instance root
  only) - see resolve_dynamic_entrypoint()'s ANCESTOR_WALK_TIER.

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
    glob_patterns  - project-owned rule files (the adapter's own entrypoint
                     is always excluded from these matches).
    legacy_signals - deprecated-but-still-read formats (existing-governance
                     signal only; EIF never generates into these).
    shared_signals - other official, adapter-confirmed-live mechanisms
                     (e.g. AGENTS.md) that count as existing governance if
                     present, without EIF ever writing to them.
    same_dir_shadow_signals - filenames that, if present in the SAME
                     directory as this adapter's own entrypoint, make the
                     entrypoint's content invisible to the agent at that
                     cwd (not merely "other governance nearby" - the write
                     itself becomes dead on arrival). Reported by
                     discover_shadow_signals() below, separately from
                     discover_governance_surfaces(), because it needs its
                     own always-shown warning independent of adoption mode
                     (see eif_preflight.run_preflight()'s shadow_signals
                     handling) - coexisting peacefully with a shadowing
                     file doesn't fix the fact that the write is pointless.
  See discover_governance_surfaces() below - this is the ONLY place that
  walks these; eif_init.py/eif_preflight.py must not hardcode adapter paths.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
        "entrypoint": "AGENTS.md",
        "entry_strategy": "marker-merge",
        "entry_ownership": "shared",
        "entry_frontmatter": "",
        # Verified live 2026-07-17 against `codex --version` and the official
        # docs (developers.openai.com/codex/guides/agents-md, redirects to
        # learn.chatgpt.com/docs/agent-configuration/agents-md): Codex builds
        # its instruction chain by walking from the git root down to cwd,
        # reading (per directory) AGENTS.override.md if present, else
        # AGENTS.md, then blank-line-concatenating root-to-cwd (root first,
        # closest-to-cwd last). Runtime-verified via `codex debug
        # prompt-input` (no auth required) against a disposable probe
        # project: a root AGENTS.md's content was confirmed present in the
        # merged chain; a nested subdirectory's own AGENTS.md was confirmed
        # appended after the root's content when cwd was inside it; and -
        # critically - adding an AGENTS.override.md in the SAME directory as
        # AGENTS.md made the base file's content vanish from the merged
        # chain entirely (not merged, not appended - fully absent). See
        # adapters/codex/README.md for the full evidence trail.
        "governance_discovery": {
            # Nested AGENTS.md/AGENTS.override.md files below the instance
            # root are part of Codex's OWN chain (unlike Cursor's AGENTS.md,
            # which is a separate mechanism) - reported as ordinary "other
            # governance" via the generic OK/WARN/STOP block, since a nested
            # file legitimately adds to (not replaces) what a deeper cwd
            # sees.
            "glob_patterns": ["**/AGENTS.md", "**/AGENTS.override.md"],
            "legacy_signals": [],
            "shared_signals": [],
            # A same-directory AGENTS.override.md is different in kind: it
            # does not add to the chain, it REPLACES this adapter's own
            # entrypoint outright (empirically confirmed above) - handled by
            # discover_shadow_signals()/eif_preflight's dedicated,
            # adoption-mode-independent warning, not the generic block.
            "same_dir_shadow_signals": ["AGENTS.override.md"],
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
        # No single fixed entrypoint - see entry_strategy note above.
        # "entrypoint" here is only the greenfield default (used when NO
        # candidate already exists anywhere relevant); the actual per-
        # instance target always comes from resolve_dynamic_entrypoint().
        "entrypoint": ".hermes.md",
        "entry_strategy": "dynamic-resolve",
        "entry_ownership": "shared",
        "entry_frontmatter": "",
        # Verified live 2026-07-17 against `hermes --version` (Hermes Agent
        # v0.18.2, 2026.7.7.2) and the official docs
        # (hermes-agent.nousresearch.com/docs/user-guide/features/
        # context-files): "Only one project context type is loaded per
        # session (first match wins): .hermes.md -> AGENTS.md -> CLAUDE.md
        # -> .cursorrules." .hermes.md and HERMES.md share the top tier (the
        # docs do not define their relative order if BOTH exist in the same
        # directory - an open, undocumented ambiguity, not assumed away).
        # Runtime-verified via `hermes prompt-size` (offline, no API call)
        # against a disposable probe project: confirmed the reported
        # "context (AGENTS.md/cwd files)" byte count changes only when the
        # HIGHEST-precedence candidate present actually gets picked up
        # (never the byte count of a lower-tier file that also exists);
        # confirmed a root .hermes.md is found from a NESTED cwd (walks to
        # git root); and confirmed a root AGENTS.md is NOT found from that
        # same nested cwd (0 bytes) - the "AGENTS.md cwd-only limitation" is
        # real, not just documentation prose.
        "entrypoint_candidates": [".hermes.md", "HERMES.md", "AGENTS.md", "CLAUDE.md"],
        "governance_discovery": {
            # .cursor/rules/*.mdc and legacy .cursorrules are read by Hermes
            # too (the docs place .cursorrules as the last link in the SAME
            # first-match chain above), but neither is a marker-merge target
            # for this adapter: .cursor/rules/*.mdc is YAML-frontmattered,
            # per-file granularity, structurally unlike a flat markdown
            # context file; .cursorrules is Cursor's own already-deprecated
            # legacy format (see adapters/cursor/README.md). Both are
            # discovery-only signals - existing governance EIF must not
            # silently write over, never a generation target.
            "glob_patterns": [".cursor/rules/**/*.mdc"],
            "legacy_signals": [".cursorrules"],
            "shared_signals": [],
            "same_dir_shadow_signals": [],
        },
        "verified_product_version": "0.18.2 (2026.7.7.2)",
        "verified_date": "2026-07-17",
        "capabilities": [
            "persistent-instruction-autoload",
            "skill-discovery",
        ],
        "unsupported": [
            "soul-md-out-of-scope-per-instruction",
            "hooks-not-verified",
        ],
        "fallback": (
            "Whichever candidate file is actually resolved (.hermes.md, "
            "HERMES.md, AGENTS.md, or CLAUDE.md) is read as plain context "
            "by any agent pointed at it, even one with no Hermes-specific "
            "integration."
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


def discover_governance_surfaces(instance_path: Path, adapter: str) -> list[str]:
    """Read-only, deterministic, instance-relative scan for pre-existing
    governance surfaces this adapter's registry entry declares - project-
    owned rule files (excluding the adapter's own entrypoint), legacy-format
    signals, and other official shared signals. Returns sorted paths
    relative to instance_path (posix separators), or [] if none found.

    Never writes anything. Guards against symlink/path escape: any match
    that resolves outside instance_path is silently excluded, never
    reported (there is nothing safe to say about content outside the
    instance root, so it is treated as absent rather than guessed at).

    A same-dir shadow signal (see discover_shadow_signals()) is also
    excluded here, the same way the entrypoint itself is: it gets its own,
    more specific report (writing our entrypoint is pointless while it is
    present, regardless of adoption mode) - reporting it a second time
    through this generic "other governance, pick an adoption mode" channel
    would be redundant and actively misleading, since choosing an adoption
    mode does not resolve a shadow signal the way it resolves everything
    else this function finds.
    """
    cfg = ADAPTERS[adapter].get("governance_discovery", {})
    instance_root = instance_path.resolve()
    if not instance_root.is_dir():
        return []
    try:
        entrypoint_resolved = (instance_path / entrypoint_for(adapter)).resolve()
    except OSError:
        entrypoint_resolved = None
    entry_dir = (instance_path / entrypoint_for(adapter)).parent
    shadow_resolved: set[Path] = set()
    for name in cfg.get("same_dir_shadow_signals", []):
        try:
            shadow_resolved.add((entry_dir / name).resolve())
        except OSError:
            continue

    def _safe_relative(p: Path) -> str | None:
        try:
            resolved = p.resolve()
            resolved.relative_to(instance_root)
        except (OSError, ValueError):
            return None  # escaped the instance root, or unreadable - never report
        if entrypoint_resolved is not None and resolved == entrypoint_resolved:
            return None  # the adapter's own entrypoint is not "other" governance
        if resolved in shadow_resolved:
            return None  # reported separately by discover_shadow_signals(), not here
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


def discover_shadow_signals(instance_path: Path, adapter: str) -> list[str]:
    """Read-only scan for filenames that, per this adapter's registry entry,
    would make its own entrypoint's content invisible to the agent if found
    in the SAME directory as that entrypoint (e.g. Codex's AGENTS.override.md
    sitting next to AGENTS.md - confirmed empirically to make the base
    file's content vanish from the merged instruction chain entirely, not
    merely add to it). Distinct from discover_governance_surfaces(), which
    reports "other governance that coexists" - this reports "another file
    that would make writing our own entrypoint pointless".

    Returns sorted relative paths (posix separators), or [] if none found or
    the adapter declares no such signals. Same symlink/path-escape guard as
    discover_governance_surfaces().
    """
    cfg = ADAPTERS[adapter].get("governance_discovery", {})
    names = cfg.get("same_dir_shadow_signals", [])
    if not names:
        return []
    instance_root = instance_path.resolve()
    if not instance_root.is_dir():
        return []
    entry_dir = (instance_path / entrypoint_for(adapter)).parent

    found: set[str] = set()
    for name in names:
        candidate = entry_dir / name
        try:
            resolved = candidate.resolve()
            resolved.relative_to(instance_root)
        except (OSError, ValueError):
            continue
        if resolved.is_file():
            found.add(candidate.relative_to(instance_path).as_posix())
    return sorted(found)


# entrypoint_candidates entries whose discovery scope is a hierarchical
# parent-directory walk up to the git root (Hermes: .hermes.md/HERMES.md).
# Anything in entrypoint_candidates but NOT in this set is checked at the
# instance root only ("cwd-only": Hermes's own AGENTS.md/CLAUDE.md
# behavior, confirmed empirically - see the "hermes" registry entry).
ANCESTOR_WALK_TIER = {".hermes.md", "HERMES.md"}
ANCESTOR_WALK_MAX_DEPTH = 5


def _find_git_root(start: Path) -> Path | None:
    current = start
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent


@dataclass
class DynamicEntrypointResolution:
    entrypoint: str
    dynamic: bool
    existing_at_root: bool
    parent_shadow: str | None
    rationale: str


def resolve_dynamic_entrypoint(instance_path: Path, adapter: str) -> DynamicEntrypointResolution:
    """Determine which file this adapter would actually treat as project
    context, for adapters whose entry_strategy is "dynamic-resolve" (a
    "marker-merge"/"full-regen" adapter gets its single static entrypoint
    back unchanged, dynamic=False). Read-only - never writes anything.

    Resolution order (mirrors the agent's OWN precedence, not an EIF
    invention):
      1. Walk instance_path and its ancestors (closest first, up to
         ANCESTOR_WALK_MAX_DEPTH levels or the git root, whichever is
         nearer) for each name in ANCESTOR_WALK_TIER, in
         entrypoint_candidates order. The first match found ANYWHERE in
         that walk is what the agent actually loads right now - whether
         it sits at instance_path itself (existing_at_root=True, EIF
         should marker-merge into it directly) or at a parent directory
         above it (parent_shadow=<path>, EIF must not silently create an
         ancestor-tier file at instance_path - that would immediately
         start shadowing the parent's file for this whole subtree, a real
         behavior change that needs an explicit decision, not a default).
      2. Only if nothing in that tier was found anywhere in the walk:
         check instance_path itself (cwd-only, no parent walk - this is
         the empirically-confirmed limitation for Hermes's own AGENTS.md/
         CLAUDE.md handling) for each remaining candidate in precedence
         order. The first one present is adopted.
      3. Only if nothing at all was found: default to the adapter's
         registered fallback entrypoint (entrypoint_for(adapter) -
         ".hermes.md" for Hermes) - the "greenfield, nothing exists yet"
         case the round's instruction requires as the ONLY time a new,
         higher-priority file gets created outright.
    """
    if entry_strategy_for(adapter) != "dynamic-resolve":
        return DynamicEntrypointResolution(
            entrypoint=entrypoint_for(adapter), dynamic=False, existing_at_root=True,
            parent_shadow=None, rationale="static entrypoint, no resolution needed",
        )

    candidates: list[str] = ADAPTERS[adapter].get("entrypoint_candidates", [entrypoint_for(adapter)])
    ancestor_tier = [c for c in candidates if c in ANCESTOR_WALK_TIER]
    cwd_only_tier = [c for c in candidates if c not in ANCESTOR_WALK_TIER]

    root = instance_path.resolve()
    git_root = _find_git_root(root)

    if ancestor_tier:
        current = root
        depth = 0
        while True:
            for name in ancestor_tier:
                if (current / name).is_file():
                    if current == root:
                        return DynamicEntrypointResolution(
                            entrypoint=name, dynamic=True, existing_at_root=True, parent_shadow=None,
                            rationale=f"existing {name!r} found at the instance root - adopting it",
                        )
                    return DynamicEntrypointResolution(
                        entrypoint=name, dynamic=True, existing_at_root=False,
                        parent_shadow=str(current / name),
                        rationale=(
                            f"{name!r} found in a parent directory ({current}), not at the instance "
                            f"root - this is what the agent actually loads right now for a session run "
                            f"at the instance root; creating a new ancestor-tier file there would start "
                            f"shadowing it for this whole subtree, so this is reported rather than acted "
                            f"on by default"
                        ),
                    )
            if git_root is not None and current == git_root:
                break
            if current.parent == current:
                break
            depth += 1
            if depth > ANCESTOR_WALK_MAX_DEPTH:
                break
            current = current.parent

    for name in cwd_only_tier:
        if (root / name).is_file():
            return DynamicEntrypointResolution(
                entrypoint=name, dynamic=True, existing_at_root=True, parent_shadow=None,
                rationale=f"existing {name!r} found at the instance root (cwd-only tier) - adopting it",
            )

    default = entrypoint_for(adapter)
    return DynamicEntrypointResolution(
        entrypoint=default, dynamic=True, existing_at_root=False, parent_shadow=None,
        rationale=f"no existing candidate found anywhere - defaulting to {default!r} (greenfield)",
    )
