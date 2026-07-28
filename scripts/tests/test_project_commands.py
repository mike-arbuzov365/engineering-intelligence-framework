#!/usr/bin/env python3
"""End-to-end checks for `eifctl new`, `upgrade`, and `projects`.

Runs the real package command modules against temporary git repositories.
The test specifically covers the first public dogfooding requirements:
create-and-connect, a private multi-project registry, dry-run-before-write,
rehydration of a gitignored runtime, clean-tree protection, and sequential
registry upgrades.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from engineering_intelligence_framework import __version__  # noqa: E402
from engineering_intelligence_framework import cli  # noqa: E402
from engineering_intelligence_framework.commands import init_cmd  # noqa: E402


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    return condition, f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else "")


def git(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def commit_all(project: Path, message: str) -> None:
    git(project, "add", "-A")
    proc = git(
        project,
        "-c", "user.name=EIF Test",
        "-c", "user.email=eif-test@example.invalid",
        "commit", "-m", message,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout + proc.stderr)


def main() -> int:
    results: list[tuple[bool, str]] = []
    # Source-tree tests run while the package resources are intentionally
    # dirty with the change under test. A built/installed wheel has no git
    # working tree; package-build coverage exercises that real path.
    real_init_run = init_cmd.run
    init_cmd.run = lambda argv: real_init_run([*argv, "--allow-dirty"])  # type: ignore[assignment]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        control = root / "control"
        control.mkdir()
        registry = control / ".eif" / "projects.yaml"
        alpha = root / "alpha"

        rc = cli.main([
            "new", str(alpha),
            "--project-name", "alpha",
            "--adapter", "codex",
            "--locale", "uk",
            "--registry", str(registry),
        ])
        results.append(check("new creates and registers a project", rc == 0))
        results.append(check("new initializes a local git repository", (alpha / ".git").exists()))
        results.append(check("new generates the selected adapter entrypoint", (alpha / "AGENTS.md").exists()))
        config = yaml.safe_load((alpha / ".eif" / "config.yaml").read_text(encoding="utf-8"))
        lock = yaml.safe_load((alpha / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8"))
        results.append(check("fresh config records the actual creating package version",
                             (config.get("framework") or {}).get("version") == __version__))
        results.append(check("fresh lock records the actual instance version",
                             (lock.get("instance") or {}).get("eif_instance_version") == __version__))
        results.append(check("new uses installed-package provenance",
                             (lock.get("framework") or {}).get("source_type") == "installed-package"))
        registry_data = yaml.safe_load(registry.read_text(encoding="utf-8"))
        results.append(check("registry stores one relative project path",
                             registry_data["projects"] == [{"name": "alpha", "path": "../../alpha"}],
                             str(registry_data)))

        existing_snapshot = sorted(p.relative_to(alpha).as_posix() for p in alpha.rglob("*"))
        rc = cli.main(["new", str(alpha), "--project-name", "must-not-overwrite"])
        results.append(check("new refuses an existing target", rc != 0))
        results.append(check("existing target remains unchanged after refusal",
                             existing_snapshot == sorted(p.relative_to(alpha).as_posix() for p in alpha.rglob("*"))))

        commit_all(alpha, "bootstrap alpha")
        runtime = alpha / ".eif" / "runtime"
        shutil.rmtree(runtime)
        rc = cli.main(["upgrade", "--instance-path", str(alpha), "--dry-run"])
        results.append(check("upgrade dry-run succeeds with a missing gitignored runtime", rc == 0))
        results.append(check("upgrade dry-run writes nothing", not runtime.exists()))
        rc = cli.main(["upgrade", "--instance-path", str(alpha)])
        results.append(check("upgrade rehydrates the runtime and passes doctor", rc == 0 and runtime.exists()))

        commit_all(alpha, "refresh alpha runtime metadata")
        (alpha / "OWNER-NOTES.md").write_text("uncommitted owner work\n", encoding="utf-8")
        rc = cli.main(["upgrade", "--instance-path", str(alpha)])
        results.append(check("upgrade blocks a dirty project by default", rc != 0))
        rc = cli.main(["upgrade", "--instance-path", str(alpha), "--dry-run"])
        results.append(check("upgrade dry-run also blocks a dirty project", rc != 0))
        results.append(check("dirty owner file is preserved", (alpha / "OWNER-NOTES.md").read_text(encoding="utf-8") == "uncommitted owner work\n"))
        commit_all(alpha, "owner notes")

        beta = root / "beta"
        rc = cli.main([
            "new", str(beta),
            "--adapter", "claude-code",
            "--registry", str(registry),
        ])
        results.append(check("new connects a second project to the same registry", rc == 0))
        commit_all(beta, "bootstrap beta")

        rc = cli.main(["projects", "status", "--registry", str(registry)])
        results.append(check("projects status reads both instances", rc == 0))
        before_locks = {
            project.name: (project / ".eif" / "framework.lock.yaml").read_bytes()
            for project in (alpha, beta)
        }
        rc = cli.main(["projects", "upgrade", "--registry", str(registry)])
        results.append(check("projects upgrade defaults to plan-only", rc == 0))
        results.append(check("registry plan writes no project lock",
                             all((project / ".eif" / "framework.lock.yaml").read_bytes() == before_locks[project.name]
                                 for project in (alpha, beta))))

        (beta / "UNCOMMITTED.md").write_text("private work\n", encoding="utf-8")
        rc = cli.main(["projects", "upgrade", "--registry", str(registry), "--apply"])
        results.append(check("fleet preflight blocks before any project write", rc != 0))
        results.append(check("fleet preflight preserved every project lock",
                             all((project / ".eif" / "framework.lock.yaml").read_bytes() == before_locks[project.name]
                                 for project in (alpha, beta))))
        commit_all(beta, "private work")

        rc = cli.main(["projects", "upgrade", "--registry", str(registry), "--apply"])
        results.append(check("projects upgrade applies sequentially after all dry-runs pass", rc == 0))

        rc = cli.main(["projects", "remove", "beta", "--registry", str(registry)])
        results.append(check("projects remove updates only the registry", rc == 0 and beta.exists()))
        after_remove = yaml.safe_load(registry.read_text(encoding="utf-8"))
        results.append(check("projects remove leaves the other registration",
                             [p["name"] for p in after_remove["projects"]] == ["alpha"]))

        legacy = root / "legacy-git-source"
        legacy.mkdir()
        source_init = subprocess.run(
            [
                sys.executable, str(REPO_ROOT / "scripts" / "eif_init.py"),
                "--framework-root", str(REPO_ROOT),
                "--instance-path", str(legacy),
                "--project-name", "legacy-git-source",
                "--allow-dirty",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        results.append(check("source-migration fixture initializes from a git checkout", source_init.returncode == 0,
                             source_init.stdout + source_init.stderr))
        git(legacy, "init", "-b", "main")
        commit_all(legacy, "bootstrap legacy source")
        config_before_migration = (legacy / ".eif" / "config.yaml").read_bytes()
        rc = cli.main(["upgrade", "--instance-path", str(legacy), "--migrate-source"])
        migrated_lock = yaml.safe_load((legacy / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8"))
        results.append(check(
            "explicit git-to-package migration succeeds without using config reconfigure",
            rc == 0 and (migrated_lock.get("framework") or {}).get("source_type") == "installed-package",
        ))
        results.append(check(
            "source migration preserves user-owned config byte-for-byte",
            (legacy / ".eif" / "config.yaml").read_bytes() == config_before_migration,
        ))

    passed = sum(1 for ok, _ in results if ok)
    for _, line in results:
        print(line)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_project_commands: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
