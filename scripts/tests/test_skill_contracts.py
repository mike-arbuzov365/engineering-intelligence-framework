#!/usr/bin/env python3
"""Negative і positive tests для model-free skill contract checker."""
from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Callable

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from engineering_intelligence_framework.commands import skills  # noqa: E402

Result = tuple[bool, str]


def check(name: str, condition: bool, detail: str = "") -> Result:
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def fixture_data() -> dict:
    return {
        "schema_version": 1,
        "skill": {
            "name": "sample-skill",
            "profile": "core",
            "canonical_workflow": "playbooks/sample.md",
        },
        "triggers": {
            "positive": [
                {"id": "positive", "prompt": "Виконай sample workflow з evidence."}
            ],
            "negative": [
                {"id": "negative", "prompt": "Виконай unrelated bounded task."}
            ],
        },
        "references": {"required": ["playbooks/sample.md"]},
        "evidence": {"required": ["Evidence token"]},
        "commands": {"required": []},
        "stop_conditions": {"required": ["Stop token"]},
        "forbidden_behavior": {"required": ["Forbidden token"]},
        "assertions": {
            "manifest_contains": ["sample.md"],
            "canonical_contains": ["status: validated"],
            "manifest_not_contains": ["TODO", "[SKILL_PRUNED]"],
        },
        "supporting_files": {"scripts": [], "references": []},
        "provenance": {
            "origin": "repository",
            "source_revision": "repository",
            "license": "repository",
            "external_import": False,
            "surfaces_reviewed": {
                "scripts": True,
                "references": True,
                "secrets": True,
                "network": True,
                "install": True,
                "permissions": True,
            },
        },
        "evaluation": {
            "deterministic": "required",
            "behavioral": "required_for_material_semantic_change",
        },
    }


