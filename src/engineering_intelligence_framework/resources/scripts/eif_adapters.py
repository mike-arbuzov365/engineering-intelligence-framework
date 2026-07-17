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
  fallback_option_key above).

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
        # Verified live 2026-07-17 against `codex --version` (codex-cli
        # 0.144.5) and the official docs
        # (developers.openai.com/codex/guides/agents-md, redirects to
        # learn.chatgpt.com/docs/agent-configuration/agents-md, fetched
        # directly - not assumed from the redirect alone):
        #  - Per directory: AGENTS.override.md is checked first, else
        #    AGENTS.md, else any configured project_doc_fallback_filenames
        #    entry (in the order configured) - "Codex includes at most one
        #    file per directory."
        #  - Directory walk: project root (git root) DOWN to cwd, root
        #    first, closest-to-cwd last, concatenated with blank lines
        #    between. Stops at cwd; does not walk past it.
        #  - project_doc_max_bytes (default 32768 = 32 KiB) is a COMBINED
        #    budget across the whole root-to-cwd chain, whole-file
        #    granularity: "Codex skips empty files and stops adding files
        #    once the combined size reaches the limit" - a file is either
        #    wholly included or wholly excluded, never byte-truncated
        #    mid-content, and Codex itself emits no warning when a file is
        #    dropped this way.
        # Runtime-verified via `codex debug prompt-input` (no auth required)
        # against a disposable probe project: a root AGENTS.md's content was
        # confirmed present in the merged chain; a nested subdirectory's own
        # AGENTS.md was confirmed appended after the root's content when cwd
        # was inside it; and - critically - adding an AGENTS.override.md in
        # the SAME directory as AGENTS.md made the base file's content
        # vanish from the merged chain entirely (not merged, not appended -
        # fully absent). See adapters/codex/README.md for the full evidence
        # trail, including what is and is not independently verified (no
        # authless machine-readable command exposes project_doc_max_bytes/
        # project_doc_fallback_filenames' live values - `codex doctor --json`
        # was checked and does not report them).
        "entrypoint_candidates": ["AGENTS.override.md", "AGENTS.md"],
        "fallback_option_key": "project_doc_fallback_filenames",
        "size_limit": {
            "unit": "bytes",
            "default_limit": 32768,
            "config_key": "project_doc_max_bytes",
            "granularity": "whole-file, combined across the root-to-cwd chain",
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
        candidates.extend(adapter_options.get(fallback_key, []))

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


@dataclass
class SizeBudgetCheck:
    fits: bool
    rendered_size: int
    limit: int
    unit: str
    # (path-as-string, size) pairs for content that would be read BEFORE
    # this file in the adapter's own chain, and so counts against the same
    # combined budget even though EIF never writes it. [] for an adapter
    # with no such chain (e.g. Hermes's own per-file, non-combined limit).
    chain_contributors: list[tuple[str, int]]
    rationale: str


def _codex_ancestor_chain_bytes(instance_path: Path) -> list[tuple[str, int]]:
    """Bytes contributed by every directory ABOVE instance_path, up to and
    including the git root (or the filesystem root if there is none), that
    Codex would read BEFORE reaching instance_path in its root-to-cwd walk -
    at most one file per directory (AGENTS.override.md else AGENTS.md,
    Codex's own per-directory precedence). Read-only. This is what makes
    "the ancestor chain alone already exceeds the budget" a real,
    detectable-in-advance failure mode, not a hypothetical - Codex's own
    root-to-cwd concatenation means EIF's instance-root write is always at
    or near the END of the chain, so content it does not control and did
    not write can still cause it to be silently dropped."""
    root = instance_path.resolve()
    if (root / ".git").exists():
        return []  # the instance root IS the git root - no ancestor directory to walk at all
    current = root.parent
    contributors: list[tuple[str, int]] = []
    seen: set[Path] = set()
    while True:
        if current in seen:
            break
        seen.add(current)
        for name in ("AGENTS.override.md", "AGENTS.md"):
            f = current / name
            if f.is_file():
                try:
                    contributors.append((str(f), f.stat().st_size))
                except OSError:
                    pass
                break  # per-directory: override-else-base, at most one counted
        if (current / ".git").exists() or current.parent == current:
            break
        current = current.parent
    contributors.reverse()  # root-first, matching Codex's own read order
    return contributors


def check_size_budget(
    instance_path: Path, adapter: str, rendered_text: str, adapter_options: dict | None = None,
) -> SizeBudgetCheck:
    """Would this adapter's own documented content-size contract actually
    include `rendered_text` (the full file EIF is about to write, existing
    preserved content plus the managed block) once it is written? Read-only;
    callers (eif_init.py before writing, eif_verify_runtime.py's doctor
    after the fact) decide what to do with the answer - this function never
    writes anything and never STOPs anything itself.

    Only Codex declares a size_limit today (project_doc_max_bytes, a
    COMBINED budget across the root-to-cwd chain, whole-file granularity -
    see the registry entry's evidence comment). An adapter with no
    registered size_limit always fits (SizeBudgetCheck.fits=True,
    limit=-1) - there is no documented contract to check it against.
    """
    adapter_options = adapter_options or {}
    limit_cfg = ADAPTERS[adapter].get("size_limit")
    rendered_size = len(rendered_text.encode("utf-8"))
    if limit_cfg is None:
        return SizeBudgetCheck(
            fits=True, rendered_size=rendered_size, limit=-1, unit="n/a", chain_contributors=[],
            rationale=f"{adapter!r} declares no size_limit contract - nothing to check",
        )

    limit = int(adapter_options.get(limit_cfg["config_key"], limit_cfg["default_limit"]))
    chain_contributors = _codex_ancestor_chain_bytes(instance_path) if adapter == "codex" else []
    chain_total = sum(size for _, size in chain_contributors)
    fits = (chain_total + rendered_size) <= limit

    if fits:
        rationale = (
            f"{rendered_size} {limit_cfg['unit']}(s) (this file) + {chain_total} {limit_cfg['unit']}(s) "
            f"({len(chain_contributors)} ancestor file(s) read first) = {chain_total + rendered_size} "
            f"<= {limit} {limit_cfg['unit']}(s) ({limit_cfg['config_key']}) - fits"
        )
    elif chain_total >= limit:
        rationale = (
            f"the ancestor chain alone already totals {chain_total} {limit_cfg['unit']}(s), at or over "
            f"the {limit} {limit_cfg['unit']}(s) {limit_cfg['config_key']} budget - {adapter!r} would "
            f"never even reach this file for a session started at the instance root; the write would be "
            f"silently dropped from the merged instruction chain entirely ({limit_cfg['granularity']} - "
            f"no partial inclusion, and no warning is emitted by the agent itself)"
        )
    else:
        rationale = (
            f"{rendered_size} {limit_cfg['unit']}(s) (this file) + {chain_total} {limit_cfg['unit']}(s) "
            f"(ancestor chain) = {chain_total + rendered_size} {limit_cfg['unit']}(s), over the {limit} "
            f"{limit_cfg['unit']}(s) {limit_cfg['config_key']} budget - the write would be silently "
            f"dropped from the merged instruction chain entirely ({limit_cfg['granularity']} - no "
            f"partial inclusion, and no warning is emitted by the agent itself)"
        )
    return SizeBudgetCheck(fits, rendered_size, limit, limit_cfg["unit"], chain_contributors, rationale)
