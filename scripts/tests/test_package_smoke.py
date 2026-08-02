#!/usr/bin/env python3
"""Fast installed-wheel smoke for ordinary package-relevant changes.

One wheel, one virtual environment, one Codex + graphic-design project:
build -> install -> workspace/profile -> project -> doctor. The exhaustive
package matrix, corruption cases, adapter/integration permutations, sdist
rebuild and reinstall remain in test_package_build.py and run once at the
local release gate.

Usage:
    python scripts/tests/test_package_smoke.py
"""
from __future__ import annotations

import sys
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, TypeVar

from test_package_build import FRAMEWORK_ROOT, clean_checkout_export, run

T = TypeVar("T")


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else "")
    )
    return condition


def timed(name: str, action: Callable[[], T]) -> T:
    started = time.monotonic()
    print(f"STAGE {name}: start", flush=True)
    try:
        return action()
    finally:
        print(f"STAGE {name}: done in {time.monotonic() - started:.1f}s", flush=True)


def bounded_run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout_s: float = 60,
) -> subprocess.CompletedProcess:
    try:
        return run(cmd, cwd=cwd, timeout_s=timeout_s)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        return subprocess.CompletedProcess(
            exc.cmd,
            124,
            stdout=stdout,
            stderr=f"timed out after {timeout_s:.0f}s",
        )


def executable(env_dir: Path, stem: str) -> Path:
    if sys.platform == "win32":
        return env_dir / "Scripts" / f"{stem}.exe"
    return env_dir / "bin" / stem


def commit(repo: Path, message: str) -> bool:
    add = bounded_run(["git", "add", "-A"], cwd=repo, timeout_s=30)
    saved = bounded_run(
        [
            "git",
            "-c",
            "user.name=EIF Package Smoke",
            "-c",
            "user.email=eif-package-smoke@example.invalid",
            "commit",
            "-m",
            message,
        ],
        cwd=repo,
        timeout_s=30,
    )
    return add.returncode == 0 and saved.returncode == 0


