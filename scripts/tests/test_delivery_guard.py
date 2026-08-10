#!/usr/bin/env python3
"""Behavioral tests для graphic-design package/final-delivery guard."""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts" / "tests"))

from engineering_intelligence_framework import cli  # noqa: E402
from engineering_intelligence_framework.commands import init_cmd  # noqa: E402
from engineering_intelligence_framework.workspace_materialization import (  # noqa: E402
    materialize_workspace,
)
from workspace_test_support import commit_all  # noqa: E402

AT = "2026-08-09T12:00:00Z"
SCOPE = "campaign-q3-final"


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def invoke(
    project: Path,
    *,
    action: str = "package",
    scope: str = SCOPE,
) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli.main(
            [
                "delivery",
                "check",
                "--action",
                action,
                "--scope",
                scope,
                "--instance-path",
                str(project),
            ]
        )
    return rc, out.getvalue(), err.getvalue()


def invoke_with_time_override(project: Path) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc = cli.main(
                [
                    "delivery",
                    "check",
                    "--action",
                    "package",
                    "--scope",
                    SCOPE,
                    "--instance-path",
                    str(project),
                    "--at",
                    AT,
                ]
            )
        except SystemExit as error:
            rc = int(error.code)
    return rc, out.getvalue(), err.getvalue()


def approval(
    project: Path,
    *,
    allowed: bool = True,
    scope: str = SCOPE,
    actions: list[str] | None = None,
    decided_at: str = "2000-01-01T00:00:00Z",
    valid_until: str = "2099-01-01T00:00:00Z",
    evidence_ref: str = "planning/approvals/design-delivery.md",
) -> Path:
    path = project / ".eif" / "local-state" / "design-delivery-approval.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {
        "schema_version": 1,
        "profile": "graphic-design",
        "package_allowed": allowed,
    }
    if allowed:
        data["decision"] = {
            "owner": "owner-reference",
            "scope": scope,
            "actions": actions or ["package", "final_delivery"],
            "decided_at": decided_at,
            "valid_until": valid_until,
            "evidence_ref": evidence_ref,
        }
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    return path


