#!/usr/bin/env python3
"""Workspace snapshot transaction and doctor drift checks."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engineering_intelligence_framework import cli  # noqa: E402
from engineering_intelligence_framework.commands import init_cmd  # noqa: E402
from engineering_intelligence_framework.workspace_materialization import (  # noqa: E402
    FAULT_ENV,
    materialize_workspace,
    verify_workspace_materialization,
)
from workspace_test_support import (  # noqa: E402
    commit_all,
    tree_bytes,
    write_profile,
)


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def main() -> int:
    results: list[tuple[bool, str]] = []
    real_init_run = init_cmd.run
    init_cmd.run = lambda argv: real_init_run(  # type: ignore[assignment]
        [*argv, "--allow-dirty"]
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        workspace = root / "workspace"
        project = root / "project"
        cli.main(["workspace", "new", str(workspace)])
        cli.main(
            [
                "new",
                str(project),
                "--project-name",
                "transaction-project",
                "--adapter",
                "codex",
            ]
        )
        rules = workspace / "workspace" / "rules"
        rules.mkdir(parents=True)
        source = rules / "quality.md"
        source.write_text("# Quality v1\n", encoding="utf-8")
        write_profile(
            workspace,
            [
                {
                    "kind": "rule",
                    "name": "quality",
                    "path": "rules/quality.md",
                    "mode": "required",
                }
            ],
        )
        commit_all(workspace, "workspace v1")
        commit_all(project, "project bootstrap")

        first = materialize_workspace(
            workspace,
            project,
            profile_name="default",
            framework_version="0.2.0",
        )
        results.append(
            check(
                "initial snapshot materializes and verifies",
                len(first["files"]) == 1
                and verify_workspace_materialization(project) == [],
            )
        )
        commit_all(project, "workspace snapshot v1")
        prior_tree = tree_bytes(project)

        source.write_text("# Quality v2\n", encoding="utf-8")
        commit_all(workspace, "workspace v2")

        for fault in (
            "workspace-runtime-stage",
            "workspace-lock-stage",
            "workspace-runtime",
            "workspace-lock",
        ):
            failed = False
            os.environ[FAULT_ENV] = fault
            try:
                materialize_workspace(
                    workspace,
                    project,
                    profile_name="default",
                    framework_version="0.2.0",
                )
            except RuntimeError:
                failed = True
            finally:
                os.environ.pop(FAULT_ENV, None)
            current_tree = tree_bytes(project)
            transients = [
                path
                for path in project.rglob("*")
                if path.name.endswith((".next", ".previous"))
                and ".git" not in path.parts
            ]
            results.append(
                check(
                    f"{fault}: failure is observed",
                    failed,
                )
            )
            results.append(
                check(
                    f"{fault}: exact prior project tree is restored",
                    current_tree == prior_tree and not transients,
                    str([path.as_posix() for path in transients]),
                )
            )

        materialize_workspace(
            workspace,
            project,
            profile_name="default",
            framework_version="0.2.0",
        )
        results.append(
            check(
                "successful refresh installs workspace v2",
                (
                    project
                    / ".eif"
                    / "workspace-runtime"
                    / "rules"
                    / "quality.md"
                ).read_text(encoding="utf-8")
                == "# Quality v2\n"
                and verify_workspace_materialization(project) == [],
            )
        )
        commit_all(project, "workspace snapshot v2")
        deterministic_before = tree_bytes(project)
        materialize_workspace(
            workspace,
            project,
            profile_name="default",
            framework_version="0.2.0",
        )
        results.append(
            check(
                "repeated clean materialization is byte-deterministic",
                tree_bytes(project) == deterministic_before,
            )
        )

        runtime_file = (
            project
            / ".eif"
            / "workspace-runtime"
            / "rules"
            / "quality.md"
        )
        runtime_before = runtime_file.read_bytes()
        runtime_file.write_text("# Drift\n", encoding="utf-8")
        hash_drift = verify_workspace_materialization(project)
        results.append(
            check(
                "doctor classifies runtime hash drift",
                any("hash drift" in problem for problem in hash_drift),
                str(hash_drift),
            )
        )
        results.append(
            check(
                "eifctl doctor fails closed on workspace hash drift",
                cli.main(["doctor", "--instance-path", str(project)]) != 0,
            )
        )
        runtime_file.write_bytes(runtime_before)

        runtime_file.unlink()
        missing = verify_workspace_materialization(project)
        results.append(
            check(
                "doctor distinguishes a missing managed file",
                any("file is missing" in problem for problem in missing),
                str(missing),
            )
        )
        runtime_file.parent.mkdir(parents=True, exist_ok=True)
        runtime_file.write_bytes(runtime_before)

        unexpected = runtime_file.parent / "unexpected.md"
        unexpected.write_text("# Unexpected\n", encoding="utf-8")
        extra = verify_workspace_materialization(project)
        results.append(
            check(
                "doctor distinguishes an unexpected runtime file",
                any("unexpected workspace runtime" in problem for problem in extra),
                str(extra),
            )
        )
        unexpected.unlink()

        lock_path = project / ".eif" / "workspace.lock.yaml"
        lock_before = lock_path.read_bytes()
        lock_path.unlink()
        missing_lock = verify_workspace_materialization(project)
        results.append(
            check(
                "doctor distinguishes a missing lock",
                missing_lock
                == ["workspace lock is missing while workspace runtime exists"],
                str(missing_lock),
            )
        )
        lock_path.write_bytes(lock_before)
        results.append(
            check(
                "restored snapshot verifies cleanly",
                verify_workspace_materialization(project) == [],
            )
        )

    passed = sum(1 for ok, _ in results if ok)
    for _, line in results:
        print(line)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_workspace_transaction: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
