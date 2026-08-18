#!/usr/bin/env python3
"""Pick the test suites a change actually needs, and run only those.

The repository has two tiers and nothing between them. `smoke.py` runs the
critical user flow in about 16 seconds and is the routine PR gate;
`run_all.py` runs every suite in roughly 17 minutes and is the release
gate. A change that touches one governance file therefore has two bad
options: run the fast tier that does not cover it, or pay the release tier
to prove one file.

That gap is not theoretical. On 2026-08-19 a contract token edit in
`skills/run-execution-packet/` passed `eifctl skills check`, passed four
hand-picked suites, and still broke `test_skill_contracts.py`. The full
run caught it seventeen minutes later. A router keyed on the changed path
would have selected that suite in the first place.

This script maps changed paths to suites, always includes the smoke tier,
and refuses to guess: a path that matches no rule escalates to the full
inventory rather than being silently dropped. Selecting too much is a
slow run; selecting too little is a false pass.

Usage:
    python scripts/tests/route_changed.py                 # vs merge-base with main
    python scripts/tests/route_changed.py --base HEAD~1
    python scripts/tests/route_changed.py --dry-run       # print the plan only
    python scripts/tests/route_changed.py --paths a.py b.md
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent

# Always run: the critical user flow, cheap enough that skipping it saves
# nothing worth the risk.
BASE_SUITES = ["smoke.py"]

# Ordered rules. The first matching prefix wins for a given path, so put
# the narrow prefixes above the directory they live in.
#
# Each entry is (path prefix, suites). A prefix ending in "/" matches a
# directory; anything else matches an exact repository-relative path.
RULES: list[tuple[str, list[str]]] = [
    # Operating layer: skills, playbooks, templates, ontology.
    ("skills/", [
        "test_skill_contracts.py",
        "test_skill_eval.py",
        "test_project_skills.py",
        "test_sync_skills.py",
        "test_operating_layer.py",
        "test_check_links.py",
    ]),
    ("playbooks/", [
        "test_operating_layer.py",
        "test_skill_contracts.py",
        "test_check_links.py",
    ]),
    ("templates/", [
        "test_operating_layer.py",
        "test_skill_contracts.py",
        "test_render.py",
        "test_check_links.py",
    ]),
    ("core/schemas/", [
        "test_validate.py",
        "test_workspace_schemas.py",
        "test_format_dependencies.py",
        "test_integration_contracts.py",
    ]),
    ("core/", [
        "test_operating_layer.py",
        "test_validate.py",
        "test_check_links.py",
    ]),
    ("professional-profiles/", [
        "test_skill_contracts.py",
        "test_delivery_guard.py",
        "test_operating_layer.py",
    ]),
    # Adapters: the expensive family. Only pay for it when adapters move.
    ("adapters/", [
        "test_cursor_adapter.py",
        "test_codex_adapter.py",
        "test_hermes_adapter.py",
        "test_adapter_switch_matrix.py",
        "test_adapter_continuity.py",
        "test_parity_matrix.py",
    ]),
    ("locales/", ["test_locale.py", "test_render.py"]),
    ("integrations/rtk/", ["test_rtk_integration.py", "test_integration_contracts.py"]),
    ("integrations/graphify/", ["test_graphify_integration.py", "test_integration_contracts.py"]),
    ("integrations/", ["test_integration_contracts.py"]),
    # Packaging and dependency pins reach everything the wheel carries.
    ("pyproject.toml", ["test_package_smoke.py", "test_check_licenses.py", "test_release_environment.py"]),
    ("scripts/requirements.txt", ["test_format_dependencies.py", "test_check_licenses.py"]),
    # The package mirror is generated from the sources above; a diff here
    # alone usually means the sync ran, so re-check the sync itself.
    ("src/engineering_intelligence_framework/resources/", ["test_sync_skills.py", "test_operating_layer.py"]),
    ("src/engineering_intelligence_framework/commands/skills.py", [
        "test_skill_contracts.py",
        "test_skill_eval.py",
        "test_project_skills.py",
    ]),
    ("src/engineering_intelligence_framework/commands/workspace.py", [
        "test_workspace_commands.py",
        "test_workspace_resolution.py",
        "test_workspace_fleet.py",
    ]),
    ("src/engineering_intelligence_framework/commands/projects.py", [
        "test_project_commands.py",
        "test_workspace_fleet.py",
        "test_workspace_transaction.py",
    ]),
    ("src/engineering_intelligence_framework/commands/session.py", ["test_session_commands.py"]),
    # scripts/tests/ is handled dynamically in route(): editing test_X.py
    # selects test_X.py. Runner and helper edits fall through to the rule
    # below them.
    ("scripts/tests/", []),
    ("scripts/eif_init.py", ["test_init.py", "test_adoption.py", "test_journey.py", "test_markers.py"]),
    ("scripts/eif_sync_skills.py", ["test_sync_skills.py", "test_skill_contracts.py"]),
    ("scripts/eif_validate_frontmatter.py", ["test_validate.py"]),
    ("scripts/eif_privacy_scan.py", ["test_privacy_scan.py"]),
    ("scripts/eif_generate_index.py", ["test_generate_index.py"]),
    ("scripts/eif_search_knowledge.py", ["test_search_knowledge.py"]),
    ("scripts/eif_benchmark.py", ["test_benchmark.py"]),
    ("scripts/sync_package_sources.py", ["test_sync_skills.py", "test_parity_matrix.py"]),
    # Prose that ships no behavior.
    ("scripts/README.md", ["test_check_links.py"]),
    ("docs/", ["test_check_links.py"]),
    ("adapters/README.md", ["test_check_links.py"]),
    ("CONTRIBUTING.md", ["test_check_links.py"]),
    ("GOVERNANCE.md", ["test_check_links.py"]),
    ("SECURITY.md", ["test_check_links.py"]),
    ("THIRD_PARTY_NOTICES.md", ["test_check_licenses.py"]),
    ("planning/", []),
    ("site/", []),
    ("examples/", []),
    ("CHANGELOG.md", []),
    ("README.md", ["test_check_links.py"]),
    ("ROADMAP.md", []),
]


def changed_paths(base: str | None) -> list[str]:
    if base is None:
        merge_base = subprocess.run(
            ["git", "merge-base", "HEAD", "main"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        base = merge_base.stdout.strip() if merge_base.returncode == 0 else "HEAD~1"
    result = subprocess.run(
        ["git", "diff", "--name-only", base, "--"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    tracked = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    tracked += [line.strip() for line in untracked.stdout.splitlines() if line.strip()]
    return sorted(set(tracked))


def route(paths: list[str]) -> tuple[list[str], list[str], bool]:
    """Returns (suites, unmatched_paths, escalate_to_full)."""
    selected: list[str] = []
    unmatched: list[str] = []
    for path in paths:
        # A changed test suite runs itself. Nothing else knows that mapping,
        # and it is exact rather than a guess.
        name = Path(path).name
        if path.startswith("scripts/tests/") and name.startswith("test_") and name.endswith(".py"):
            if name not in selected:
                selected.append(name)
            continue
        for prefix, suites in RULES:
            hit = path.startswith(prefix) if prefix.endswith("/") else path == prefix
            if hit:
                for suite in suites:
                    if suite not in selected:
                        selected.append(suite)
                break
        else:
            unmatched.append(path)
    return selected, unmatched, bool(unmatched)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=None, help="Git ref to diff against. Default: merge-base with main.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan and exit 0 without running anything.")
    parser.add_argument("--paths", nargs="*", default=None, help="Route these paths instead of asking git.")
    args = parser.parse_args()

    paths = args.paths if args.paths is not None else changed_paths(args.base)
    if not paths:
        print("route_changed: no changed paths; nothing to run.")
        return 0

    selected, unmatched, escalate = route(paths)

    print(f"route_changed: {len(paths)} changed path(s)")
    for path in paths:
        print(f"  {path}")

    if escalate:
        print("\nroute_changed: unclassified path(s), escalating to the full inventory:")
        for path in unmatched:
            print(f"  {path}")
        print("\nroute_changed: add a rule for these in RULES if this repeats.")
        plan = ["run_all.py"]
    else:
        plan = BASE_SUITES + sorted(selected)
        print(f"\nroute_changed: selected {len(plan)} suite(s)")
        for suite in plan:
            print(f"  {suite}")

    if args.dry_run:
        print("\nroute_changed: dry run, nothing executed.")
        return 0

    print()
    failures: list[str] = []
    for suite in plan:
        if suite == "run_all.py":
            command = [sys.executable, str(TESTS_DIR / "run_all.py")]
        elif suite == "smoke.py":
            command = [sys.executable, str(TESTS_DIR / "smoke.py")]
        else:
            command = [sys.executable, str(TESTS_DIR / "run_all.py"), "--only", suite]
        completed = subprocess.run(command, cwd=REPO_ROOT)
        if completed.returncode != 0:
            failures.append(suite)

    if failures:
        print(f"\nroute_changed: FAILED {', '.join(failures)}")
        return 1
    print(f"\nroute_changed: all {len(plan)} selected suite(s) passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
