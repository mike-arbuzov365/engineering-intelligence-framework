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
        if not (
            workspace_new.returncode == 0
            and profile_install.returncode == 0
            and workspace_committed
        ):
            passed = sum(results)
            print(f"EIF-RESULT: passed={passed} total={len(results)}")
            return 1

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
        if not committed:
            passed = sum(results)
            print(f"EIF-RESULT: passed={passed} total={len(results)}")
            return 1

        session_task = project / "planning" / "package-smoke-session.md"
        session_task.parent.mkdir(parents=True, exist_ok=True)
        session_task.write_text(
            "# Package smoke session\n\nExercise installed session tooling.\n",
            encoding="utf-8",
        )
        session_seeded = timed(
            "commit session source artifact",
            lambda: commit(project, "Seed package smoke session"),
        )
        resolved = timed(
            "resolve project identity",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "projects",
                    "resolve",
                    "design-project",
                    "--registry",
                    str(registry),
                ],
                cwd=workspace,
                timeout_s=30,
            ),
        )
        checkpointed = timed(
            "write session checkpoint",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "session",
                    "checkpoint",
                    "--session-id",
                    "PACKAGE-SMOKE",
                    "--source-artifact",
                    "planning/package-smoke-session.md",
                    "--goal",
                    "Exercise installed session tooling.",
                    "--in-scope",
                    "Installed-wheel continuity",
                    "--no-touch",
                    "External systems",
                    "--approval-state",
                    "not_required",
                    "--next-action",
                    "Run the resume audit.",
                    "--continuation-mode",
                    "same_chat",
                ],
                cwd=project,
                timeout_s=30,
            ),
        )
        checkpoint = project / ".session-context" / "PACKAGE-SMOKE.md"
        validated = timed(
            "validate session checkpoint",
            lambda: bounded_run(
                [str(eifctl), "session", "validate", str(checkpoint)],
                cwd=project,
                timeout_s=30,
            ),
        )
        audited = timed(
            "audit session resume",
            lambda: bounded_run(
                [str(eifctl), "session", "resume-audit", str(checkpoint)],
                cwd=project,
                timeout_s=30,
            ),
        )
        handoff = timed(
            "render adapter handoff",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "session",
                    "handoff",
                    str(checkpoint),
                    "--mode",
                    "auto",
                ],
                cwd=project,
                timeout_s=30,
            ),
        )
        refused_open = timed(
            "refuse unverified adapter open",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "session",
                    "handoff",
                    str(checkpoint),
                    "--mode",
                    "auto",
                    "--open",
                ],
                cwd=project,
                timeout_s=30,
            ),
        )
        results.append(
            check(
                "installed project resolution and session checkpoint journey pass",
                session_seeded
                and resolved.returncode == 0
                and checkpointed.returncode == 0
                and validated.returncode == 0
                and audited.returncode == 0
                and checkpoint.is_file()
                and "project_name=design-project" in resolved.stdout
                and "PASS" in validated.stdout
                and "PASS" in audited.stdout,
                resolved.stdout
                + resolved.stderr
                + checkpointed.stdout
                + checkpointed.stderr
                + validated.stdout
                + validated.stderr
                + audited.stdout
                + audited.stderr,
            )
        )

        results.append(
            check(
                "installed adapter handoff uses truthful manual fallback",
                handoff.returncode == 0
                and "strategy=manual_new_chat" in handoff.stdout
                and "candidate_link=codex://threads/new?" in handoff.stdout
                and "candidate_link_status=manual_only_canary_inconclusive"
                in handoff.stdout
                and refused_open.returncode != 0
                and "FAIL automatic open is not verified for adapter codex"
                in refused_open.stderr,
                handoff.stdout
                + handoff.stderr
                + refused_open.stdout
                + refused_open.stderr,
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
                apply.returncode == 0
                and (
                    project
                    / ".eif"
                    / "workspace-runtime"
                    / "skills"
                    / "run-graphic-design-project"
                    / "tests"
                    / "contract.yaml"
                ).is_file()
                and "tests/contract.yaml"
                not in (
                    project
                    / ".agents"
                    / "skills"
                    / "run-graphic-design-project"
                    / "SKILL.md"
                ).read_text(encoding="utf-8"),
                apply.stdout + apply.stderr,
            )
        )

        blocked_delivery = timed(
            "block package without approval",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "delivery",
                    "check",
                    "--action",
                    "package",
                    "--scope",
                    "package-smoke-final",
                    "--instance-path",
                    str(project),
                ],
                cwd=project,
                timeout_s=30,
            ),
        )
        approval_evidence = project / "planning" / "approvals" / "package-smoke.md"
        approval_evidence.parent.mkdir(parents=True, exist_ok=True)
        approval_evidence.write_text("# Synthetic owner approval evidence\n", encoding="utf-8")
        approval_state = (
            project / ".eif" / "local-state" / "design-delivery-approval.yaml"
        )
        approval_state.parent.mkdir(parents=True, exist_ok=True)
        approval_state.write_text(
            "schema_version: 1\n"
            "profile: graphic-design\n"
            "package_allowed: true\n"
            "decision:\n"
            "  owner: package-smoke-owner\n"
            "  scope: package-smoke-final\n"
            "  actions:\n"
            "  - package\n"
            "  decided_at: '2000-01-01T00:00:00Z'\n"
            "  valid_until: '2099-01-01T00:00:00Z'\n"
            "  evidence_ref: planning/approvals/package-smoke.md\n",
            encoding="utf-8",
        )
        approved_delivery = timed(
            "allow exact-scope package with valid approval",
            lambda: bounded_run(
                [
                    str(eifctl),
                    "delivery",
                    "check",
                    "--action",
                    "package",
                    "--scope",
                    "package-smoke-final",
                    "--instance-path",
                    str(project),
                ],
                cwd=project,
                timeout_s=30,
            ),
        )
        results.append(
            check(
                "installed delivery guard blocks by default and accepts exact owner evidence",
                blocked_delivery.returncode != 0
                and "package_allowed defaults to false" in blocked_delivery.stderr
                and approved_delivery.returncode == 0
                and "enforcement=machine" in approved_delivery.stdout
                and "approval_origin=owner_gate" in approved_delivery.stdout
                and "external_shell_enforcement=instruction_only"
                in approved_delivery.stdout,
                blocked_delivery.stdout
                + blocked_delivery.stderr
                + approved_delivery.stdout
                + approved_delivery.stderr,
            )
        )

        skill_check = timed(
            "check installed skill contracts",
            lambda: bounded_run(
                [str(eifctl), "skills", "check"],
                cwd=host_root,
                timeout_s=60,
            ),
        )
        results.append(
            check(
                "installed skill contracts validate without model calls",
                skill_check.returncode == 0
                and "EIF-RESULT: passed=15 total=15" in skill_check.stdout,
                skill_check.stdout + skill_check.stderr,
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
