#!/usr/bin/env python3
"""Schema and named registry migration checks for EIF private workspaces."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from engineering_intelligence_framework.workspace_contract import (  # noqa: E402
    WorkspaceContractError,
    migrate_registry_v1_to_v2,
)

SCHEMA_ROOT = REPO_ROOT / "core" / "schemas"

VALID = {
    "project-registry.schema.json": {
        "schema_version": 2,
        "workspace_id": "sample-workspace",
        "projects": [
            {
                "id": "sample-project-12345678",
                "name": "Sample project",
                "profile": "default",
                "status": "active",
            }
        ],
    },
    "project-registry-v1.schema.json": {
        "schema_version": 1,
        "projects": [{"name": "Sample project", "path": "../../sample"}],
    },
    "project-locations.schema.json": {
        "schema_version": 1,
        "locations": [
            {
                "project_id": "sample-project-12345678",
                "path": "machine-local/sample",
            }
        ],
    },
    "workspace-config.schema.json": {
        "schema_version": 1,
        "workspace": {"id": "sample-workspace", "name": "Sample workspace"},
        "registry": {
            "path": ".eif/projects.yaml",
            "locations_path": ".eif/local-state/project-locations.yaml",
        },
        "profiles": {"root": "workspace/profiles", "default": "default"},
        "content": {"root": "workspace"},
    },
    "workspace-profile.schema.json": {
        "schema_version": 1,
        "name": "default",
        "framework": {"requires": ">=0.2.0,<0.3.0"},
        "artifacts": [
            {
                "kind": "rule",
                "name": "review-evidence",
                "path": "rules/review-evidence.md",
                "mode": "required",
            }
        ],
    },
    "workspace-lock.schema.json": {
        "lock_schema_version": 1,
        "workspace": {
            "id": "sample-workspace",
            "revision": "1" * 40,
            "profile": "default",
        },
        "bundle": {
            "path": ".eif/workspace-runtime",
            "manifest": [
                {
                    "path": "rules/review-evidence.md",
                    "sha256": "2" * 64,
                    "kind": "rule",
                    "name": "review-evidence",
                    "mode": "required",
                }
            ],
            "digest": "sha256:" + "3" * 64,
        },
        "generated_at": "2026-07-28T12:00:00+00:00",
    },
    "workspace-overrides.schema.json": {
        "schema_version": 1,
        "overrides": [
            {
                "kind": "rule",
                "name": "review-evidence",
                "override_of": "workspace://rule/review-evidence",
                "reason": "Project has a stricter equivalent.",
                "approved_by": "project-owner",
            }
        ],
    },
}


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def schema(name: str) -> dict:
    return json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))


def valid(name: str, data: dict) -> bool:
    return not list(Draft202012Validator(schema(name)).iter_errors(data))


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes() if path.is_file() else b"<DIR>"
        )
        for path in sorted(root.rglob("*"))
    }


def main() -> int:
    results: list[tuple[bool, str]] = []

    for name, fixture in VALID.items():
        results.append(check(f"{name}: valid fixture passes", valid(name, fixture)))
        future = copy.deepcopy(fixture)
        version_key = (
            "lock_schema_version"
            if "lock_schema_version" in future
            else "schema_version"
        )
        future[version_key] = 99
        results.append(
            check(f"{name}: future schema version fails closed", not valid(name, future))
        )

    leaked_path = copy.deepcopy(VALID["project-registry.schema.json"])
    leaked_path["projects"][0]["path"] = "machine-local/private-project"
    results.append(
        check(
            "registry v2 rejects a machine path",
            not valid("project-registry.schema.json", leaked_path),
        )
    )
    traversal = copy.deepcopy(VALID["workspace-profile.schema.json"])
    traversal["artifacts"][0]["path"] = "../outside.md"
    results.append(
        check(
            "workspace profile rejects path traversal",
            not valid("workspace-profile.schema.json", traversal),
        )
    )
    secret = copy.deepcopy(VALID["workspace-lock.schema.json"])
    secret["credential"] = "must-not-fit-the-contract"
    results.append(
        check(
            "workspace lock rejects credential fields",
            not valid("workspace-lock.schema.json", secret),
        )
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        registry = root / "control" / ".eif" / "projects.yaml"
        registry.parent.mkdir(parents=True)
        alpha = root / "alpha"
        beta = root / "beta"
        alpha.mkdir()
        beta.mkdir()
        legacy = {
            "schema_version": 1,
            "projects": [
                {"name": "Alpha", "path": "../../alpha"},
                {"name": "Beta", "path": "../../beta"},
            ],
        }
        registry.write_text(
            yaml.safe_dump(legacy, sort_keys=False),
            encoding="utf-8",
        )

        before = tree_bytes(root)
        target_registry, target_locations, locations = migrate_registry_v1_to_v2(
            registry
        )
        results.append(
            check(
                "registry migration is dry-run-first",
                tree_bytes(root) == before and not locations.exists(),
            )
        )
        results.append(
            check(
                "migration plan preserves names and separates paths",
                [item["name"] for item in target_registry["projects"]]
                == ["Alpha", "Beta"]
                and all("path" not in item for item in target_registry["projects"])
                and len(target_locations["locations"]) == 2,
            )
        )

        migrate_registry_v1_to_v2(registry, apply=True)
        migrated_registry = yaml.safe_load(registry.read_text(encoding="utf-8"))
        migrated_locations = yaml.safe_load(locations.read_text(encoding="utf-8"))
        results.append(
            check(
                "named migration applies registry v2 and locations v1",
                migrated_registry["schema_version"] == 2
                and migrated_locations["schema_version"] == 1
                and {
                    item["id"] for item in migrated_registry["projects"]
                }
                == {
                    item["project_id"]
                    for item in migrated_locations["locations"]
                },
            )
        )
        results.append(
            check(
                "committed migrated registry contains no path key",
                "path:" not in registry.read_text(encoding="utf-8"),
            )
        )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        registry = root / ".eif" / "projects.yaml"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "projects": [{"name": "Rollback", "path": "../../project"}],
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        before = tree_bytes(root)
        failed = False
        try:
            migrate_registry_v1_to_v2(
                registry,
                apply=True,
                fault_after="registry",
            )
        except RuntimeError:
            failed = True
        results.append(check("fault injection is observed", failed))
        results.append(
            check(
                "failed migration restores the exact prior tree",
                tree_bytes(root) == before,
                str(sorted(set(tree_bytes(root)) ^ set(before))),
            )
        )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        registry = root / ".eif" / "projects.yaml"
        locations = root / ".eif" / "local-state" / "project-locations.yaml"
        locations.parent.mkdir(parents=True)
        registry.write_text(
            "schema_version: 1\nprojects: []\n",
            encoding="utf-8",
        )
        locations.write_text(
            "schema_version: 1\nlocations: []\n",
            encoding="utf-8",
        )
        before = tree_bytes(root)
        refused = False
        try:
            migrate_registry_v1_to_v2(registry, apply=True)
        except WorkspaceContractError:
            refused = True
        results.append(
            check(
                "migration refuses an existing local-state target",
                refused and tree_bytes(root) == before,
            )
        )

    passed = sum(1 for ok, _ in results if ok)
    for _, line in results:
        print(line)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_workspace_schemas: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
