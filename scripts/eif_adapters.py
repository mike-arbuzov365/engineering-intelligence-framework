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
  See discover_governance_surfaces() below - this is the ONLY place that
  walks these; eif_init.py/eif_preflight.py must not hardcode adapter paths.
"""
from __future__ import annotations

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
    """
    cfg = ADAPTERS[adapter].get("governance_discovery", {})
    instance_root = instance_path.resolve()
    if not instance_root.is_dir():
        return []
    try:
        entrypoint_resolved = (instance_path / entrypoint_for(adapter)).resolve()
    except OSError:
        entrypoint_resolved = None

    def _safe_relative(p: Path) -> str | None:
        try:
            resolved = p.resolve()
            resolved.relative_to(instance_root)
        except (OSError, ValueError):
            return None  # escaped the instance root, or unreadable - never report
        if entrypoint_resolved is not None and resolved == entrypoint_resolved:
            return None  # the adapter's own entrypoint is not "other" governance
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
