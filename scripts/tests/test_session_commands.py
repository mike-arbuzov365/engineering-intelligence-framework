#!/usr/bin/env python3
"""Behavioral tests для deterministic project resolution і session continuity."""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from engineering_intelligence_framework import cli  # noqa: E402
from engineering_intelligence_framework.commands import init_cmd  # noqa: E402

try:  # The first TDD run records a clean feature-missing failure.
    from engineering_intelligence_framework.commands import session as session_cmd  # noqa: E402
except ImportError:
    session_cmd = None


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    line = f"{'PASS' if condition else 'FAIL'} {name}"
    if detail and not condition:
        line += f": {detail}"
    return condition, line


def invoke(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    previous = Path.cwd()
    try:
        os.chdir(cwd)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = cli.main(argv)
    finally:
        os.chdir(previous)
    return rc, stdout.getvalue(), stderr.getvalue()


def git(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def commit_all(project: Path, message: str) -> None:
    add = git(project, "add", "-A")
    saved = git(
        project,
        "-c",
        "user.name=EIF Session Test",
        "-c",
        "user.email=eif-session-test@example.invalid",
        "commit",
        "-m",
        message,
    )
    if add.returncode != 0 or saved.returncode != 0:
        raise RuntimeError(add.stdout + add.stderr + saved.stdout + saved.stderr)


def rewrite_frontmatter(source: Path, target: Path, *, remove: str) -> None:
    text = source.read_text(encoding="utf-8")
    _, raw, body = text.split("---\n", 2)
    data = yaml.safe_load(raw)
    data.pop(remove, None)
    target.write_text(
        "---\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
        + "---\n"
        + body,
        encoding="utf-8",
    )


def main() -> int:
    results: list[tuple[bool, str]] = []
    results.append(check("session command module exists", session_cmd is not None))
    if session_cmd is None:
        for _, line in results:
            print(line)
        print(f"EIF-RESULT: passed=0 total={len(results)}")
        print(f"\ntest_session_commands: 0/{len(results)} passed")
        return 1

    real_init_run = init_cmd.run
    init_cmd.run = lambda argv: real_init_run([*argv, "--allow-dirty"])  # type: ignore[assignment]
    try:
        with tempfile.TemporaryDirectory(prefix="eif-session-test-") as raw_tmp:
            root = Path(raw_tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            registry = workspace / ".eif" / "projects.yaml"
            locations = workspace / ".eif" / "local-state" / "project-locations.yaml"
            alpha = root / "alpha"
            beta = root / "beta"

            alpha_new = invoke(
                [
                    "new",
                    str(alpha),
                    "--project-name",
                    "alpha",
                    "--adapter",
                    "codex",
                    "--locale",
                    "uk",
                    "--registry",
                    str(registry),
                ],
                root,
            )
            beta_new = invoke(
                [
                    "new",
                    str(beta),
                    "--project-name",
                    "beta",
                    "--adapter",
                    "claude-code",
                    "--registry",
                    str(registry),
                ],
                root,
            )
            results.append(check(
                "two real EIF projects are registered",
                alpha_new[0] == 0 and beta_new[0] == 0,
                "".join(alpha_new[1:] + beta_new[1:]),
            ))

            task = alpha / "planning" / "session-task.md"
            task.parent.mkdir(parents=True)
            task.write_text("# Session task\n\nContinue deterministically.\n", encoding="utf-8")
            beta_task = beta / "planning" / "session-task.md"
            beta_task.parent.mkdir(parents=True)
            beta_task.write_text("# Other task\n", encoding="utf-8")
            commit_all(alpha, "Seed alpha session task")
            commit_all(beta, "Seed beta session task")

            registry_data = yaml.safe_load(registry.read_text(encoding="utf-8"))
            alpha_id = next(item["id"] for item in registry_data["projects"] if item["name"] == "alpha")

            by_name = invoke(
                ["projects", "resolve", "alpha", "--registry", str(registry)],
                workspace,
            )
            by_id = invoke(
                ["projects", "resolve", alpha_id, "--registry", str(registry)],
                workspace,
            )
            results.append(check(
                "projects resolve accepts exact name and stable ID",
                by_name[0] == 0
                and by_id[0] == 0
                and f"project_id={alpha_id}" in by_name[1]
                and f"path={alpha.resolve()}" in by_id[1],
                "".join(by_name[1:] + by_id[1:]),
            ))

            unknown = invoke(
                ["projects", "resolve", "missing", "--registry", str(registry)],
                workspace,
            )
            results.append(check(
                "projects resolve rejects an unknown selector",
                unknown[0] != 0 and "unknown project selector" in unknown[2],
                unknown[1] + unknown[2],
            ))

            original_locations = locations.read_bytes()
            local_data = yaml.safe_load(original_locations)
            local_data["locations"] = [
                item for item in local_data["locations"] if item["project_id"] != alpha_id
            ]
            locations.write_text(
                yaml.safe_dump(local_data, sort_keys=False), encoding="utf-8"
            )
            unresolved = invoke(
                ["projects", "resolve", "alpha", "--registry", str(registry)],
                workspace,
            )
            results.append(check(
                "projects resolve rejects a missing machine-local path",
                unresolved[0] != 0 and "no machine-local location" in unresolved[2],
                unresolved[1] + unresolved[2],
            ))
            locations.write_bytes(original_locations)

            lock = alpha / ".eif" / "framework.lock.yaml"
            lock_backup = lock.read_bytes()
            lock.unlink()
            incomplete = invoke(
                ["projects", "resolve", "alpha", "--registry", str(registry)],
                workspace,
            )
            results.append(check(
                "projects resolve rejects an incomplete EIF instance",
                incomplete[0] != 0 and "not a complete EIF instance" in incomplete[2],
                incomplete[1] + incomplete[2],
            ))
            lock.write_bytes(lock_backup)

            config = alpha / ".eif" / "config.yaml"
            config_backup = config.read_bytes()
            config_data = yaml.safe_load(config_backup)
            config_data["adapter"]["name"] = "cursor"
            config.write_text(
                yaml.safe_dump(config_data, sort_keys=False), encoding="utf-8"
            )
            mismatch = invoke(
                ["projects", "resolve", "alpha", "--registry", str(registry)],
                workspace,
            )
            results.append(check(
                "projects resolve rejects config-lock identity drift",
                mismatch[0] != 0 and "adapter mismatch" in mismatch[2],
                mismatch[1] + mismatch[2],
            ))
            config.write_bytes(config_backup)

            ambiguous_registry = workspace / ".eif" / "ambiguous-projects.yaml"
            ambiguous_locations = workspace / ".eif" / "local-state" / "ambiguous-locations.yaml"
            ambiguous_registry_data = yaml.safe_load(registry.read_text(encoding="utf-8"))
            ambiguous_registry_data["projects"][0]["id"] = "alpha"
            ambiguous_registry_data["projects"][0]["name"] = "first"
            ambiguous_registry_data["projects"][1]["name"] = "alpha"
            ambiguous_registry.write_text(
                yaml.safe_dump(ambiguous_registry_data, sort_keys=False),
                encoding="utf-8",
            )
            ambiguous_location_data = yaml.safe_load(locations.read_text(encoding="utf-8"))
            ambiguous_location_data["locations"][0]["project_id"] = "alpha"
            ambiguous_locations.write_text(
                yaml.safe_dump(ambiguous_location_data, sort_keys=False),
                encoding="utf-8",
            )
            ambiguous = invoke(
                [
                    "projects",
                    "resolve",
                    "alpha",
                    "--registry",
                    str(ambiguous_registry),
                    "--locations",
                    str(ambiguous_locations),
                ],
                workspace,
            )
            results.append(check(
                "projects resolve rejects an ID-name collision",
                ambiguous[0] != 0 and "ambiguous project selector" in ambiguous[2],
                ambiguous[1] + ambiguous[2],
            ))

            checkpoint_args = [
                "session",
                "checkpoint",
                "--session-id",
                "SESSION-TEST",
                "--source-artifact",
                "planning/session-task.md",
                "--goal",
                "Prove deterministic continuation.",
                "--in-scope",
                "Session checkpoint commands",
                "--no-touch",
                "External systems",
                "--approval-state",
                "not_required",
                "--decision",
                "Use same-chat continuation.",
                "--completed",
                "Project resolver verified.",
                "--verification",
                "pass::python tests/test_session.py::Fixture passed",
                "--next-action",
                "Run the resume audit.",
                "--continuation-mode",
                "same_chat",
            ]
            created = invoke(checkpoint_args, alpha)
            checkpoint = alpha / ".session-context" / "SESSION-TEST.md"
            results.append(check(
                "checkpoint writes a localized atomic Markdown record",
                created[0] == 0
                and checkpoint.is_file()
                and "# Контрольна точка сесії: SESSION-TEST" in checkpoint.read_text(encoding="utf-8")
                and not list(checkpoint.parent.glob("*.tmp-*")),
                created[1] + created[2],
            ))

            validated = invoke(
                ["session", "validate", str(checkpoint)], alpha
            )
            audited = invoke(
                ["session", "resume-audit", str(checkpoint)], alpha
            )
            handoff = invoke(
                ["session", "handoff", str(checkpoint)], alpha
            )
            results.append(check(
                "validate, resume-audit and same-chat handoff pass",
                validated[0] == 0
                and audited[0] == 0
                and handoff[0] == 0
                and "strategy=same_chat" in handoff[1]
                and "automation=none" in handoff[1],
                "".join(validated[1:] + audited[1:] + handoff[1:]),
            ))

            wrong_project = invoke(
                ["session", "resume-audit", str(checkpoint), "--project-root", str(beta)],
                beta,
            )
            results.append(check(
                "resume audit rejects the wrong active project",
                wrong_project[0] != 0 and "project_root" in wrong_project[2],
                wrong_project[1] + wrong_project[2],
            ))

            task_backup = task.read_bytes()
            task.write_text("# Session task\n\nChanged after checkpoint.\n", encoding="utf-8")
            stale_source = invoke(
                ["session", "resume-audit", str(checkpoint)], alpha
            )
            results.append(check(
                "resume audit detects a changed source artifact",
                stale_source[0] != 0 and "source_artifact_hash" in stale_source[2],
                stale_source[1] + stale_source[2],
            ))
            task.write_bytes(task_backup)

            drift_file = alpha / "UNCOMMITTED.md"
            drift_file.write_text("new work\n", encoding="utf-8")
            stale_git = invoke(
                ["session", "resume-audit", str(checkpoint)], alpha
            )
            results.append(check(
                "resume audit detects stale changed-file state",
                stale_git[0] != 0 and "git_status_fingerprint" in stale_git[2],
                stale_git[1] + stale_git[2],
            ))
            refreshed = invoke(checkpoint_args, alpha)
            fresh_again = invoke(
                ["session", "resume-audit", str(checkpoint)], alpha
            )
            results.append(check(
                "rolling checkpoint refresh accepts current changed files",
                refreshed[0] == 0 and fresh_again[0] == 0,
                "".join(refreshed[1:] + fresh_again[1:]),
            ))

            invalid_source = invoke(
                [
                    *checkpoint_args[:3],
                    "SESSION-ESCAPE",
                    checkpoint_args[4],
                    "../outside.md",
                    *checkpoint_args[6:],
                ],
                alpha,
            )
            results.append(check(
                "checkpoint rejects a source artifact outside the project",
                invalid_source[0] != 0
                and "source artifact" in invalid_source[2]
                and not (alpha / ".session-context" / "SESSION-ESCAPE.md").exists(),
                invalid_source[1] + invalid_source[2],
            ))

            missing_approval = alpha / ".session-context" / "missing-approval.md"
            rewrite_frontmatter(checkpoint, missing_approval, remove="approvals")
            approval_validation = invoke(
                ["session", "validate", str(missing_approval)], alpha
            )
            results.append(check(
                "schema rejects a checkpoint without approval state",
                approval_validation[0] != 0 and "approvals" in approval_validation[2],
                approval_validation[1] + approval_validation[2],
            ))

            missing_next = alpha / ".session-context" / "missing-next-action.md"
            rewrite_frontmatter(checkpoint, missing_next, remove="next_action")
            next_validation = invoke(
                ["session", "validate", str(missing_next)], alpha
            )
            results.append(check(
                "schema rejects a checkpoint without an exact next action",
                next_validation[0] != 0 and "next_action" in next_validation[2],
                next_validation[1] + next_validation[2],
            ))

            before_atomic_failure = checkpoint.read_bytes()

            def fail_replace(_source: Path, _target: Path) -> None:
                raise OSError("injected replace failure")

            atomic_failed = False
            try:
                session_cmd._atomic_write(checkpoint, "corrupt\n", replace=fail_replace)
            except OSError:
                atomic_failed = True
            results.append(check(
                "atomic checkpoint failure preserves the prior file and cleans staging",
                atomic_failed
                and checkpoint.read_bytes() == before_atomic_failure
                and not list(checkpoint.parent.glob("*.tmp-*")),
            ))
    finally:
        init_cmd.run = real_init_run

    passed = sum(1 for ok, _ in results if ok)
    for _, line in results:
        print(line)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_session_commands: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
