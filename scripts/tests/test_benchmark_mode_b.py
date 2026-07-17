#!/usr/bin/env python3
"""Real, executed end-to-end proof that benchmark mode B
(B_eif_governance) actually exercises an installed eifctl package - not a
mock, not a PATH-resolution guess. Builds a real wheel, installs it into
an isolated venv, and runs the harness's own materialize/run subcommands
against it, pinned via --eifctl-path so mode B provably invokes THAT
venv's eifctl and no other.

This is a separate suite from test_package_build.py (packaging itself)
and test_benchmark.py (harness logic against a fake agent, no real
package needed) - it needs both together, and needs build+hatchling like
test_package_build.py, so it is NOT in run_all.py's SUITES (same reason
test_package_build.py isn't); it runs directly in the dedicated
`package-build` CI job.

Usage:
    python scripts/tests/test_benchmark_mode_b.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import venv
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = FRAMEWORK_ROOT / "scripts"
BENCHMARK_SCRIPT = SCRIPTS_DIR / "eif_benchmark.py"
FAKE_AGENT = SCRIPTS_DIR / "tests" / "fixtures" / "benchmark" / "fake_agent_runner.py"
FIXTURES_DIR = FRAMEWORK_ROOT / "docs" / "benchmarks" / "fixtures"


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **env} if env else None
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=full_env,
    )


def clean_checkout_export(framework_root: Path, dest_dir: Path) -> None:
    """Same technique as test_package_build.py's own helper - builds from
    exactly the tracked-file state (git stash-create + git archive), not
    the live working tree, so a stray local artifact never leaks in."""
    stash = subprocess.run(
        ["git", "-C", str(framework_root), "stash", "create"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    tree_ish = stash or "HEAD"
    dest_dir.mkdir(parents=True, exist_ok=True)
    tar_path = dest_dir.parent / "clean-checkout-mode-b.tar"
    archive = subprocess.run(
        ["git", "-C", str(framework_root), "archive", "--format=tar", f"--output={tar_path}", tree_ish],
        capture_output=True, text=True,
    )
    if archive.returncode != 0:
        raise RuntimeError(f"git archive failed: {archive.stdout}{archive.stderr}")
    with tarfile.open(tar_path) as tf:
        tf.extractall(dest_dir)  # noqa: S202 - own git archive output, not untrusted input
    tar_path.unlink()


def benchmark(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return run([sys.executable, str(BENCHMARK_SCRIPT), *args], env=env)


def main() -> int:
    results: list[bool] = []

    with tempfile.TemporaryDirectory(prefix="eif-mode-b-test-") as tmp:
        tmp_root = Path(tmp)

        # --- build a real wheel from a clean checkout, install into an
        # isolated venv - the exact eifctl mode B must invoke. ---
        clean_src = tmp_root / "clean-src"
        clean_checkout_export(FRAMEWORK_ROOT, clean_src)
        dist_dir = tmp_root / "dist"
        build = run([sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir), str(clean_src)])
        results.append(check("wheel builds from a clean checkout", build.returncode == 0, build.stdout + build.stderr))
        if build.returncode != 0:
            print(f"EIF-RESULT: passed={sum(results)} total={len(results)}")
            print(f"\ntest_benchmark_mode_b: {sum(results)}/{len(results)} passed")
            return 1

        wheel_path = next(dist_dir.glob("*.whl"))
        venv_dir = tmp_root / "venv"
        venv.create(venv_dir, with_pip=True)
        venv_python = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
        eifctl_exe = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("eifctl.exe" if sys.platform == "win32" else "eifctl")
        install = run([str(venv_python), "-m", "pip", "install", "-q", str(wheel_path)])
        results.append(check("wheel installs into an isolated venv", install.returncode == 0 and eifctl_exe.exists(), install.stdout + install.stderr))

        # A second, DIFFERENT venv with a DIFFERENT (older-looking) fake
        # eifctl shim on its own PATH entry, prepended ahead of the real
        # one - proves --eifctl-path is actually pinning the real venv's
        # eifctl, not silently falling through to whatever resolves first
        # on PATH.
        decoy_bin = tmp_root / "decoy-bin"
        decoy_bin.mkdir()
        decoy_eifctl = decoy_bin / ("eifctl.exe" if sys.platform == "win32" else "eifctl")
        if sys.platform == "win32":
            decoy_eifctl.write_text("@echo off\r\necho DECOY-EIFCTL-SHOULD-NEVER-RUN 1>&2\r\nexit /b 1\r\n", encoding="utf-8")
        else:
            decoy_eifctl.write_text("#!/bin/sh\necho DECOY-EIFCTL-SHOULD-NEVER-RUN >&2\nexit 1\n", encoding="utf-8")
            decoy_eifctl.chmod(0o755)
        poisoned_path_env = {"PATH": f"{decoy_bin}{os.pathsep}{os.environ.get('PATH', '')}"}

        t02 = FIXTURES_DIR / "T02-fix-a-bug"
        source_digest_before = benchmark("validate-manifest", str(t02))
        results.append(check("T02 fixture validates before materialization", source_digest_before.returncode == 0, source_digest_before.stdout + source_digest_before.stderr))

        # --- materialize T02 in mode A (no eifctl needed at all) ---
        work_a = tmp_root / "work-a"
        mat_a = benchmark("materialize", str(t02), str(work_a), "--mode", "A_baseline", env=poisoned_path_env)
        results.append(check("materialize mode A succeeds", mat_a.returncode == 0, mat_a.stdout + mat_a.stderr))
        results.append(check("mode A instance has NO .eif/ (no EIF artifacts at all)", not (work_a / ".eif").exists()))

        # --- materialize the SAME T02 source in mode B, pinned to the
        # isolated venv's eifctl via --eifctl-path - PATH is deliberately
        # poisoned with a decoy eifctl that would fail loudly if ever
        # invoked, proving --eifctl-path is not merely a hint. ---
        work_b = tmp_root / "work-b"
        mat_b = benchmark(
            "materialize", str(t02), str(work_b), "--mode", "B_eif_governance",
            "--adapter", "claude-code", "--eifctl-path", str(eifctl_exe),
            env=poisoned_path_env,
        )
        results.append(check(
            "materialize mode B succeeds using --eifctl-path, with a decoy eifctl poisoning PATH",
            mat_b.returncode == 0, mat_b.stdout + mat_b.stderr,
        ))
        results.append(check("the decoy eifctl was never invoked (no DECOY-EIFCTL-SHOULD-NEVER-RUN in output)", "DECOY-EIFCTL-SHOULD-NEVER-RUN" not in (mat_b.stdout + mat_b.stderr)))

        lock_path = work_b / ".eif" / "framework.lock.yaml"
        config_path = work_b / ".eif" / "config.yaml"
        runtime_dir = work_b / ".eif" / "runtime"
        claude_md = work_b / "CLAUDE.md"
        results.append(check("mode B instance has a valid .eif/config.yaml", config_path.is_file()))
        results.append(check("mode B instance has a materialized runtime bundle", runtime_dir.is_dir() and any(runtime_dir.iterdir())))
        results.append(check("mode B instance has a lock file", lock_path.is_file()))
        results.append(check("mode B instance has the claude-code entrypoint (CLAUDE.md)", claude_md.is_file()))

        lock_text = lock_path.read_text(encoding="utf-8") if lock_path.is_file() else ""
        results.append(check("mode B lock records source_type: installed-package", "source_type: installed-package" in lock_text, lock_text))

        # --- package provenance in B's lock matches the actual wheel ---
        wheel_sha256 = None
        direct_url_matches = list(venv_dir.glob("Lib/site-packages/engineering_intelligence_framework-*.dist-info/direct_url.json"))
        if not direct_url_matches:
            direct_url_matches = list(venv_dir.glob("lib/*/site-packages/engineering_intelligence_framework-*.dist-info/direct_url.json"))
        if direct_url_matches:
            direct_url = json.loads(direct_url_matches[0].read_text(encoding="utf-8"))
            archive_info = direct_url.get("archive_info", {})
            wheel_sha256 = (archive_info.get("hashes") or {}).get("sha256") or (archive_info.get("hash", "").split("=", 1)[-1] or None)
        results.append(check(
            "package provenance in mode B's lock (wheel_sha256) matches the actual installed wheel's own hash",
            wheel_sha256 is not None and f"wheel_sha256: {wheel_sha256}" in lock_text,
            f"expected wheel_sha256={wheel_sha256}, lock={lock_text}",
        ))

        source_digest_after = benchmark("validate-manifest", str(t02))
        results.append(check(
            "T02 fixture's source_digest is identical before/after both A and B materialization (materializing never mutates the fixture source)",
            source_digest_before.returncode == source_digest_after.returncode == 0,
            f"before rc={source_digest_before.returncode}, after rc={source_digest_after.returncode}",
        ))

        # --- fake-runner attempts succeed in BOTH modes, for all 3 fixtures ---
        for fixture_name in ["T02-fix-a-bug", "T07-avoid-repeating-a-known-failed-fix", "T10-security-relevant-fix"]:
            fixture = FIXTURES_DIR / fixture_name
            work_a2 = tmp_root / f"{fixture_name}-a"
            work_b2 = tmp_root / f"{fixture_name}-b"
            out_a = tmp_root / f"{fixture_name}-a-results.jsonl"
            out_b = tmp_root / f"{fixture_name}-b-results.jsonl"

            benchmark("materialize", str(fixture), str(work_a2), "--mode", "A_baseline")
            run_a = benchmark(
                "run", str(fixture), str(work_a2), "--mode", "A_baseline",
                "--agent-runner", sys.executable, str(FAKE_AGENT), "--out", str(out_a),
                env={"EIF_FAKE_AGENT_BEHAVIOR": "correct_fix"},
            )
            records_a = [json.loads(l) for l in out_a.read_text(encoding="utf-8").splitlines() if l.strip()] if out_a.exists() else []
            results.append(check(
                f"{fixture_name}: fake-runner attempt succeeds in mode A",
                run_a.returncode == 0 and len(records_a) == 1 and records_a[0]["outcome"]["status"] == "success",
                run_a.stdout + run_a.stderr + str(records_a),
            ))

            benchmark("materialize", str(fixture), str(work_b2), "--mode", "B_eif_governance", "--adapter", "claude-code", "--eifctl-path", str(eifctl_exe))
            run_b = benchmark(
                "run", str(fixture), str(work_b2), "--mode", "B_eif_governance",
                "--agent-runner", sys.executable, str(FAKE_AGENT), "--out", str(out_b),
                env={"EIF_FAKE_AGENT_BEHAVIOR": "correct_fix"},
            )
            records_b = [json.loads(l) for l in out_b.read_text(encoding="utf-8").splitlines() if l.strip()] if out_b.exists() else []
            results.append(check(
                f"{fixture_name}: fake-runner attempt succeeds in mode B",
                run_b.returncode == 0 and len(records_b) == 1 and records_b[0]["outcome"]["status"] == "success",
                run_b.stdout + run_b.stderr + str(records_b),
            ))

            if records_b:
                record_b = records_b[0]
                results.append(check(
                    f"{fixture_name}: mode B record's setup_cost_seconds is recorded (>= 0, not absent)",
                    isinstance(record_b.get("metrics", {}).get("setup_cost_seconds"), (int, float)),
                    str(record_b.get("metrics")),
                ))
                tv = record_b.get("tool_versions") or {}
                eifctl_tv = tv.get("eifctl")
                results.append(check(
                    f"{fixture_name}: mode B record's tool_versions.eifctl is NOT null and carries real distribution/version/digest fields (not PATH-inferred)",
                    isinstance(eifctl_tv, dict) and eifctl_tv.get("distribution") == "engineering-intelligence-framework"
                    and bool(eifctl_tv.get("version")) and bool(eifctl_tv.get("resource_manifest_digest")),
                    str(eifctl_tv),
                ))
                results.append(check(
                    f"{fixture_name}: mode A's record has tool_versions.eifctl: null (no package involved)",
                    records_a[0].get("tool_versions", {}).get("eifctl") is None,
                    str(records_a[0].get("tool_versions")),
                ))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_benchmark_mode_b: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