def main() -> int:
    started = time.monotonic()
    results: list[bool] = []

    sync = timed(
        "package source sync",
        lambda: bounded_run(
            [
                sys.executable,
                str(FRAMEWORK_ROOT / "scripts" / "sync_package_sources.py"),
                "--check",
            ],
            timeout_s=30,
        ),
    )
    results.append(
        check(
            "package copies match their sources",
            sync.returncode == 0,
            sync.stdout + sync.stderr,
        )
    )

    with tempfile.TemporaryDirectory(prefix="eif-package-smoke-test-") as raw_tmp:
        tmp = Path(raw_tmp)

        source = tmp / "source"
        clean_checkout_export(FRAMEWORK_ROOT, source)
        dist = tmp / "dist"

        build = timed(
            "build one wheel",
            lambda: bounded_run(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--wheel",
                    "--outdir",
                    str(dist),
                ],
                cwd=source,
                timeout_s=120,
            ),
        )
        wheels = sorted(dist.glob("*.whl"))
        results.append(
            check(
                "one wheel builds",
                build.returncode == 0 and len(wheels) == 1,
                build.stdout + build.stderr,
            )
        )
        if len(wheels) != 1:
            passed = sum(results)
            print(f"EIF-RESULT: passed={passed} total={len(results)}")
            return 1

        # Reproduce the real designer-laptop failure from 0.2.6 without
        # letting the fixture's Git metadata affect the wheel build itself:
        # the installed environment lives below an unrelated dirty host
        # checkout, while the built artifact remains outside that checkout.
        host_root = tmp / "host-application"
        host_root.mkdir()
        host_init = timed(
            "create dirty host checkout fixture",
            lambda: bounded_run(
                ["git", "init", "-b", "main"], cwd=host_root, timeout_s=30
            ),
        )
        (host_root / "host-application.txt").write_text(
            "host-owned state\n", encoding="utf-8"
        )
        host_committed = (
            host_init.returncode == 0
            and commit(host_root, "Seed unrelated host application")
        )
        (host_root / "unrelated-work-in-progress.txt").write_text(
            "dirty host change\n", encoding="utf-8"
        )
        results.append(
            check(
                "unrelated dirty host checkout fixture is ready",
                host_committed,
                host_init.stdout + host_init.stderr,
            )
        )

        env_dir = host_root / "venv"
        venv_create = timed(
            "create virtual environment",
            lambda: bounded_run(
                [sys.executable, "-m", "venv", str(env_dir)],
                timeout_s=90,
            ),
        )
        results.append(
            check(
                "clean virtual environment is ready",
                venv_create.returncode == 0,
                venv_create.stdout + venv_create.stderr,
            )
        )
        if venv_create.returncode != 0:
            passed = sum(results)
            print(f"EIF-RESULT: passed={passed} total={len(results)}")
            return 1
        pip = executable(env_dir, "pip")
        eifctl = executable(env_dir, "eifctl")
        install = timed(
            "install wheel",
            lambda: bounded_run(
                [
                    str(pip),
                    "install",
                    "--quiet",
                    "--disable-pip-version-check",
                    str(wheels[0]),
                ],
                timeout_s=180,
            ),
        )
        results.append(
            check(
                "wheel installs once in a clean environment",
                install.returncode == 0 and eifctl.is_file(),
                install.stdout + install.stderr,
            )
        )

        workspace = host_root / "designer-eif"
        project = host_root / "design-project"
        workspace_new = timed(
            "create designer workspace",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "workspace",
                    "new",
                    str(workspace),
                    "--workspace-name",
                    "designer-eif",
                    "--adapter",
                    "codex",
                    "--locale",
                    "uk",
                ],
                cwd=host_root,
                timeout_s=90,
            ),
        )
        profile_install = timed(
            "install graphic-design profile",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "workspace",
                    "profile",
                    "install",
                    "graphic-design",
                    "--workspace-path",
                    str(workspace),
                ],
                cwd=host_root,
                timeout_s=60,
            ),
        )
        workspace_committed = False
        if workspace_new.returncode == 0 and profile_install.returncode == 0:
            workspace_committed = timed(
                "commit designer workspace",
                lambda: commit(workspace, "Bootstrap designer EIF workspace"),
            )
        workspace_lock = workspace / ".eif" / "framework.lock.yaml"
        workspace_lock_text = (
            workspace_lock.read_text(encoding="utf-8")
            if workspace_lock.is_file()
            else ""
        )
        results.append(
            check(
                "designer workspace ignores the dirty unrelated host checkout",
                workspace_new.returncode == 0
                and profile_install.returncode == 0
                and workspace_committed
                and "source_type: installed-package" in workspace_lock_text
                and "dirty:" not in workspace_lock_text,
                workspace_new.stdout
                + workspace_new.stderr
                + profile_install.stdout
                + profile_install.stderr
                + workspace_lock_text,
            )
        )

        registry = workspace / ".eif" / "projects.yaml"
        project_new = timed(
            "create Codex designer project",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "new",
                    str(project),
                    "--project-name",
                    "design-project",
                    "--adapter",
                    "codex",
                    "--locale",
                    "uk",
                    "--profile",
                    "graphic-design",
                    "--registry",
                    str(registry),
                ],
                cwd=host_root,
                timeout_s=90,
            ),
        )
        committed = False
        if project_new.returncode == 0:
            committed = timed(
                "commit designer project state",
                lambda: commit(workspace, "Register design project")
                and commit(project, "Bootstrap design project"),
            )
        results.append(
            check(
                "Codex designer project is registered cleanly",
                committed,
                project_new.stdout + project_new.stderr,
            )
        )

        apply = timed(
            "materialize profile",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "projects",
                    "upgrade",
                    "--registry",
                    str(registry),
                    "--apply",
                ],
                cwd=workspace,
                timeout_s=120,
            ),
        )
        results.append(
            check(
                "workspace profile materializes",
                apply.returncode == 0,
                apply.stdout + apply.stderr,
            )
        )

        doctor = timed(
            "doctor",
            lambda: bounded_run(
                [str(eifctl), "doctor", "--instance-path", str(project)],
                cwd=host_root,
                timeout_s=60,
            ),
        )
        results.append(
            check(
                "installed Codex designer context is active",
                doctor.returncode == 0
                and "instruction: AGENTS.md (codex)" in doctor.stdout
                and "profile: graphic-design" in doctor.stdout
                and "review-graphic-design-delivery" in doctor.stdout
                and "run-graphic-design-project" in doctor.stdout
                and "project memory: managed at knowledge" in doctor.stdout
                and "deferred until the first durable knowledge artifact"
                in doctor.stdout,
                doctor.stdout + doctor.stderr,
            )
        )

    passed = sum(results)
    total = len(results)
    duration = time.monotonic() - started
    print(f"EIF-RESULT: passed={passed} total={total}")
    print(f"test_package_smoke: {passed}/{total} passed in {duration:.1f}s")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
