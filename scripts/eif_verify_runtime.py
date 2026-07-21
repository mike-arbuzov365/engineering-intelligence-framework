#!/usr/bin/env python3
"""Integrity and consistency check for an EIF project instance ("doctor").

Bundled into every instance (`.eif/runtime/eif_verify_runtime.py`) and
referenced from the generated CLAUDE.md, so an instance can audit its own
state without a framework checkout.

Checks, each independently reported:

  1. config schema      - .eif/config.yaml validates
  2. lock schema         - .eif/framework.lock.yaml validates
  3. manifest digest      - the lock's own combined digest matches a fresh
                            recompute over its manifest (self-consistency)
  4. bundle file hashes   - every manifested file's current sha256 matches
                            the lock (catches hand-edits or partial upgrades)
  5. missing managed files    - a manifested path that no longer exists
  6. unexpected managed files - a file under .eif/runtime/ NOT in the
                            manifest. README.md and __pycache__/ are
                            classified separately (known, by-design
                            incidental output - see stage_bundle() in
                            eif_init.py) - anything else is flagged as a
                            real integrity concern, not silently ignored.
  7. config/adapter/lock/entrypoint consistency (see check_consistency()) -
                            for a "dynamic-resolve" adapter (Codex), this
                            RECOMPUTES active-entrypoint resolution fresh
                            (eif_adapters.resolve_active_entrypoint()) and
                            fails if it no longer agrees with the lock, not
                            merely "is the locked value one of the
                            registered candidates" - a shadowing sibling
                            candidate, a changed configured fallback list, or
                            an unresolvable state are all real drift the
                            lock's mere presence in a candidate list would
                            miss.
  8. migration provenance - config.adoption.mode vs lock.migration_status
                            do not contradict (coexist + greenfield is
                            impossible - see
                            check_migration_provenance_consistency())
  9. provenance state    - dirty / asserted, surfaced, not just recorded
 10. marker integrity     - CLAUDE.md and .gitignore's managed blocks are
                            each a single well-formed BEGIN/END pair
 11. config/generated-block drift - .eif/config.yaml's adoption.mode and
                            knowledge.root/index_path still match what is
                            actually written into the generated managed
                            block (catches a hand-edited config.yaml, or
                            entrypoint file, with no regeneration since -
                            see check_config_block_drift())
 12. knowledge index drift  - if the lock records an EIF-managed knowledge
                            index, it still exists, still carries EIF's
                            ownership marker, and its hash still matches
                            what was generated (see
                            check_knowledge_index_drift())
 13. size budget          - for an adapter with a registered size_limit
                            (Codex: project_doc_max_bytes), does the
                            CURRENT on-disk entrypoint, combined with the
                            CURRENT ancestor-chain content this instance
                            does not control, still fit the CURRENT
                            configured limit? Content grows, ancestor docs
                            get added, and a project may lower its own
                            configured limit after generation - none of
                            that re-runs eif_init.py automatically (see
                            check_size_budget_drift()).

Usage:
    python eif_verify_runtime.py --framework-root PATH [--instance-path PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eif_adapters import (  # noqa: E402
    ADAPTERS, entrypoint_for, entry_strategy_for,
    resolve_active_entrypoint, resolve_hermes_active_source, check_size_budget, EntrypointState,
)
from eif_markers import check_marker_integrity  # noqa: E402
from eif_integrations import (  # noqa: E402
    evaluate_integrations,
    integration_problems,
    validate_health_results,
)
from eif_validate_frontmatter import load_schema, validate_one, _normalize_yaml_scalars  # noqa: E402

try:
    import yaml
except ImportError:
    print(
        "eif-verify-runtime: PyYAML is required. Install with: "
        "pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(1)

EIF_BEGIN = "<!-- EIF:BEGIN"
EIF_END = "<!-- EIF:END -->"
GITIGNORE_BEGIN = "# EIF:BEGIN gitignore"
GITIGNORE_END = "# EIF:END gitignore"

# Files that legitimately exist under .eif/runtime/ but are NOT in the
# manifest - by design (see eif_init.py's stage_bundle()), not an oversight.
KNOWN_UNMANIFESTED_NAMES = {"README.md"}
KNOWN_UNMANIFESTED_DIR_NAMES = {"__pycache__"}

# Stable, distinguishing substrings from eif_init.py's GREENFIELD_/
# COEXIST_AUTHORITY_SECTION and eif_generate_index.py's render() output.
# Duplicated here as plain string literals (not imported) because this
# script IS bundled into every instance while eif_init.py and
# eif_preflight.py deliberately are NOT (see docs/architecture/
# instance-contract.md#validation-surface) - a bundled doctor command
# cannot import framework-only tooling, so it checks for these markers'
# text directly instead of re-deriving them from the same code that
# generated them.
# NOTE: both substrings must land entirely within a single physical line of
# GREENFIELD_AUTHORITY_SECTION/COEXIST_AUTHORITY_SECTION in eif_init.py - those
# are hand-wrapped triple-quoted strings, and read_text() preserves their
# literal newlines. A substring that straddles one of those line breaks (e.g.
# "platform/system safety first...", which crosses a real newline between
# "platform/system" and "safety") would never match the generated file's
# actual text, silently making the drift check a permanent false positive
# (coexist) or a permanent no-op (greenfield). Verify against the current
# source text before changing either value.
GREENFIELD_MARKER_TEXT = "safety first, then owner-ratified safeguards"
COEXIST_MARKER_TEXT = "EIF is NOT this project's sole or"
MANAGED_INDEX_MARKER = "<!-- Auto-generated by scripts/eif_generate_index.py. Do not edit by hand. -->"
# From eif_init.py's UNMANAGED_KNOWLEDGE_BEFORE_WORK - same duplication
# reasoning as the two markers above (this bundled script cannot import
# eif_init.py's own generation code).
UNMANAGED_KNOWLEDGE_TEXT = "knowledge is not managed by EIF"


class Report:
    def __init__(self):
        self.sections: list[tuple[str, list[str]]] = []

    def add(self, title: str, problems: list[str]) -> None:
        self.sections.append((title, problems))

    def print(self) -> bool:
        ok = True
        for title, problems in self.sections:
            if problems:
                ok = False
                print(f"FAIL {title}")
                for p in problems:
                    print(f"  - {p}")
            else:
                print(f"ok   {title}")
        return ok


def _load_yaml(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return _normalize_yaml_scalars(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    except yaml.YAMLError:
        return None


def check_schema(framework_root: Path, path: Path, schema_rel: str, label: str) -> list[str]:
    if not path.exists():
        return [f"missing: {path}"]
    data = _load_yaml(path)
    if data is None:
        return [f"invalid YAML: {path}"]
    # load_schema() is shared with eif_validate_frontmatter.py's standalone
    # CLI, where an unreadable/malformed/self-invalid schema file crashing
    # the process (via an uncaught FileNotFoundError/JSONDecodeError, or its
    # own deliberate `raise SystemExit(1)` on a schema that fails its own
    # meta-schema check) is fine - that's the entire process. Here it is one
    # check among many in a doctor report: a corrupt or partially-staged
    # bundle must not abort every OTHER check that hadn't run yet, so all
    # three failure modes are caught and reported as this one check's
    # problem list instead of propagating.
    schema_path = framework_root / "core" / "schemas" / schema_rel
    try:
        schema = load_schema(schema_path)
    except FileNotFoundError:
        return [f"runtime schema missing: {schema_path} (bundle may be corrupt or partially staged - re-run eifctl init)"]
    except json.JSONDecodeError as e:
        return [f"runtime schema is not valid JSON: {schema_path}: {e}"]
    except SystemExit:
        return [f"runtime schema failed its own self-check: {schema_path}"]
    errors = validate_one(data, schema, label)
    return errors


def check_manifest_digest(lock: dict) -> list[str]:
    manifest = lock.get("bundle", {}).get("manifest", [])
    stored_digest = lock.get("bundle", {}).get("digest", "")
    h = hashlib.sha256()
    for entry in sorted(manifest, key=lambda e: e["path"]):
        h.update(f"{entry['path']}:{entry['sha256']}\n".encode("utf-8"))
    recomputed = f"sha256:{h.hexdigest()}"
    if recomputed != stored_digest:
        return [f"manifest digest mismatch: lock says {stored_digest}, recomputed {recomputed} "
                f"(the manifest list itself was edited or is out of order)"]
    return []


def check_bundle_files(instance_path: Path, lock: dict) -> tuple[list[str], list[str], list[str]]:
    """Returns (hash_mismatches, missing, unexpected)."""
    bundle_path = instance_path / lock.get("bundle", {}).get("path", ".eif/runtime")
    manifest = lock.get("bundle", {}).get("manifest", [])
    manifested_paths = {e["path"] for e in manifest}

    hash_mismatches, missing = [], []
    for entry in manifest:
        f = bundle_path / entry["path"]
        if not f.exists():
            missing.append(entry["path"])
            continue
        actual = hashlib.sha256(f.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            hash_mismatches.append(entry["path"])

    unexpected = []
    if bundle_path.is_dir():
        for f in sorted(bundle_path.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(bundle_path).as_posix()
            if rel in manifested_paths:
                continue
            if f.name in KNOWN_UNMANIFESTED_NAMES:
                continue
            if any(part in KNOWN_UNMANIFESTED_DIR_NAMES for part in f.relative_to(bundle_path).parts):
                continue
            unexpected.append(rel)

    return hash_mismatches, missing, unexpected


def check_consistency(config: dict | None, lock: dict | None, instance_path: Path) -> list[str]:
    """config <-> adapter registry <-> lock <-> entrypoint. See module
    docstring item 7 / the round-3 review's Finding D.

    For a "dynamic-resolve" adapter (Codex), the lock's recorded entrypoint
    is not checked against a static expected value or mere membership in a
    candidate list - it is checked against a FRESH recomputation of
    resolve_active_entrypoint() run right now, against this instance's
    actual current disk state and current config. This is deliberately a
    stronger bar: "the locked value is A valid candidate" does not catch a
    higher-priority sibling appearing later (a lock says AGENTS.md but
    AGENTS.override.md now shadows it), a configured fallback list changing,
    or the resolution becoming altogether unresolvable. Every failure
    message below is written to distinguish FILE INTEGRITY (is the locked
    file itself still present and well-formed on disk? - a separate
    question, checked by check_markers()/check_bundle_files()) from AGENT
    CONSUMPTION (would the agent actually still read that file as its
    active source today, regardless of whether the file itself is fine)."""
    problems = []
    if config is None or lock is None:
        return ["cannot check consistency: config or lock missing/invalid"]

    cfg_adapter = (config.get("adapter") or {}).get("name")
    lock_adapter = (lock.get("adapter") or {}).get("name")
    lock_entrypoint = (lock.get("adapter") or {}).get("entrypoint")

    if cfg_adapter not in ADAPTERS:
        problems.append(f"config adapter.name {cfg_adapter!r} is not in the adapter registry (scripts/eif_adapters.py)")
    if cfg_adapter != lock_adapter:
        problems.append(f"config adapter.name ({cfg_adapter!r}) != lock adapter.name ({lock_adapter!r})")

    if lock_adapter in ADAPTERS:
        if entry_strategy_for(lock_adapter) == "dynamic-resolve":
            adapter_options = (((config.get("adapter") or {}).get("options")) or {}).get(lock_adapter) or {}
            resolution = (
                resolve_hermes_active_source(instance_path, adapter_options)
                if lock_adapter == "hermes" else
                resolve_active_entrypoint(instance_path, lock_adapter, adapter_options)
            )
            if resolution.state not in (EntrypointState.ACTIVE_MANAGEABLE, EntrypointState.NOT_FOUND):
                problems.append(
                    f"AGENT CONSUMPTION invalid for {lock_adapter!r}: the active-entrypoint resolution "
                    f"that was safe when this instance was last generated (lock records "
                    f"{lock_entrypoint!r}) is no longer safe today - {resolution.rationale}. This is "
                    f"independent of whether {lock_entrypoint!r} itself is still well-formed on disk. "
                    f"Resolve the conflict, then run eif_init.py again to re-resolve and regenerate."
                )
            elif resolution.entrypoint != lock_entrypoint:
                problems.append(
                    f"AGENT CONSUMPTION invalid for {lock_adapter!r}: lock adapter.entrypoint "
                    f"({lock_entrypoint!r}) no longer matches the active entrypoint {lock_adapter!r} "
                    f"would actually resolve to right now ({resolution.entrypoint!r}) - {resolution.rationale}. "
                    f"{lock_entrypoint!r} may still be FILE INTEGRITY valid (present, well-formed) while "
                    f"no longer being what the agent actually reads. Run eif_init.py again to re-resolve "
                    f"and regenerate."
                )
        elif lock_entrypoint != entrypoint_for(lock_adapter):
            problems.append(f"lock adapter.entrypoint ({lock_entrypoint!r}) != the registered entrypoint for {lock_adapter!r} ({entrypoint_for(lock_adapter)!r})")

    migration_status = (lock.get("instance") or {}).get("migration_status")
    if migration_status not in ("greenfield", "adopted"):
        problems.append(f"lock instance.migration_status is missing or invalid: {migration_status!r}")

    return problems


def check_size_budget_drift(config: dict | None, lock: dict | None, instance_path: Path) -> list[str]:
    """Independent-review addition: for an adapter with a registered
    size_limit (Codex: project_doc_max_bytes - see eif_adapters.ADAPTERS),
    recompute check_size_budget() against the CURRENT on-disk entrypoint
    content, the CURRENT root-marker-resolved ancestor chain, and the
    CURRENT configured limit. Content grows after generation, ancestor
    AGENTS.md/AGENTS.override.md files can appear above the instance root,
    a project may lower its own configured limit, and a project may change
    project_root_markers (changing which directory the chain simulation
    even starts from) - none of that re-runs eif_init.py automatically, so
    a doctor run that only re-validated file integrity would miss a real,
    silent "the agent no longer reads the whole governance block"
    regression. Uses the file's OWN current bytes directly (not a
    re-render from templates/ - that rendering code is deliberately not
    bundled into instances, same reasoning as check_config_block_drift()).

    Root-marker drift is checked FIRST and reported directly (AGENT
    CONSUMPTION - a changed root marker list means the chain Codex would
    actually simulate has changed, independent of whether it happens to
    still fit today) before the fresh chain simulation runs, so a project
    that hand-edited project_root_markers gets a message pointing at the
    actual cause, not just a generic "budget failed" from the recompute."""
    if config is None or lock is None:
        return []
    lock_adapter = (lock.get("adapter") or {}).get("name")
    lock_entrypoint = (lock.get("adapter") or {}).get("entrypoint")
    if lock_adapter not in ADAPTERS or not lock_entrypoint:
        return []
    if ADAPTERS[lock_adapter].get("size_limit") is None:
        return []
    entry_path = instance_path / lock_entrypoint
    if not entry_path.exists():
        return []  # missing entrypoint is check_consistency's/check_markers' concern, not this one's
    current_text = entry_path.read_text(encoding="utf-8", errors="replace")
    adapter_options = (((config.get("adapter") or {}).get("options")) or {}).get(lock_adapter) or {}

    problems: list[str] = []
    root_marker_key = ADAPTERS[lock_adapter].get("root_marker_option_key")
    if root_marker_key:
        locked_markers = (lock.get("adapter") or {}).get("effective_root_markers")
        current_markers = list(adapter_options.get(root_marker_key, ADAPTERS[lock_adapter].get("default_root_markers", [])))
        if locked_markers is not None and locked_markers != current_markers:
            problems.append(
                f"AGENT CONSUMPTION invalid for {lock_adapter!r}: effective {root_marker_key} changed "
                f"since this instance was generated (locked: {locked_markers!r}, current: "
                f"{current_markers!r}) - the project-root Codex resolves, and therefore the whole "
                f"chain the size budget is computed against, may now differ. Run eif_init.py again to "
                f"re-resolve and regenerate."
            )

    budget = check_size_budget(instance_path, lock_adapter, lock_entrypoint, current_text, EIF_BEGIN, EIF_END, adapter_options)
    if not budget.fits:
        problems.append(f"{lock_entrypoint} size budget: {budget.rationale}")
    return problems


def check_migration_provenance_consistency(config: dict | None, lock: dict | None) -> list[str]:
    """Independent-review addition: config.adoption.mode (current coexistence
    behavior) and lock.instance.migration_status (historical origin) answer
    different questions but must not contradict the evidence.

    The one hard contradiction: adoption.mode: coexist means this instance
    coexists with pre-existing project governance, so it cannot also claim a
    greenfield (empty-repo) birth. That pairing FAILs with a concrete repair
    instruction (an explicit reconfigure is the only supported way to change
    it - never a hand-edit of one file).

    The reverse - a greenfield authority mode over an `adopted` history - is
    NOT flagged: it is exactly what a greenfield authority override on an
    already-existing repo produces, and stays permissible/documented (an
    override changes who the block claims authority for; it does not rewrite
    how the repository came to be)."""
    if config is None or lock is None:
        return []  # schema checks already surface a missing/invalid file
    adoption_mode = (config.get("adoption") or {}).get("mode", "greenfield")
    migration_status = (lock.get("instance") or {}).get("migration_status")
    if adoption_mode == "coexist" and migration_status == "greenfield":
        return [
            "config says adoption.mode: coexist (this instance coexists with pre-existing "
            "project governance), but the lock records migration_status: greenfield (created "
            "in an empty repo) - these contradict. Re-run eif_init.py with "
            "--force --adoption-mode coexist --migration-status adopted to record the true "
            "history (do not hand-edit one file to match the other)."
        ]
    return []


def check_provenance(lock: dict | None) -> list[str]:
    """Informational, not failures - reported but does not flip overall ok
    to False. Branches on framework.source_type (adoption-hardening round's
    discriminated provenance contract - see
    core/schemas/framework-lock.schema.json): a git source can be dirty; a
    source-bundle source is always an unverified assertion by definition; an
    installed-package source has neither concept, but is still named so a
    doctor run always states plainly which kind of provenance this instance
    has. Whether an installed-package source's OWN provenance is still
    internally consistent (same version/resources as currently installed) is
    a separate, live-environment-dependent check the package wrapper adds
    (commands/doctor.py) - this shared script cannot assume it is running
    from an installed package at all."""
    if lock is None:
        return ["cannot check provenance: lock missing/invalid"]
    fw = lock.get("framework", {})
    source_type = fw.get("source_type")
    notes = []
    if source_type == "git":
        git = lock.get("git", {})
        if git.get("dirty"):
            notes.append(f"framework was DIRTY when this bundle was generated (ref {str(git.get('commit_sha', '?'))[:12]}) - "
                         f"the recorded ref does not exactly match what was materialized")
    elif source_type == "source-bundle":
        bundle = lock.get("source_bundle", {})
        notes.append(f"framework ref ({bundle.get('asserted_ref', '?')}) was ASSERTED via --framework-ref "
                     f"(a source-bundle export), not git-verified - provenance is only as trustworthy as "
                     f"whoever passed that flag")
        if bundle.get("dirty"):
            notes.append(f"framework was DIRTY when this bundle was generated (asserted ref {bundle.get('asserted_ref', '?')})")
    elif source_type == "installed-package":
        pkg = lock.get("package", {})
        notes.append(f"generated by installed package {pkg.get('distribution', '?')} {pkg.get('version', '?')} "
                     f"(Python {pkg.get('python_version', '?')}) - no git commit to report")
    return notes


def check_markers(instance_path: Path, entrypoint: str) -> list[str]:
    problems = []
    entry_path = instance_path / entrypoint
    if entry_path.exists():
        problems.extend(
            f"{entrypoint}: {p}" for p in check_marker_integrity(entry_path.read_text(encoding="utf-8"), EIF_BEGIN, EIF_END)
        )
    gi_path = instance_path / ".gitignore"
    if gi_path.exists():
        problems.extend(
            f".gitignore: {p}" for p in check_marker_integrity(gi_path.read_text(encoding="utf-8"), GITIGNORE_BEGIN, GITIGNORE_END)
        )
    return problems


def check_config_block_drift(config: dict | None, instance_path: Path, entrypoint: str) -> list[str]:
    """Independent-review addition: detects when .eif/config.yaml's
    adoption.mode / knowledge.root / knowledge.index_path no longer match
    what is actually written into the generated managed block - i.e.
    someone hand-edited config.yaml (or the entrypoint file) without
    re-running eif_init to regenerate. A stale generated block is worse
    than an honest doctor failure: left alone, it silently tells an agent
    the wrong authority framing or a knowledge path config no longer
    agrees with. Text-presence checks against known marker substrings,
    not a full re-render - eif_init.py's own rendering code is
    deliberately NOT bundled (see instance-contract.md#validation-
    surface), so this doctor command cannot reconstruct the exact
    expected block byte-for-byte; it can still catch the cases that
    matter without that."""
    if config is None:
        return []  # config's own schema check already failed; do not double-report here
    entry_path = instance_path / entrypoint
    if not entry_path.exists():
        return []  # missing-entrypoint is check_markers'/consistency's concern, not this one's
    text = entry_path.read_text(encoding="utf-8", errors="replace")
    if EIF_BEGIN not in text or EIF_END not in text:
        return []  # no managed block yet (or malformed - check_markers reports that) - nothing to drift-check
    block_text = text[text.index(EIF_BEGIN):text.index(EIF_END) + len(EIF_END)]

    problems = []
    adoption_mode = (config.get("adoption") or {}).get("mode", "greenfield")
    has_greenfield_text = GREENFIELD_MARKER_TEXT in block_text
    has_coexist_text = COEXIST_MARKER_TEXT in block_text
    if adoption_mode == "coexist" and not has_coexist_text:
        problems.append(
            f"config says adoption.mode: coexist, but {entrypoint}'s generated block does not have the "
            f"coexistence authority framing (still greenfield, or corrupted) - run eif_init.py again "
            f"(a routine upgrade) to regenerate it"
        )
    elif adoption_mode == "greenfield" and not has_greenfield_text:
        problems.append(
            f"config says adoption.mode: greenfield, but {entrypoint}'s generated block does not have the "
            f"greenfield authority framing (still coexistence, or corrupted) - run eif_init.py again "
            f"(a routine upgrade) to regenerate it"
        )

    knowledge = config.get("knowledge") or {}
    knowledge_root = knowledge.get("root", "knowledge")
    knowledge_index_path = knowledge.get("index_path", f"{knowledge_root.rstrip('/')}/index.md")
    # knowledge.managed absent means a config written before this field
    # existed - same backward-compat default eif_init.py itself uses.
    knowledge_managed = knowledge.get("managed", True)
    if knowledge_managed:
        if knowledge_index_path not in block_text:
            problems.append(
                f"config says knowledge.index_path: {knowledge_index_path!r}, but {entrypoint}'s generated block "
                f"does not reference that path - run eif_init.py again (a routine upgrade) to regenerate it"
            )
        # The generated search command quotes the interpolated knowledge root
        # (shell-safety fix - a root with a space would otherwise split into two
        # arguments). Match the quoted form the current template emits.
        if f'--knowledge-root "{knowledge_root}"' not in block_text:
            problems.append(
                f"config says knowledge.root: {knowledge_root!r}, but {entrypoint}'s generated block's search "
                f"command does not reference it (as a quoted --knowledge-root argument) - run eif_init.py "
                f"again (a routine upgrade) to regenerate it"
            )
    else:
        # Unmanaged/external knowledge: the block must say so, not silently
        # carry stale managed-mode text from before knowledge.managed was
        # flipped to false without regenerating (prior private-pilot finding
        # - see eif_init.py's UNMANAGED_KNOWLEDGE_BEFORE_WORK).
        if UNMANAGED_KNOWLEDGE_TEXT not in block_text:
            problems.append(
                f"config says knowledge.managed: false, but {entrypoint}'s generated block does not have the "
                f"unmanaged-knowledge framing (still references a managed index, or is stale) - run "
                f"eif_init.py again (a routine upgrade) to regenerate it"
            )
    return problems


def check_knowledge_index_drift(instance_path: Path, lock: dict | None) -> list[str]:
    """Independent-review addition: if the lock records an EIF-managed
    knowledge index (i.e. eif_init.py actually created/regenerated one
    the last time it ran), verify it is still exactly what was generated
    - byte-for-byte hash match - and still carries EIF's own ownership
    marker. Catches a hand-edited index file, which would otherwise sit
    silently out of sync with what the lock (and knowledge.managed: true
    in config) claims is true."""
    if lock is None:
        return []
    ki = lock.get("knowledge_index")
    if ki is None:
        return []  # no index was EIF-managed as of the last real run - nothing to check
    index_path = instance_path / ki["path"]
    if not index_path.exists():
        return [f"lock records an EIF-managed knowledge index at {ki['path']!r}, but that file is missing"]
    raw = index_path.read_bytes()
    if not raw.startswith(MANAGED_INDEX_MARKER.encode("utf-8")):
        return [f"knowledge index at {ki['path']!r} is recorded as EIF-managed in the lock but has lost its "
                f"ownership marker - was it hand-edited? Delete it and run eif_init.py again to regenerate."]
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != ki["sha256"]:
        return [f"knowledge index at {ki['path']!r} does not match the hash recorded when it was generated "
                f"(hand-edited since, or eif_init.py was interrupted) - run eif_init.py again to regenerate it"]
    return []


def check_integrations(
    config: dict | None,
    framework_root: Path | None = None,
    instance_path: Path | None = None,
) -> list[str]:
    """Compatibility wrapper for callers that need only doctor failures.

    Health itself is behavioral and machine-readable through
    evaluate_integrations(); this wrapper applies fail-closed/degrade policy.
    """
    root = framework_root or Path(__file__).resolve().parent.parent
    instance = instance_path or Path.cwd()
    return integration_problems(config, evaluate_integrations(config, root, instance))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--framework-root", required=True, help="Where core/schemas/ lives (the framework checkout, or this instance's own .eif/runtime bundle)")
    ap.add_argument("--instance-path", default=".", help="Instance root to verify. Default: current directory.")
    ap.add_argument("--integration-report", default=None, help="Optional path for a machine-readable integration health report.")
    args = ap.parse_args(argv)

    framework_root = Path(args.framework_root).resolve()
    instance_path = Path(args.instance_path).resolve()

    report = Report()

    config_path = instance_path / ".eif" / "config.yaml"
    lock_path = instance_path / ".eif" / "framework.lock.yaml"
    config = _load_yaml(config_path)
    lock = _load_yaml(lock_path)

    report.add("config schema (.eif/config.yaml)", check_schema(framework_root, config_path, "eif-config.schema.json", str(config_path)))
    report.add("lock schema (.eif/framework.lock.yaml)", check_schema(framework_root, lock_path, "framework-lock.schema.json", str(lock_path)))

    if lock is not None:
        report.add("manifest digest self-consistency", check_manifest_digest(lock))
        hash_mismatches, missing, unexpected = check_bundle_files(instance_path, lock)
        report.add("bundle file hashes", [f"hash mismatch (file changed since generation): {p}" for p in hash_mismatches])
        report.add("missing managed files", [f"manifested but missing on disk: {p}" for p in missing])
        report.add("unexpected managed files (outside manifest, not README.md/__pycache__)", unexpected)

    report.add("config/adapter/lock/entrypoint consistency", check_consistency(config, lock, instance_path))
    report.add("migration provenance consistency (adoption.mode vs migration_status)", check_migration_provenance_consistency(config, lock))
    report.add("size budget (current content vs configured limit)", check_size_budget_drift(config, lock, instance_path))

    provenance_notes = check_provenance(lock)
    if provenance_notes:
        print("note: provenance")
        for n in provenance_notes:
            print(f"  - {n}")

    entrypoint = (lock.get("adapter") or {}).get("entrypoint", "CLAUDE.md") if lock else "CLAUDE.md"
    report.add(f"marker integrity ({entrypoint}, .gitignore)", check_markers(instance_path, entrypoint))
    report.add("config/generated-block drift (adoption.mode, knowledge paths)", check_config_block_drift(config, instance_path, entrypoint))
    report.add("knowledge index drift (ownership marker, hash)", check_knowledge_index_drift(instance_path, lock))
    integration_results = evaluate_integrations(config, framework_root, instance_path)
    for result in integration_results:
        print(
            f"note: integration {result['integration']} provider={result['provider']!r} "
            f"state={result['state']} version={result['version']['detected']!r}"
        )
        for capability in result["capabilities"]:
            if capability["status"] != "pass":
                print(f"  - {capability['id']}: {capability['status']} ({capability['evidence']['summary']})")
    report.add("optional integration result schema", validate_health_results(integration_results, framework_root))
    report.add("optional integrations (behavioral health and failure policy)", integration_problems(config, integration_results))
    if args.integration_report:
        report_path = Path(args.integration_report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps({"schema_version": 1, "results": integration_results}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    ok = report.print()
    print(f"\neif-verify-runtime: {'all checks passed' if ok else 'FAILED - see above'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
