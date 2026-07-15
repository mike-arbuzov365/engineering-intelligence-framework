#!/usr/bin/env python3
"""Tests for scripts/eif_paths.py: the runtime path-policy check for
knowledge.root/knowledge.index_path (independent-review finding - a JSON
Schema pattern alone cannot catch a resolved-path escape).

Usage:
    python scripts/tests/test_paths.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_paths  # noqa: E402


def check(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    print(f"{status} {name}" + (f": {detail}" if detail and not cond else ""))
    return cond


def main() -> int:
    results: list[bool] = []

    with tempfile.TemporaryDirectory() as td:
        instance = Path(td) / "instance"
        instance.mkdir()
        (instance / "knowledge").mkdir()
        outside = Path(td) / "outside-the-instance"
        outside.mkdir()

        # --- Negative cases: each must raise PathPolicyError, and must not
        # create anything anywhere (proven by snapshotting the whole temp
        # tree before/after and diffing). ---
        before = sorted(str(p) for p in Path(td).rglob("*"))

        rejected_cases = [
            ("../outside", "traversal"),
            ("/etc/passwd", "absolute POSIX"),
            ("C:\\Windows\\System32", "Windows drive"),
            ("C:/Windows/System32", "Windows drive (forward slash)"),
            ("\\\\server\\share\\file", "UNC (backslash)"),
            ("//server/share/file", "UNC (forward slash)"),
            ("knowledge/../../outside", "embedded traversal"),
            ("", "empty string"),
        ]
        for raw, label in rejected_cases:
            try:
                eif_paths.validate_instance_relative_path(raw, instance, "knowledge.root")
                results.append(check(f"rejects {label} ({raw!r})", False))
            except eif_paths.PathPolicyError:
                results.append(check(f"rejects {label} ({raw!r})", True))

        after = sorted(str(p) for p in Path(td).rglob("*"))
        results.append(check("no rejected path created any file/directory anywhere in the temp tree", before == after, f"before={before} after={after}"))
        results.append(check("outside-the-instance directory itself untouched (still empty)", list(outside.iterdir()) == []))

        # --- Positive cases ---
        try:
            resolved = eif_paths.validate_instance_relative_path("knowledge", instance, "knowledge.root")
            results.append(check("ordinary 'knowledge' resolves inside instance", resolved == (instance / "knowledge").resolve()))
        except eif_paths.PathPolicyError as e:
            results.append(check("ordinary 'knowledge' resolves inside instance", False, str(e)))

        try:
            resolved = eif_paths.validate_instance_relative_path("docs/knowledge/index.md", instance, "knowledge.index_path")
            results.append(check("nested 'docs/knowledge/index.md' resolves inside instance", resolved == (instance / "docs" / "knowledge" / "index.md").resolve()))
        except eif_paths.PathPolicyError as e:
            results.append(check("nested 'docs/knowledge/index.md' resolves inside instance", False, str(e)))

        # Spaces are allowed, not rejected - the policy is "quote it in
        # generated commands", not "reject it".
        try:
            resolved = eif_paths.validate_instance_relative_path("my knowledge/index.md", instance, "knowledge.index_path")
            results.append(check("path with spaces is allowed (not rejected)", resolved == (instance / "my knowledge" / "index.md").resolve()))
        except eif_paths.PathPolicyError as e:
            results.append(check("path with spaces is allowed (not rejected)", False, str(e)))

    # --- index-inside-root check ---
    try:
        eif_paths.validate_index_inside_root("docs/knowledge/index.md", "docs/knowledge")
        results.append(check("index directly inside root: accepted", True))
    except eif_paths.PathPolicyError as e:
        results.append(check("index directly inside root: accepted", False, str(e)))

    try:
        eif_paths.validate_index_inside_root("docs/knowledge/nested/index.md", "docs/knowledge")
        results.append(check("index in a subdirectory of root: accepted", True))
    except eif_paths.PathPolicyError as e:
        results.append(check("index in a subdirectory of root: accepted", False, str(e)))

    try:
        eif_paths.validate_index_inside_root("elsewhere/index.md", "docs/knowledge")
        results.append(check("index outside root: rejected", False))
    except eif_paths.PathPolicyError:
        results.append(check("index outside root: rejected", True))

    try:
        eif_paths.validate_index_inside_root("docs/knowledge-other/index.md", "docs/knowledge")
        results.append(check("index in a sibling dir with a shared prefix: rejected (not a substring match)", False))
    except eif_paths.PathPolicyError:
        results.append(check("index in a sibling dir with a shared prefix: rejected (not a substring match)", True))

    passed = sum(results)
    print(f"\ntest_paths: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