def main() -> int:
    results: list[tuple[bool, str]] = []
    real_init_run = init_cmd.run
    init_cmd.run = lambda argv: real_init_run(  # type: ignore[assignment]
        [*argv, "--allow-dirty"]
    )
    try:
        with tempfile.TemporaryDirectory(prefix="eif-delivery-guard-") as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            project = root / "project"
            workspace_new = cli.main(["workspace", "new", str(workspace)])
            profile_install = cli.main(
                [
                    "workspace",
                    "profile",
                    "install",
                    "graphic-design",
                    "--workspace-path",
                    str(workspace),
                ]
            )
            if workspace_new == 0 and profile_install == 0:
                commit_all(workspace, "install graphic design profile")
            registry = workspace / ".eif" / "projects.yaml"
            project_new = cli.main(
                [
                    "new",
                    str(project),
                    "--project-name",
                    "design-project",
                    "--adapter",
                    "codex",
                    "--locale",
                    "uk",
                    "--profile",
                    "graphic-design",
                    "--registry",
                    str(registry),
                ]
            )
            if project_new == 0:
                commit_all(workspace, "register design project")
                commit_all(project, "bootstrap design project")
                materialize_workspace(
                    workspace,
                    project,
                    profile_name="graphic-design",
                    framework_version="0.2.7",
                )
            results.append(
                check(
                    "graphic-design fixture materializes",
                    workspace_new == profile_install == project_new == 0
                    and (project / ".eif" / "workspace.lock.yaml").is_file(),
                )
            )

            lock_path = project / ".eif" / "workspace.lock.yaml"
            lock = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
            rule_entries = [
                item
                for item in lock["bundle"]["manifest"]
                if item["kind"] == "rule"
                and item["name"] == "design-delivery-approval"
            ]
            results.append(
                check(
                    "required rule and false-default template materialize",
                    len(rule_entries) == 1
                    and rule_entries[0]["mode"] == "required"
                    and rule_entries[0]["path"]
                    == "rules/design-delivery-approval.md"
                    and (
                        project
                        / ".eif"
                        / "workspace-runtime"
                        / "templates"
                        / "design-package-approval.yaml"
                    ).is_file(),
                )
            )
            approval_template = yaml.safe_load(
                (
                    project
                    / ".eif"
                    / "workspace-runtime"
                    / "templates"
                    / "design-package-approval.yaml"
                ).read_text(encoding="utf-8")
            )
            results.append(
                check(
                    "approval starter remains schema-compatible YAML data",
                    approval_template
                    == {
                        "schema_version": 1,
                        "profile": "graphic-design",
                        "package_allowed": False,
                    },
                    repr(approval_template),
                )
            )

            missing = invoke(project)
            results.append(
                check(
                    "missing approval defaults package_allowed to false",
                    missing[0] != 0
                    and "package_allowed defaults to false" in missing[2],
                    missing[1] + missing[2],
                )
            )

            approval(project, allowed=False)
            denied = invoke(project)
            results.append(
                check(
                    "explicit package_allowed false blocks",
                    denied[0] != 0 and "package_allowed is false" in denied[2],
                    denied[1] + denied[2],
                )
            )

            evidence = project / "planning" / "approvals" / "design-delivery.md"
            evidence.parent.mkdir(parents=True)
            evidence.write_text("# Owner approval evidence\n", encoding="utf-8")
            approval(project)
            accepted_package = invoke(project)
            accepted_delivery = invoke(project, action="final_delivery")
            results.append(
                check(
                    "valid exact-scope approval passes package and final delivery",
                    accepted_package[0] == 0
                    and accepted_delivery[0] == 0
                    and "enforcement=machine" in accepted_package[1]
                    and "approval_origin=owner_gate" in accepted_package[1]
                    and "external_shell_enforcement=instruction_only"
                    in accepted_package[1],
                    "".join(accepted_package[1:] + accepted_delivery[1:]),
                )
            )

            time_override = invoke_with_time_override(project)
            results.append(
                check(
                    "public CLI rejects approval-clock override",
                    time_override[0] == 2
                    and "unrecognized arguments: --at" in time_override[2],
                    time_override[1] + time_override[2],
                )
            )

            wrong_scope = invoke(project, scope="other-delivery")
            results.append(
                check(
                    "wrong scope blocks",
                    wrong_scope[0] != 0 and "scope mismatch" in wrong_scope[2],
                    wrong_scope[1] + wrong_scope[2],
                )
            )

            approval(project, actions=["final_delivery"])
            wrong_action = invoke(project, action="package")
            results.append(
                check(
                    "unapproved action blocks",
                    wrong_action[0] != 0
                    and "does not include action" in wrong_action[2],
                    wrong_action[1] + wrong_action[2],
                )
            )

            approval(
                project,
                decided_at="2000-01-01T00:00:00Z",
                valid_until="2000-01-02T00:00:00Z",
            )
            expired = invoke(project)
            results.append(
                check(
                    "expired approval blocks",
                    expired[0] != 0 and "approval has expired" in expired[2],
                    expired[1] + expired[2],
                )
            )

            approval(
                project,
                decided_at="2099-01-01T00:00:00Z",
                valid_until="2100-01-01T00:00:00Z",
            )
            future = invoke(project)
            results.append(
                check(
                    "future decision timestamp blocks",
                    future[0] != 0 and "timestamp is in the future" in future[2],
                    future[1] + future[2],
                )
            )

            approval(project, evidence_ref="planning/approvals/missing.md")
            no_evidence = invoke(project)
            results.append(
                check(
                    "missing local evidence reference blocks",
                    no_evidence[0] != 0 and "evidence_ref is missing" in no_evidence[2],
                    no_evidence[1] + no_evidence[2],
                )
            )

            approval(project)
            original_lock = lock_path.read_bytes()
            exception_lock = yaml.safe_load(original_lock)
            exception_lock["resolution"]["required_exceptions"].append(
                {
                    "artifact": "rule/design-delivery-approval",
                    "reason": "synthetic override attempt",
                    "approved_by": "test-owner",
                }
            )
            lock_path.write_text(
                yaml.safe_dump(exception_lock, sort_keys=False), encoding="utf-8"
            )
            exception = invoke(project)
            results.append(
                check(
                    "required-rule exception keeps EIF-managed delivery blocked",
                    exception[0] != 0
                    and "required rule has an exception" in exception[2],
                    exception[1] + exception[2],
                )
            )
            lock_path.write_bytes(original_lock)

            rule_path = (
                project
                / ".eif"
                / "workspace-runtime"
                / "rules"
                / "design-delivery-approval.md"
            )
            rule_bytes = rule_path.read_bytes()
            rule_path.unlink()
            missing_rule = invoke(project)
            results.append(
                check(
                    "missing required runtime rule blocks",
                    missing_rule[0] != 0
                    and "workspace materialization is invalid" in missing_rule[2],
                    missing_rule[1] + missing_rule[2],
                )
            )
            rule_path.write_bytes(rule_bytes)

            escape = invoke(project, scope="../escape")
            results.append(
                check(
                    "scope traversal blocks before approval use",
                    escape[0] != 0 and "bounded relative identifier" in escape[2],
                    escape[1] + escape[2],
                )
            )

            approval_path = approval(project)
            malformed = yaml.safe_load(approval_path.read_text(encoding="utf-8"))
            del malformed["decision"]["owner"]
            approval_path.write_text(
                yaml.safe_dump(malformed, sort_keys=False), encoding="utf-8"
            )
            malformed_result = invoke(project)
            results.append(
                check(
                    "missing owner metadata blocks at schema gate",
                    malformed_result[0] != 0
                    and "schema validation failed" in malformed_result[2],
                    malformed_result[1] + malformed_result[2],
                )
            )

            playbook = (
                ROOT
                / "professional-profiles"
                / "graphic-design"
                / "playbooks"
                / "graphic-design-project.md"
            ).read_text(encoding="utf-8")
            delivery_template = (
                ROOT
                / "professional-profiles"
                / "graphic-design"
                / "templates"
                / "design-delivery.md"
            ).read_text(encoding="utf-8")
            required_rule = (
                ROOT
                / "professional-profiles"
                / "graphic-design"
                / "rules"
                / "design-delivery-approval.md"
            ).read_text(encoding="utf-8")
            results.append(
                check(
                    "changed-only versus full QA contract is explicit and bounded",
                    all(
                        token in playbook
                        for token in (
                            "changed_only",
                            "shared/global",
                            "full` QA",
                            "не automatic dependency engine",
                        )
                    )
                    and "Dependency uncertainty" in delivery_template,
                )
            )
            results.append(
                check(
                    "external shell limitation is explicit",
                    "instruction_only" in required_rule
                    and "Довільна external ZIP" in required_rule
                    and "verified adapter guard" in required_rule,
                )
            )
    finally:
        init_cmd.run = real_init_run  # type: ignore[assignment]

    for passed, message in results:
        print(message)
    passed_count = sum(1 for passed, _message in results if passed)
    print(f"EIF-RESULT: passed={passed_count} total={len(results)}")
    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