def make_framework(root: Path) -> Path:
    skill = root / "skills" / "sample-skill"
    (skill / "tests").mkdir(parents=True)
    (root / "playbooks").mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: sample-skill\n"
        "description: Use for one sample contract workflow.\n"
        "---\n\n"
        "# Sample skill\n\n"
        "Read `playbooks/sample.md`. Evidence token. Stop token. "
        "Forbidden token.\n",
        encoding="utf-8",
    )
    (root / "playbooks" / "sample.md").write_text(
        "---\nstatus: validated\n---\n\n# Sample workflow\n",
        encoding="utf-8",
    )
    contract = skill / "tests" / "contract.yaml"
    contract.write_text(
        yaml.safe_dump(fixture_data(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return contract


def synthetic_errors(mutate: Callable[[Path, Path], None]) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        contract = make_framework(root)
        mutate(root, contract)
        _records, errors = skills.check_framework(root)
        return errors


def main() -> int:
    results: list[Result] = []

    records, errors = skills.check_framework(ROOT)
    core = [item for item in records if item.profile == "core"]
    starters = [item for item in records if item.profile != "core"]
    results.append(
        check(
            "15 current skill contracts pass",
            len(records) == 15 and len(core) == 12 and len(starters) == 3 and not errors,
            f"records={len(records)} core={len(core)} starters={len(starters)} errors={errors}",
        )
    )
    results.append(
        check(
            "professional profile remains the starter grouping unit",
            sorted((item.profile, item.name) for item in starters)
            == [
                ("graphic-design", "review-graphic-design-delivery"),
                ("graphic-design", "run-graphic-design-project"),
                ("software-development", "onboard-software-project"),
            ],
        )
    )
    results.append(
        check(
            "no current contract imports external content",
            all(
                yaml.safe_load(item.contract.read_text(encoding="utf-8"))["provenance"]
                ["external_import"]
                is False
                for item in records
            ),
        )
    )

    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        cli_result = skills.main(["check", "--framework-root", str(ROOT)])
    results.append(
        check(
            "eifctl skills check surface is model-free and deterministic",
            cli_result == 0
            and "EIF-RESULT: passed=15 total=15" in out.getvalue()
            and not err.getvalue(),
            out.getvalue() + err.getvalue(),
        )
    )

    malformed = synthetic_errors(
        lambda _root, contract: contract.write_text("[broken", encoding="utf-8")
    )
    results.append(check("malformed fixture fails", bool(malformed), str(malformed)))

    def escape(_root: Path, contract: Path) -> None:
        data = fixture_data()
        data["references"]["required"] = ["../outside.md"]
        data["skill"]["canonical_workflow"] = "../outside.md"
        contract.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    escaped = synthetic_errors(escape)
    results.append(
        check(
            "reference escape fails",
            any("does not match" in error or "escapes" in error for error in escaped),
            str(escaped),
        )
    )

    def undeclared_script(root: Path, _contract: Path) -> None:
        script = root / "skills" / "sample-skill" / "scripts" / "unsafe.py"
        script.parent.mkdir()
        script.write_text("print('not executed')\n", encoding="utf-8")

    unsafe = synthetic_errors(undeclared_script)
    results.append(
        check(
            "undeclared executable support fails without execution",
            any("scripts declaration mismatch" in error for error in unsafe),
            str(unsafe),
        )
    )

    def wrong_hash(root: Path, contract: Path) -> None:
        script = root / "skills" / "sample-skill" / "scripts" / "reviewed.py"
        script.parent.mkdir()
        script.write_text("print('bounded')\n", encoding="utf-8")
        data = fixture_data()
        data["supporting_files"]["scripts"] = [
            {
                "path": "scripts/reviewed.py",
                "sha256": "0" * 64,
                "network": False,
                "install": False,
                "permissions": [],
                "side_effects": [],
                "reviewed": True,
            }
        ]
        contract.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    digest_errors = synthetic_errors(wrong_hash)
    results.append(
        check(
            "declared script digest drift fails",
            any("script digest mismatch" in error for error in digest_errors),
            str(digest_errors),
        )
    )

    duplicate_paragraph = (
        "This deliberately duplicated workflow paragraph is longer than one hundred and "
        "twenty characters so the deterministic checker can reject copied canonical prose "
        "without using a model or semantic similarity service."
    )

    def duplicate(root: Path, _contract: Path) -> None:
        manifest = root / "skills" / "sample-skill" / "SKILL.md"
        canonical = root / "playbooks" / "sample.md"
        manifest.write_text(
            manifest.read_text(encoding="utf-8") + "\n\n" + duplicate_paragraph + "\n",
            encoding="utf-8",
        )
        canonical.write_text(
            canonical.read_text(encoding="utf-8") + "\n\n" + duplicate_paragraph + "\n",
            encoding="utf-8",
        )

    duplicate_errors = synthetic_errors(duplicate)
    results.append(
        check(
            "duplicated canonical workflow prose fails",
            any("duplicates canonical workflow prose" in error for error in duplicate_errors),
            str(duplicate_errors),
        )
    )

    def overlap(_root: Path, contract: Path) -> None:
        data = fixture_data()
        data["triggers"]["negative"][0]["prompt"] = data["triggers"]["positive"][0]["prompt"]
        contract.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )

    overlap_errors = synthetic_errors(overlap)
    results.append(
        check(
            "positive and negative trigger overlap fails",
            any("trigger prompts overlap" in error for error in overlap_errors),
            str(overlap_errors),
        )
    )

    def imported(_root: Path, contract: Path) -> None:
        data = fixture_data()
        data["provenance"]["external_import"] = True
        contract.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    import_errors = synthetic_errors(imported)
    results.append(
        check(
            "external import metadata fails in the first contract version",
            any("False was expected" in error for error in import_errors),
            str(import_errors),
        )
    )

    missing_contract = synthetic_errors(lambda _root, contract: contract.unlink())
    results.append(
        check(
            "missing local contract fails",
            any("missing local contract fixture" in error for error in missing_contract),
            str(missing_contract),
        )
    )

    def missing_description(root: Path, _contract: Path) -> None:
        manifest = root / "skills" / "sample-skill" / "SKILL.md"
        manifest.write_text(
            "---\nname: sample-skill\n---\n\nRead `playbooks/sample.md`. "
            "Evidence token. Stop token. Forbidden token.\n",
            encoding="utf-8",
        )

    description_errors = synthetic_errors(missing_description)
    results.append(
        check(
            "missing manifest description fails",
            any("frontmatter description is required" in error for error in description_errors),
            str(description_errors),
        )
    )

    for passed, message in results:
        print(message)
    passed_count = sum(1 for passed, _message in results if passed)
    print(f"EIF-RESULT: passed={passed_count} total={len(results)}")
    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
