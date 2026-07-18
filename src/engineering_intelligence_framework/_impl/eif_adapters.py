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


def check_size_budget(
    instance_path: Path, adapter: str, active_entrypoint: str, rendered_text: str,
    begin_marker: str, end_marker: str, adapter_options: dict | None = None,
) -> SizeBudgetCheck:
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

    Only Codex declares a size_limit today. An adapter with no registered
    size_limit always fits trivially (fits=True, limit=-1, empty entries) -
    there is no documented contract to check it against.
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
