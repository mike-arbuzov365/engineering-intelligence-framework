#!/usr/bin/env python3
"""Characterize CLI output before the structured-service refactor."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests")]
from engineering_intelligence_framework import cli
from engineering_intelligence_framework.commands import session
from engineering_intelligence_framework.workspace_materialization import materialize_workspace
from workspace_test_support import commit_all
from test_delivery_guard import approval

GOLDEN = ROOT / "scripts/tests/fixtures/service_golden/cli.json"


def capture(argv: list[str], cwd: Path) -> dict:
    out, err = io.StringIO(), io.StringIO()
    previous = Path.cwd()
    try:
        os.chdir(cwd)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cli.main(argv)
    finally:
        os.chdir(previous)
    return {"rc": rc, "stdout": out.getvalue(), "stderr": err.getvalue()}


def cases(base: Path) -> dict:
    project = base / "project"
    assert capture(["new", str(project), "--project-name", "synthetic-golden", "--adapter", "claude-code"], base)["rc"] == 0
    results = {"doctor_ok": capture(["doctor", "--instance-path", str(project)], base)}
    entry = project / "CLAUDE.md"
    saved_entry = entry.read_bytes()
    entry.write_bytes(saved_entry + b"\n<!-- EIF:BEGIN -->\n")
    results["doctor_fail"] = capture(["doctor", "--instance-path", str(project)], base)
    entry.write_bytes(saved_entry)
    task = project / "planning/task.md"
    task.parent.mkdir(exist_ok=True)
    task.write_text("# Synthetic task\n", encoding="utf-8")
    argv = ["session", "checkpoint", "--project-root", str(project), "--source-artifact", "planning/task.md", "--session-id", "golden", "--goal", "Synthetic", "--in-scope", "planning", "--no-touch", "product", "--next-action", "Inspect", "--approval-state", "not_required"]
    assert capture(argv, project)["rc"] == 0
    path = project / ".session-context/golden.md"
    saved = session._parse_checkpoint(path)
    validate = ["session", "validate", str(path), "--project-root", str(project)]
    audit = ["session", "resume-audit", str(path), "--project-root", str(project)]
    results["validate_pass"] = capture(validate, project)
    results["audit_pass"] = capture(audit, project)
    for group, field, value in [
        ("project", "id", "other"), ("project", "name", "other"),
        ("project", "root", str(base / "other")),
        ("project", "config_sha256", "0" * 64), ("project", "lock_sha256", "0" * 64),
        ("project", "adapter", "other"), ("source_artifact", "sha256", "0" * 64),
        ("git", "repository", False), ("git", "root", str(base / "other")),
        ("git", "branch", "other"), ("git", "head", "0" * 40),
        ("git", "status_fingerprint", "0" * 64), ("git", "changed_files", ["other.md"]),
    ]:
        altered = copy.deepcopy(saved)
        altered[group][field] = value
        path.write_text("---\n" + yaml.safe_dump(altered, sort_keys=False) + "---\n", encoding="utf-8")
        results[f"audit_{group}_{field}"] = capture(audit, project)
    path.write_text("---\ninvalid: true\n---\n", encoding="utf-8")
    results["validate_fail"] = capture(validate, project)
    results["audit_schema"] = capture(audit, project)
    knowledge = project / "knowledge"
    knowledge.mkdir(exist_ok=True)
    (knowledge / "sample.md").write_text("---\ntype: fact\nstatus: validated\nscope: project\nevidence: OBSERVED\nsource: code\ncreated: 2026-07-15\n---\n# Synthetic fact\nSynthetic result.\n", encoding="utf-8")
    search = ["search", "synthetic", "--knowledge-root", str(knowledge)]
    results["search_match"] = capture(search, project)
    results["search_none"] = capture(["search", "nomatch", "--knowledge-root", str(knowledge)], project)
    (knowledge / "malformed.md").write_text("---\n[broken: yaml\n---\n", encoding="utf-8")
    results["search_malformed"] = capture(search, project)
    for name in ("knowledge-delta", "session-closeout"):
        results[f"render_{name}"] = capture(["render", name, "--instance-root", str(project), "--stdout", "--draft"], project)
    workspace = base / "workspace"
    assert capture(["workspace", "new", str(workspace)], base)["rc"] == 0
    assert capture(["workspace", "profile", "install", "graphic-design", "--workspace-path", str(workspace)], base)["rc"] == 0
    commit_all(workspace, "Seed synthetic profile")
    design = base / "design"
    assert capture(["new", str(design), "--project-name", "synthetic-design", "--adapter", "codex", "--profile", "graphic-design", "--registry", str(workspace / ".eif/projects.yaml")], base)["rc"] == 0
    commit_all(workspace, "Register synthetic project")
    commit_all(design, "Seed synthetic project")
    materialize_workspace(workspace, design, profile_name="graphic-design", framework_version="0.2.7")
    deliver = ["delivery", "check", "--instance-path", str(design), "--action", "package", "--scope", "campaign-q3-final"]
    results["delivery_blocked"] = capture(deliver, design)
    evidence = design / "planning/approvals/design-delivery.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("Synthetic owner decision.\n", encoding="utf-8")
    approval(design)
    results["delivery_pass"] = capture(deliver, design)
    return results


def normalize(value: dict, tmp: Path) -> dict:
    def walk(item):
        if isinstance(item, dict):
            return {k: walk(v) for k, v in item.items()}
        if not isinstance(item, str):
            return item
        # Windows resolve() expands an 8.3 TEMP alias; repr() then doubles
        # separators in audit diagnostics. Normalize both spellings before
        # JSON encoding, rather than changing any captured CLI content.
        item = re.sub(r"[A-Za-z]:[\\/]+[^\n]*?[\\/]+eif-golden-[A-Za-z0-9_-]+", "<tmp>", item)
        spellings = [(str(ROOT), "<source>"), (ROOT.as_posix(), "<source>")]
        if not str(tmp).startswith("<"):
            spellings += [(str(tmp), "<tmp>"), (str(tmp.resolve()), "<tmp>"), (tmp.as_posix(), "<tmp>")]
        for spelling, token in spellings:
            item = item.replace(spelling, token).replace(spelling.replace("\\", "\\\\"), token)
        item = re.sub(r"[0-9a-f]{64}", "<sha256>", item)
        item = re.sub(r"[0-9a-f]{40}", "<sha1>", item)
        item = re.sub(r"(generated by installed package engineering-intelligence-framework) \S+ \(Python [^)]+\)", r"\1 <version> (Python <version>)", item)
        return item
    return walk(value)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="eif-golden-") as tmp:
        actual = normalize(cases(Path(tmp)), Path(tmp))
    if "--record" in sys.argv:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(actual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        print(f"Recorded {len(actual)} CLI cases before refactoring")
        return 0
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    matches = [name for name in actual if actual[name] == expected.get(name)]
    for name in actual.keys() - set(matches):
        print(f"FAIL golden {name}: {actual[name]!r}; expected {expected.get(name)!r}")
    total = len(actual)
    print(f"EIF-RESULT: passed={len(matches)} total={total}")
    return 0 if len(matches) == total and actual.keys() == expected.keys() else 1


if __name__ == "__main__":
    raise SystemExit(main())
