#!/usr/bin/env python3
"""Deterministic tests для bounded skill-eval dry-run у eif_benchmark.py."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "scripts" / "eif_benchmark.py"
MANIFEST = ROOT / "docs" / "benchmarks" / "skill-eval" / "eif-021-manifest.yaml"
FIXED_TIME = "2026-08-09T12:00:00Z"


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BENCHMARK), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> int:
    results: list[tuple[bool, str]] = []
    with tempfile.TemporaryDirectory(
        prefix="eif-skill-eval-test-",
        dir=MANIFEST.parent,
    ) as tmp:
        temp = Path(tmp)
        out_a = temp / "dry-a.json"
        out_b = temp / "dry-b.json"
        dry_a = run(
            "skill-eval-dry-run",
            str(MANIFEST),
            "--out",
            str(out_a),
            "--generated-at",
            FIXED_TIME,
        )
        dry_b = run(
            "skill-eval-dry-run",
            str(MANIFEST),
            "--out",
            str(out_b),
            "--generated-at",
            FIXED_TIME,
        )
        result = json.loads(out_a.read_text(encoding="utf-8")) if out_a.is_file() else {}
        results.append(
            check(
                "dry-run creates exactly 12 sequential deferred attempts",
                dry_a.returncode == 0
                and result.get("execution_status") == "DEFERRED"
                and result.get("behavioral_model_runs") == 0
                and result.get("planned_attempts") == 12
                and [item["sequence"] for item in result.get("attempts", [])]
                == list(range(1, 13)),
                dry_a.stdout + dry_a.stderr,
            )
        )
        results.append(
            check(
                "fixed timestamp makes dry-run byte deterministic",
                dry_b.returncode == 0
                and out_a.read_bytes() == out_b.read_bytes(),
                dry_b.stdout + dry_b.stderr,
            )
        )

        pairs: dict[tuple[str, str], list[dict]] = {}
        for attempt in result.get("attempts", []):
            pairs.setdefault((attempt["skill"], attempt["scenario_id"]), []).append(
                attempt
            )
        matched = all(
            {item["mode"] for item in pair} == {"baseline", "treatment"}
            and len({item["prompt_sha256"] for item in pair}) == 1
            and {item["context"]["skill_available"] for item in pair}
            == {False, True}
            for pair in pairs.values()
        )
        results.append(
            check(
                "all six scenarios have matched baseline-treatment prompt digests",
                len(pairs) == 6 and matched,
            )
        )
        results.append(
            check(
                "dry-run metrics stay null and no prompt payload is retained",
                all(
                    item["metrics"]
                    == {
                        "input_tokens": None,
                        "measurement": "not_run",
                        "output_tokens": None,
                        "tool_calls": None,
                        "wall_time_seconds": None,
                    }
                    for item in result.get("attempts", [])
                )
                and "Виконай" not in out_a.read_text(encoding="utf-8"),
            )
        )
        validate = run("validate-skill-eval", str(out_a))
        results.append(
            check(
                "integrity-bound dry-run validates",
                validate.returncode == 0
                and "DEFERRED model_runs=0 planned_attempts=12" in validate.stdout,
                validate.stdout + validate.stderr,
            )
        )

        tampered_prompt = json.loads(out_a.read_text(encoding="utf-8"))
        tampered_prompt["attempts"][1]["prompt_sha256"] = "sha256:" + "0" * 64
        tampered_prompt_path = temp / "tampered-prompt.json"
        tampered_prompt_path.write_text(
            json.dumps(tampered_prompt, indent=2), encoding="utf-8"
        )
        prompt_validation = run("validate-skill-eval", str(tampered_prompt_path))
        results.append(
            check(
                "mismatched baseline-treatment prompt digest fails",
                prompt_validation.returncode != 0
                and "prompt digests differ" in prompt_validation.stdout,
                prompt_validation.stdout + prompt_validation.stderr,
            )
        )

        tampered_integrity = json.loads(out_a.read_text(encoding="utf-8"))
        tampered_integrity["integrity"]["source_files"][0]["sha256"] = (
            "sha256:" + "0" * 64
        )
        tampered_integrity_path = temp / "tampered-integrity.json"
        tampered_integrity_path.write_text(
            json.dumps(tampered_integrity, indent=2), encoding="utf-8"
        )
        integrity_validation = run(
            "validate-skill-eval", str(tampered_integrity_path)
        )
        results.append(
            check(
                "source digest substitution fails",
                integrity_validation.returncode != 0
                and "integrity digest drift" in integrity_validation.stdout,
                integrity_validation.stdout + integrity_validation.stderr,
            )
        )

        manifest_data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        manifest_data["skills"][0]["scenario_ids"][0] = "unknown-scenario"
        unknown_manifest = temp / "unknown-scenario.yaml"
        unknown_manifest.write_text(
            yaml.safe_dump(manifest_data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        unknown_out = temp / "unknown.json"
        unknown = run(
            "skill-eval-dry-run",
            str(unknown_manifest),
            "--out",
            str(unknown_out),
        )
        results.append(
            check(
                "unknown contract scenario fails before provider access",
                unknown.returncode != 0
                and "unknown scenario" in unknown.stdout
                and not unknown_out.exists(),
                unknown.stdout + unknown.stderr,
            )
        )

        approved_data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        approved_data["owner_gate"].update(
            {
                "behavioral_status": "approved",
                "hard_zero_cost_confirmed": True,
                "provider": "already-authorized",
                "model": "approved-model",
                "version": "approved-version",
                "rubric_judge": "not_requested",
            }
        )
        approved_data["model"].update(
            {
                "provider": "already-authorized",
                "name": "approved-model",
                "version": "approved-version",
            }
        )
        approved_manifest = temp / "approved.yaml"
        approved_manifest.write_text(
            yaml.safe_dump(approved_data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        approved_out = temp / "approved.json"
        approved = run(
            "skill-eval-dry-run",
            str(approved_manifest),
            "--out",
            str(approved_out),
        )
        results.append(
            check(
                "dry-run refuses to impersonate an approved behavioral runner",
                approved.returncode != 0
                and "this command never calls a provider" in approved.stdout
                and not approved_out.exists(),
                approved.stdout + approved.stderr,
            )
        )

        limited_data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        limited_data["max_model_runs"] = 11
        limited_manifest = temp / "limited.yaml"
        limited_manifest.write_text(
            yaml.safe_dump(limited_data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        limited_out = temp / "limited.json"
        limited = run(
            "skill-eval-dry-run",
            str(limited_manifest),
            "--out",
            str(limited_out),
        )
        results.append(
            check(
                "planned attempts cannot exceed manifest budget",
                limited.returncode != 0
                and "exceed max_model_runs 11" in limited.stdout
                and not limited_out.exists(),
                limited.stdout + limited.stderr,
            )
        )

        with tempfile.TemporaryDirectory(prefix="eif-skill-eval-outside-") as outside_tmp:
            outside_manifest = Path(outside_tmp) / "outside-skill-eval.yaml"
            outside_manifest.write_text(
                MANIFEST.read_text(encoding="utf-8"), encoding="utf-8"
            )
            outside_out = temp / "outside.json"
            outside = run(
                "skill-eval-dry-run",
                str(outside_manifest),
                "--out",
                str(outside_out),
            )
            results.append(
                check(
                    "manifest outside framework root fails containment",
                    outside.returncode != 0
                    and "inside framework root" in outside.stdout
                    and not outside_out.exists(),
                    outside.stdout + outside.stderr,
                )
            )

    for passed, message in results:
        print(message)
    passed_count = sum(1 for passed, _message in results if passed)
    print(f"EIF-RESULT: passed={passed_count} total={len(results)}")
    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
