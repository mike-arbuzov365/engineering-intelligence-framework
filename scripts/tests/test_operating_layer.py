#!/usr/bin/env python3
"""Structural tests for the public operating layer (playbooks/templates/skills).

Not a test of workflow correctness (that's exercised by actually using the
workflow) - a test that the artifacts themselves are well-formed: every
playbook declares the frontmatter this framework's own knowledge schema
requires, every skill's manifest name matches its directory, and no
unfinished-content marker (TODO/FIXME/TBD/XXX) slipped into what's
supposed to be finished, publishable prose. Templates are checked for
structure but not scanned for those markers in the same way - a
template's `<placeholder>` fill-in slots are intentional, not leftovers.

Usage:
    python scripts/tests/test_operating_layer.py
"""
from __future__ import annotations

import re
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS_DIR = FRAMEWORK_ROOT / "playbooks"
TEMPLATES_DIR = FRAMEWORK_ROOT / "templates"
SKILLS_DIR = FRAMEWORK_ROOT / "skills"
PACKAGE_RESOURCES_DIR = FRAMEWORK_ROOT / "src" / "engineering_intelligence_framework" / "resources"

Result = tuple[bool, str]

UNFINISHED_MARKERS = ("TODO", "FIXME", "TBD", "XXX")


def check(name: str, condition: bool, detail: str = "") -> Result:
    line = f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else "")
    return condition, line


def check_playbooks() -> list[Result]:
    results: list[Result] = []
    files = sorted(p for p in PLAYBOOKS_DIR.glob("*.md") if p.name != "README.md")
    results.append(check("at least one playbook exists", len(files) > 0))
    for f in files:
        text = f.read_text(encoding="utf-8")
        results.append(check(f"{f.name}: has a frontmatter block", text.startswith("---\n")))
        results.append(check(
            f"{f.name}: declares type playbook or knowledge_operation",
            re.search(r"^type:\s*(playbook|knowledge_operation)\s*$", text, re.M) is not None,
        ))
        results.append(check(f"{f.name}: scope is framework", "scope: framework" in text))
        results.append(check(f"{f.name}: has a level-1 heading", re.search(r"^# \S", text, re.M) is not None))
        results.append(check(f"{f.name}: has a Knowledge source comment", "<!-- Knowledge source:" in text))
        found = [m for m in UNFINISHED_MARKERS if m in text]
        results.append(check(f"{f.name}: no unfinished-content markers", not found, str(found)))
    return results


def check_templates() -> list[Result]:
    results: list[Result] = []
    files = sorted(p for p in TEMPLATES_DIR.glob("*.md") if p.name != "README.md")
    results.append(check("at least one template exists", len(files) > 0))
    for f in files:
        text = f.read_text(encoding="utf-8")
        results.append(check(f"{f.name}: has a level-1 heading", re.search(r"^# \S", text, re.M) is not None))
        found = [m for m in UNFINISHED_MARKERS if m in text]
        results.append(check(f"{f.name}: no unfinished-content markers", not found, str(found)))
    return results


def check_skills() -> list[Result]:
    results: list[Result] = []
    dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    results.append(check("at least one skill exists", len(dirs) > 0))
    for d in dirs:
        skill_file = d / "SKILL.md"
        results.append(check(f"{d.name}: has SKILL.md", skill_file.is_file()))
        if not skill_file.is_file():
            continue
        text = skill_file.read_text(encoding="utf-8")
        name_match = re.search(r"^name:\s*(\S+)\s*$", text, re.M)
        results.append(check(
            f"{d.name}: frontmatter name matches directory",
            name_match is not None and name_match.group(1) == d.name,
            name_match.group(1) if name_match else "no name field",
        ))
        results.append(check(f"{d.name}: has a description field", re.search(r"^description:", text, re.M) is not None))
        found = [m for m in UNFINISHED_MARKERS if m in text]
        results.append(check(f"{d.name}: no unfinished-content markers", not found, str(found)))
    return results


def check_bounded_loop_contract() -> list[Result]:
    results: list[Result] = []
    playbook = (PLAYBOOKS_DIR / "bounded-evidence-loop.md").read_text(encoding="utf-8")
    template = (TEMPLATES_DIR / "bounded-evidence-loop.md").read_text(encoding="utf-8")
    session_execution = (PLAYBOOKS_DIR / "session-execution.md").read_text(encoding="utf-8")
    packet_execution = (PLAYBOOKS_DIR / "execution-packet-execution.md").read_text(encoding="utf-8")
    gitignore = (FRAMEWORK_ROOT / ".gitignore").read_text(encoding="utf-8")

    for field in ("success_evidence", "evaluator", "max_iterations", "remote_run_budget", "failure_signature"):
        results.append(check(
            f"bounded loop: playbook and template declare {field}",
            field in playbook and field in template,
        ))
    results.append(check(
        "bounded loop: session execution invokes the contract",
        "bounded-evidence-loop.md" in session_execution,
    ))
    results.append(check(
        "bounded loop: packet execution invokes the contract",
        "bounded-evidence-loop.md" in packet_execution,
    ))
    results.append(check(
        "Session layer: .session-context is gitignored",
        ".session-context/" in gitignore,
    ))
    session_context = FRAMEWORK_ROOT / ".session-context"
    committed_like_files = list(session_context.glob("*.md")) if session_context.exists() else []
    results.append(check(
        "Session layer: repository contains no durable session-context files",
        not committed_like_files,
        ", ".join(p.name for p in committed_like_files),
    ))
    runtime_docs = (
        "docs/architecture/HOW-EIF-WORKS.md",
        "docs/product/claims-evidence.md",
        "docs/reference/terminology.md",
        "docs/research/bounded-evidence-loops.md",
    )
    for relative_path in runtime_docs:
        results.append(check(
            f"runtime docs: package contains {relative_path}",
            (PACKAGE_RESOURCES_DIR / relative_path).is_file(),
        ))
    return results


def main() -> int:
    all_results = check_playbooks() + check_templates() + check_skills() + check_bounded_loop_contract()
    for _, line in all_results:
        print(line)

    passed = sum(1 for ok, _ in all_results if ok)
    total = len(all_results)
    print(f"EIF-RESULT: passed={passed} total={total}")
    print(f"\ntest_operating_layer: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
