#!/usr/bin/env python3
"""Regressions from a full 0.2.0 owner walkthrough on two real private
repositories: the line-ending contract, lock idempotence, the documented
`eifctl init PATH` form, and content-based workspace freshness.

Each check here corresponds to a defect that a user actually hit, not to a
hypothetical one.

Usage:
    python scripts/tests/test_line_endings.py
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import eif_init as init_script  # noqa: E402
import eif_verify_runtime as verify  # noqa: E402
from engineering_intelligence_framework import cli  # noqa: E402
from engineering_intelligence_framework.commands import init_cmd  # noqa: E402
from engineering_intelligence_framework.workspace_materialization import (  # noqa: E402
    materialize_workspace,
)
from workspace_test_support import commit_all, write_profile  # noqa: E402


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    condition = bool(condition)
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def check_gitattributes_block() -> list[tuple[bool, str]]:
    """The managed block has to name every generated file whose exact bytes
    are recorded in committed state, using the entrypoint and knowledge-index
    paths this instance actually configured."""
    results = []
    block = init_script.render_gitattributes_block("AGENTS.md", "docs/knowledge/index.md")
    results.append(
        check(
            "gitattributes block pins the configured entrypoint",
            "AGENTS.md text eol=lf" in block,
            block,
        )
    )
    results.append(
        check(
            "gitattributes block pins the configured knowledge index",
            "docs/knowledge/index.md text eol=lf" in block,
            block,
        )
    )
    results.append(
        check(
            "gitattributes block pins both locks and the config",
            all(
                f"{path} text eol=lf" in block
                for path in (
                    ".eif/config.yaml",
                    ".eif/framework.lock.yaml",
                    ".eif/workspace.lock.yaml",
                )
            ),
            block,
        )
    )
    results.append(
        check(
            "gitattributes pins itself, or it is the one file left in the trap",
            ".gitattributes text eol=lf" in block,
            block,
        )
    )
    results.append(
        check(
            "the block covers everything EIF writes, not only what it hashes",
            ".gitignore text eol=lf" in block,
            block,
        )
    )
    unmanaged = init_script.render_gitattributes_block("CLAUDE.md", None)
    results.append(
        check(
            "an unmanaged knowledge index contributes no pattern",
            "index.md" not in unmanaged,
            unmanaged,
        )
    )
    spaced = init_script.gitattributes_pattern("docs/my notes/index.md")
    results.append(
        check(
            "a path with whitespace is quoted, since git ends a pattern at the first space",
            spaced == '"docs/my notes/index.md"',
            spaced,
        )
    )
    return results


def check_instance_line_endings(root: Path) -> list[tuple[bool, str]]:
    results = []
    project = root / "endings-project"
    rc = cli.main(["init", str(project), "--adapter", "claude-code"])
    results.append(check("eifctl init accepts the documented positional path", rc == 0))
    results.append(
        check(
            "a positional init derives the project name from the directory",
            "name: endings-project"
            in (project / ".eif" / "config.yaml").read_text(encoding="utf-8"),
        )
    )

    attributes = project / ".gitattributes"
    results.append(
        check(
            "init writes an EIF-managed .gitattributes",
            attributes.is_file()
            and init_script.GITATTRIBUTES_MARKER
            in attributes.read_text(encoding="utf-8"),
        )
    )
    results.append(
        check(
            ".gitattributes is itself written with LF",
            b"\r\n" not in attributes.read_bytes(),
        )
    )
    results.append(
        check(
            "doctor accepts the managed .gitattributes markers",
            verify.check_markers(project, "CLAUDE.md") == [],
        )
    )
    corrupted = attributes.read_text(encoding="utf-8").replace(
        init_script.GITATTRIBUTES_END, ""
    )
    attributes.write_text(corrupted, encoding="utf-8")
    results.append(
        check(
            "doctor rejects a half-open .gitattributes marker pair",
            any(
                ".gitattributes" in problem
                for problem in verify.check_markers(project, "CLAUDE.md")
            ),
        )
    )
    return results


def check_crlf_diagnosis(root: Path) -> list[tuple[bool, str]]:
    """Git for Windows converts on checkout with core.autocrlf=true, so a
    clone of a project generated before the managed .gitattributes block
    existed fails the index hash check on content nobody edited. The message
    has to say that instead of blaming a hand-edit."""
    results = []
    project = root / "crlf-project"
    knowledge = project / "knowledge"
    knowledge.mkdir(parents=True)
    (knowledge / "fact.md").write_text(
        "---\ntype: fact\nstatus: validated\nscope: project\n"
        "created: 2026-07-29\nreview_after: 2026-10-29\n---\n\n# Fact\n",
        encoding="utf-8",
    )
    rc = cli.main([str("init"), str(project), "--adapter", "claude-code"])
    results.append(check("init succeeds against a seeded knowledge root", rc == 0))

    import yaml

    lock = yaml.safe_load(
        (project / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")
    )
    index_path = project / lock["knowledge_index"]["path"]
    lf_bytes = index_path.read_bytes()
    results.append(
        check(
            "the generated knowledge index is stored as LF",
            b"\r\n" not in lf_bytes,
        )
    )
    index_path.write_bytes(lf_bytes.replace(b"\n", b"\r\n"))
    problems = verify.check_knowledge_index_drift(project, lock)
    results.append(
        check(
            "a CRLF checkout is reported as a line-ending conversion",
            len(problems) == 1 and "CRLF-to-LF normalization" in problems[0],
            str(problems),
        )
    )
    results.append(
        check(
            "the line-ending report explicitly clears the user of a hand-edit",
            bool(problems) and "was not hand-edited" in problems[0],
            str(problems),
        )
    )
    index_path.write_bytes(lf_bytes[:-1] + b"x\n")
    edited = verify.check_knowledge_index_drift(project, lock)
    results.append(
        check(
            "a real edit is still reported as a real edit",
            len(edited) == 1
            and "hand-edited" in edited[0]
            and "CRLF" not in edited[0],
            str(edited),
        )
    )
    index_path.write_bytes(lf_bytes)
    return results


def check_autocrlf_clone_stays_clean(root: Path) -> list[tuple[bool, str]]:
    """The promise this whole contract exists to keep, stated as one check:
    clone a connected project on a machine that converts newlines, upgrade
    it, and the tree is still committable-clean.

    core.autocrlf is set explicitly rather than inherited, so this asserts the
    same thing on a Linux runner as on the Windows machine where the symptom
    was found. Without it the suite would pass everywhere the bug cannot
    appear and fail nowhere else."""
    results = []
    origin = root / "autocrlf-origin"
    origin.mkdir()
    git(origin, "init", "-b", "main", "-q")
    git(origin, "config", "core.autocrlf", "true")
    (origin / "README.md").write_bytes(b"# demo\n")
    knowledge = origin / "knowledge"
    knowledge.mkdir()
    (knowledge / "fact.md").write_bytes(
        b"---\ntype: fact\nstatus: validated\nscope: project\n"
        b"created: 2026-07-29\nreview_after: 2026-10-29\n---\n\n# Fact\n"
    )
    cli.main(["init", str(origin), "--adapter", "claude-code"])
    commit_all(origin, "bootstrap with EIF")
    results.append(
        check(
            "an autocrlf origin is clean right after its bootstrap commit",
            not git(origin, "status", "--porcelain").stdout.strip(),
            git(origin, "status", "--porcelain").stdout,
        )
    )

    clone = root / "autocrlf-clone"
    cloned = subprocess.run(
        ["git", "-c", "core.autocrlf=true", "clone", "-q", str(origin), str(clone)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    results.append(check("the project clones", cloned.returncode == 0, cloned.stderr))
    git(clone, "config", "core.autocrlf", "true")
    results.append(
        check(
            "a fresh autocrlf clone starts clean",
            not git(clone, "status", "--porcelain").stdout.strip(),
            git(clone, "status", "--porcelain").stdout,
        )
    )

    rc = cli.main(["upgrade", "--instance-path", str(clone)])
    results.append(check("upgrade rehydrates the cloned project", rc == 0))
    git(clone, "update-index", "--refresh")
    dirty = git(clone, "status", "--porcelain").stdout.strip()
    results.append(
        check(
            "upgrading a fresh autocrlf clone leaves no phantom modifications",
            not dirty,
            f"dirty={dirty!r} numstat={git(clone, 'diff', '--numstat').stdout!r}",
        )
    )
    return results


def check_lock_idempotence(root: Path) -> list[tuple[bool, str]]:
    """A re-run that resolves to identical provenance must not move the lock's
    clock. Otherwise every fleet apply leaves every project dirty with a
    timestamp-only diff, and that diff blocks the next fleet run."""
    results = []
    project = root / "idempotent-project"
    cli.main(["init", str(project), "--adapter", "codex"])
    lock_path = project / ".eif" / "framework.lock.yaml"
    first = lock_path.read_bytes()
    rc = cli.main(["init", str(project)])
    second = lock_path.read_bytes()
    results.append(check("a routine re-run succeeds", rc == 0))
    results.append(
        check(
            "an unchanged upgrade rewrites no byte of the framework lock",
            first == second,
            "generated_at moved with no content change",
        )
    )
    return results


def check_workspace_freshness(root: Path) -> list[tuple[bool, str]]:
    """Freshness is a question about resolved content. A workspace commit that
    changes nothing a project consumes - registering another project, editing
    the ledger - must not restage every connected project."""
    results = []
    if True:
        workspace = root / "freshness-workspace"
        project = root / "freshness-project"
        cli.main(["workspace", "new", str(workspace)])
        cli.main(
            ["new", str(project), "--project-name", "freshness-project", "--adapter", "codex"]
        )
        rules = workspace / "workspace" / "rules"
        rules.mkdir(parents=True)
        (rules / "gate.md").write_bytes(b"# Gate\n")
        write_profile(
            workspace,
            [
                {
                    "kind": "rule",
                    "name": "gate",
                    "path": "rules/gate.md",
                    "mode": "required",
                }
            ],
        )
        commit_all(workspace, "workspace v1")
        commit_all(project, "project bootstrap")

        first = materialize_workspace(
            workspace, project, profile_name="default", framework_version="0.2.0"
        )
        results.append(
            check("the first materialization reports a change", first.get("changed") is True)
        )
        lock_path = project / ".eif" / "workspace.lock.yaml"
        pinned = lock_path.read_bytes()
        commit_all(project, "workspace snapshot")

        (workspace / "planning" / "notes.md").write_text("# Notes\n", encoding="utf-8")
        commit_all(workspace, "workspace commit that changes no consumed artifact")
        second = materialize_workspace(
            workspace, project, profile_name="default", framework_version="0.2.0"
        )
        results.append(
            check(
                "a workspace commit with no consumed change is not a change",
                second.get("changed") is False,
            )
        )
        results.append(
            check(
                "an unchanged resolution leaves the workspace lock byte-identical",
                lock_path.read_bytes() == pinned,
            )
        )
        results.append(
            check(
                "the project stays clean after a no-op fleet pass",
                not git(project, "status", "--porcelain").stdout.strip(),
                git(project, "status", "--porcelain").stdout,
            )
        )

        (rules / "gate.md").write_bytes(b"# Gate v2\n")
        commit_all(workspace, "workspace v2")
        third = materialize_workspace(
            workspace, project, profile_name="default", framework_version="0.2.0"
        )
        results.append(
            check(
                "a real artifact change is still materialized",
                third.get("changed") is True
                and (
                    project / ".eif" / "workspace-runtime" / "rules" / "gate.md"
                ).read_bytes()
                == b"# Gate v2\n",
            )
        )
        results.append(
            check(
                "the refreshed lock records the digest of the new content",
                hashlib.sha256(b"# Gate v2\n").hexdigest()
                in lock_path.read_text(encoding="utf-8"),
            )
        )
    return results


def main() -> int:
    results: list[tuple[bool, str]] = []
    results += check_gitattributes_block()
    # This suite runs against the working checkout, which is dirty whenever a
    # contributor is mid-change. Provenance dirtiness is a different contract,
    # covered by test_init.py; assert it away here so these checks are about
    # line endings and idempotence only.
    real_init_run = init_cmd.run
    patched = lambda argv: real_init_run([*argv, "--allow-dirty"])  # noqa: E731
    init_cmd.run = patched  # type: ignore[assignment]
    # cli.COMMANDS captured the original function object at import time, so
    # rebinding the module attribute alone would not reach `eifctl init`.
    cli.COMMANDS["init"] = patched
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results += check_instance_line_endings(root)
            results += check_crlf_diagnosis(root)
            results += check_autocrlf_clone_stays_clean(root)
            results += check_lock_idempotence(root)
            results += check_workspace_freshness(root)
    finally:
        init_cmd.run = real_init_run  # type: ignore[assignment]
        cli.COMMANDS["init"] = real_init_run

    for _, line in results:
        print(line)
    passed = sum(1 for ok, _ in results if ok)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_line_endings: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
