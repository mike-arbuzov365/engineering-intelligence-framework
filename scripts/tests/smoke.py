#!/usr/bin/env python3
"""Compact local smoke suite - the critical user flow only, not
permutations. Target ~10s, measured ~20-21s wall-clock (see note below on
why the gap is real per-call product work, not test bloat). This is the
routine PR gate (D-14): replaces routine, automatic CI execution of the
full adapter/package/benchmark test suites (see
docs/architecture/HOW-EIF-WORKS.md#ci-and-quality-gates and
.github/workflows/release-check.yml for what still runs, and only
manually, before a technical-preview or release).

Covers:
  - core sanity: schemas parse, marker block integrity, privacy scan,
    one synthetic demo smoke, doctor catching an obviously corrupted
    managed block
  - all four v0.1 adapters (claude-code, cursor, codex, hermes):
    greenfield init, correct active entrypoint, exactly one EIF block,
    doctor passes, repeat init is idempotent, project-owned text survives.
    All four are supported adapters (D-16, 2026-07-27, retiring the
    two-tier split D-09 recorded), which is why all four are checked here
    rather than two being checked as defense-in-depth - see
    adapters/README.md for the frozen scope.
  - one minimal adapter-switch cycle touching all four adapters
    (claude-code -> cursor -> codex -> hermes -> claude-code), proving
    switching doesn't corrupt files, without the full 12-directed-pair
    matrix

Deliberately NOT here: dozens of boundary/depth/platform variations,
exact historical check counts, or anything whose only purpose was to
prove PR text. See .github/workflows/release-check.yml for what moved to
the manual release gate instead of being deleted outright.

Each real check shells out to the actual eif_init.py/eif_verify_runtime.py
scripts (not a reimplementation), and each of those calls does real,
necessary work (framework-runtime bundle hash/refresh, git provenance) -
measured at roughly 1.4-2.3s per call, not just interpreter startup
(~0.3s). With ~25 such calls required to cover the checklist above, the
independent jobs run concurrently (a ThreadPoolExecutor - subprocess.run()
releases the GIL while waiting on the child, so this is real wall-clock
parallelism, not concurrency theater): this alone cut a naive serial run
from ~52s to ~21s. The remaining ~21s is the switch cycle's own
irreducible critical path - 9 sequential calls (each transition depends
on the previous one's on-disk state, so it cannot parallelize internally)
that no other job's parallel execution can shorten. Cutting the
per-transition doctor call would close the gap to the ~10s target, but
this suite ranks correctness above gate cost - so the extra ~1s versus
the stated max is spent on a real check, not padding, and is reported
as-is rather than hidden.

Usage:
    python scripts/tests/smoke.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
INIT = FRAMEWORK_ROOT / "scripts" / "eif_init.py"
DOCTOR = FRAMEWORK_ROOT / "scripts" / "eif_verify_runtime.py"
PRIVACY_SCAN = FRAMEWORK_ROOT / "scripts" / "eif_privacy_scan.py"

Result = tuple[bool, str]

# (adapter name, entrypoint path relative to instance root) - the default,
# no-parent-directory, no-coexistence entrypoint each adapter resolves to
# on a plain greenfield init. Codex and Hermes have dynamic resolution in
# general (see adapters/codex/README.md, adapters/hermes/README.md) but
# both have one unambiguous default when nothing else is present. All four
# are supported adapters (D-16); the differences between them are hook
# mechanics, not status.
ADAPTERS = [
    ("claude-code", "CLAUDE.md"),
    ("cursor", ".cursor/rules/eif/governance.mdc"),
    ("codex", "AGENTS.md"),
    ("hermes", ".hermes.md"),
]


def check(name: str, condition: bool, detail: str = "") -> Result:
    line = f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else "")
    return condition, line


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def eif_block_count(text: str) -> int:
    return text.count("<!-- EIF:BEGIN")


def init_ok(instance: Path, adapter: str, force: bool = False, locale: str | None = None, adoption_mode: str | None = None) -> subprocess.CompletedProcess:
    # --allow-dirty: this suite runs against a working tree mid-edit, not a
    # clean commit - real provenance/dirty-tracking is a package-build
    # concern (test_package_build.py), not a local dev-loop smoke concern.
    cmd = [
        sys.executable, str(INIT),
        "--framework-root", str(FRAMEWORK_ROOT),
        "--instance-path", str(instance),
        "--project-name", "smoke-test",
        "--adapter", adapter,
        "--allow-dirty",
    ]
    if force:
        cmd.append("--force")
    if locale:
        cmd += ["--locale", locale]
    if adoption_mode:
        cmd += ["--adoption-mode", adoption_mode]
    return run(cmd)


def doctor_ok(instance: Path) -> subprocess.CompletedProcess:
    return run([sys.executable, str(DOCTOR), "--framework-root", str(FRAMEWORK_ROOT), "--instance-path", str(instance)])


# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------

def check_schemas_parse() -> list[Result]:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError

    schema_files = sorted((FRAMEWORK_ROOT / "core" / "schemas").glob("*.schema.json"))
    failures = []
    for f in schema_files:
        try:
            Draft202012Validator.check_schema(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, SchemaError) as e:
            failures.append(f"{f.name}: {e}")
    return [check(
        f"all {len(schema_files)} core schemas parse and are self-consistent",
        not failures and len(schema_files) > 0,
        "; ".join(failures) or "no schema files found",
    )]


def check_privacy_scan() -> list[Result]:
    proc = run([sys.executable, str(PRIVACY_SCAN), "--repo", str(FRAMEWORK_ROOT)])
    return [check(
        "privacy scan reports 0 unsuppressed findings against the framework repo",
        proc.returncode == 0,
        proc.stdout + proc.stderr,
    )]


def check_package_sources_synced() -> list[Result]:
    """The installable package bundles copies of scripts/ and several docs
    trees; sync_package_sources.py is what keeps them byte-identical.

    Added after a pre-publication audit found two docs/product/ files that
    the sync declares as package resources and that had never been copied at
    all - the wheel would have shipped without them. That drift survived
    because the only sync check lived in the manual release gate, and a
    documentation-only change never reaches it. This is a file comparison,
    not a build, so it belongs in the fast loop a contributor runs before
    pushing rather than at release time when it is expensive to be wrong.
    """
    proc = run([sys.executable, str(FRAMEWORK_ROOT / "scripts" / "sync_package_sources.py"), "--check"])
    return [check(
        "package resource copies match their sources and contain no stale generated files",
        proc.returncode == 0,
        proc.stdout + proc.stderr,
    )]


def check_demo_smoke(tmp_path: Path) -> list[Result]:
    """One synthetic demo smoke: init a fresh instance and confirm the
    generated entrypoint has exactly one well-formed managed block -
    marker integrity and a working init in one check, not a full
    end-to-end journey (that lives in the manual release-check demo step)."""
    instance = tmp_path / "demo-smoke"
    proc = init_ok(instance, "claude-code")
    entry = instance / "CLAUDE.md"
    text = entry.read_text(encoding="utf-8") if entry.is_file() else ""
    return [check(
        "synthetic demo smoke: greenfield init produces exactly one managed block",
        proc.returncode == 0 and eif_block_count(text) == 1 and "<!-- EIF:END -->" in text,
        proc.stdout + proc.stderr,
    )]


def check_doctor_catches_corruption(tmp_path: Path) -> list[Result]:
    instance = tmp_path / "doctor-corruption"
    init_proc = init_ok(instance, "claude-code")
    entry = instance / "CLAUDE.md"
    if not entry.is_file():
        return [check(
            "doctor detects an obviously corrupted managed block (missing END marker)",
            False,
            f"setup init failed, nothing to corrupt: {init_proc.stdout + init_proc.stderr}",
        )]
    text = entry.read_text(encoding="utf-8")
    # Obviously corrupt: delete the END marker, leaving BEGIN with no partner.
    corrupted = text.replace("<!-- EIF:END -->", "")
    entry.write_text(corrupted, encoding="utf-8")
    proc = doctor_ok(instance)
    return [check(
        "doctor detects an obviously corrupted managed block (missing END marker)",
        proc.returncode != 0,
        proc.stdout + proc.stderr,
    )]


# --------------------------------------------------------------------------
# Four supported adapters (D-16 - see ADAPTERS)
# --------------------------------------------------------------------------

def check_adapter(tmp_path: Path, adapter: str, entry_rel: str) -> list[Result]:
    results: list[Result] = []
    instance = tmp_path / f"adapter-{adapter}"
    instance.mkdir()
    sentinel = instance / "PROJECT_OWNED.md"
    sentinel.write_text("# Real project content that must survive init.\n", encoding="utf-8")

    proc = init_ok(instance, adapter)
    results.append(check(f"{adapter}: greenfield init succeeds", proc.returncode == 0, proc.stdout + proc.stderr))

    entry = instance / entry_rel
    text = entry.read_text(encoding="utf-8") if entry.is_file() else ""
    results.append(check(f"{adapter}: correct active entrypoint exists ({entry_rel})", entry.is_file()))
    results.append(check(f"{adapter}: exactly one EIF block", eif_block_count(text) == 1, f"found {eif_block_count(text)}"))
    results.append(check(
        f"{adapter}: optional integration health/fallback pointer is discoverable",
        ".eif/runtime/integrations/README.md" in text
        and "Only `healthy` is usable without qualification" in text,
    ))

    doctor_proc = doctor_ok(instance)
    results.append(check(f"{adapter}: doctor passes after init", doctor_proc.returncode == 0, doctor_proc.stdout + doctor_proc.stderr))

    # Idempotent repeat: a routine upgrade (no --adapter, no --force) must
    # not duplicate the block or fail.
    repeat_proc = run([sys.executable, str(INIT), "--framework-root", str(FRAMEWORK_ROOT), "--instance-path", str(instance), "--allow-dirty"])
    repeat_text = entry.read_text(encoding="utf-8") if entry.is_file() else ""
    results.append(check(
        f"{adapter}: repeat init is idempotent (no duplicate block, no error)",
        repeat_proc.returncode == 0 and eif_block_count(repeat_text) == 1,
        repeat_proc.stdout + repeat_proc.stderr,
    ))

    results.append(check(
        f"{adapter}: project-owned text survives init and re-init",
        sentinel.is_file() and "Real project content" in sentinel.read_text(encoding="utf-8"),
    ))
    return results


# --------------------------------------------------------------------------
# Minimal 4-adapter switch cycle
# --------------------------------------------------------------------------

def check_switch_cycle(tmp_path: Path) -> list[Result]:
    """claude-code -> cursor -> codex -> hermes -> claude-code. Proves all
    four adapters participate in switching without the full 12-directed-
    pair matrix the old test_adapter_switch_matrix.py exhaustively covered
    - deliberately not reproduced anywhere; a corrupting transition would
    fail here regardless of which two adapters are involved. Exercising
    codex/hermes here is defense-in-depth (D-09 does not require them).

    Each reconfigure uses --adoption-mode greenfield: switching an
    EIF-managed instance to a different adapter is not "adopting a
    foreign project" - without it, the adoption-safety preflight
    correctly (and, for this cycle, unhelpfully) STOPs on the unedited
    "add your project rules here" placeholder EIF's own template leaves
    below the marker block on every switch-away. Project-content safety
    is still genuinely checked, just via the dedicated sentinel file
    below rather than the entrypoint file itself, which never holds real
    user content in this scenario.
    """
    results: list[Result] = []
    instance = tmp_path / "switch-cycle"
    instance.mkdir()
    sentinel = instance / "PROJECT_OWNED.md"
    sentinel.write_text("# Real project content that must survive every switch.\n", encoding="utf-8")

    cycle = ["claude-code", "cursor", "codex", "hermes", "claude-code"]
    entry_for = dict(ADAPTERS)
    # Hermes's tier-2 precedence adopts a pre-existing, non-empty AGENTS.md
    # rather than creating .hermes.md - verified directly (a codex->hermes
    # transition writes into AGENTS.md). See
    # eif_adapters.py:resolve_hermes_active_source, tier 2.
    destination_override = {("codex", "hermes"): "AGENTS.md"}

    init_ok(instance, cycle[0])
    for step, (src, dst) in enumerate(zip(cycle, cycle[1:]), start=1):
        proc = init_ok(instance, dst, force=True, adoption_mode="greenfield")
        results.append(check(f"switch {step} ({src}->{dst}): reconfigure succeeds", proc.returncode == 0, proc.stdout + proc.stderr))

        dst_rel = destination_override.get((src, dst), entry_for[dst])
        dst_entry = instance / dst_rel
        dst_text = dst_entry.read_text(encoding="utf-8") if dst_entry.is_file() else ""
        results.append(check(f"switch {step} ({src}->{dst}): destination entrypoint has exactly one EIF block ({dst_rel})", eif_block_count(dst_text) == 1))

        src_rel = entry_for[src]
        if src_rel != dst_rel:
            src_entry = instance / src_rel
            src_text = src_entry.read_text(encoding="utf-8") if src_entry.is_file() else ""
            results.append(check(f"switch {step} ({src}->{dst}): old entrypoint no longer has an active EIF block", eif_block_count(src_text) == 0))

        doctor_proc = doctor_ok(instance)
        results.append(check(f"switch {step} ({src}->{dst}): doctor passes", doctor_proc.returncode == 0, doctor_proc.stdout + doctor_proc.stderr))

    results.append(check(
        "switch cycle: project-owned text survives all four transitions",
        sentinel.is_file() and "Real project content" in sentinel.read_text(encoding="utf-8"),
    ))
    return results


def main() -> int:
    start = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="eif-smoke-") as tmp:
        tmp_path = Path(tmp)

        jobs = [
            lambda: check_schemas_parse(),
            lambda: check_privacy_scan(),
            lambda: check_package_sources_synced(),
            lambda: check_demo_smoke(tmp_path),
            lambda: check_doctor_catches_corruption(tmp_path),
            *(lambda a=adapter, e=entry_rel: check_adapter(tmp_path, a, e) for adapter, entry_rel in ADAPTERS),
            lambda: check_switch_cycle(tmp_path),
        ]

        # Every job targets its own temp instance directory - no shared
        # mutable state, so real wall-clock parallelism is safe. Submitted
        # in a fixed order and drained in that same order so output stays
        # deterministic even though completion order is not.
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            futures = [pool.submit(job) for job in jobs]
            job_results = [future.result() for future in futures]

    all_results: list[Result] = [r for job_result in job_results for r in job_result]
    for _, line in all_results:
        print(line)

    elapsed = time.monotonic() - start
    passed = sum(1 for ok, _ in all_results if ok)
    total = len(all_results)
    print(f"EIF-RESULT: passed={passed} total={total}")
    print(f"\nsmoke: {passed}/{total} passed in {elapsed:.1f}s")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
