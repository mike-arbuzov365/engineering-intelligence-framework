"""Fail-closed guard для EIF-managed graphic-design package і delivery."""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..workspace_contract import WorkspaceContractError, read_yaml
from ..workspace_materialization import verify_workspace_materialization

APPROVAL_SCHEMA = "design-delivery-approval.schema.json"
APPROVAL_PATH = Path(".eif/local-state/design-delivery-approval.yaml")
REQUIRED_RULE_NAME = "design-delivery-approval"
REQUIRED_RULE_ARTIFACT = f"rule/{REQUIRED_RULE_NAME}"
REQUIRED_RULE_PATH = f"rules/{REQUIRED_RULE_NAME}.md"
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


class DeliveryGuardError(RuntimeError):
    """EIF-managed delivery action не має valid owner-gated approval."""


def _timestamp(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise DeliveryGuardError(f"{label} must be ISO 8601 date-time") from error
    if parsed.tzinfo is None:
        raise DeliveryGuardError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _scope(value: str) -> str:
    path = Path(value)
    if (
        not value
        or path.is_absolute()
        or WINDOWS_DRIVE.match(value)
        or value.startswith(("/", "\\"))
        or ".." in path.parts
    ):
        raise DeliveryGuardError("scope must be a bounded relative identifier")
    return value


def _required_rule(lock: dict[str, Any], project: Path) -> None:
    workspace = lock.get("workspace") or {}
    if workspace.get("profile") != "graphic-design":
        raise DeliveryGuardError("active workspace profile is not graphic-design")

    manifest = (lock.get("bundle") or {}).get("manifest") or []
    matches = [
        item
        for item in manifest
        if isinstance(item, dict)
        and item.get("kind") == "rule"
        and item.get("name") == REQUIRED_RULE_NAME
    ]
    if len(matches) != 1:
        raise DeliveryGuardError("required design-delivery-approval rule is missing or ambiguous")
    rule = matches[0]
    if rule.get("mode") != "required" or rule.get("path") != REQUIRED_RULE_PATH:
        raise DeliveryGuardError("design-delivery-approval rule is not pinned as required")

    exceptions = (lock.get("resolution") or {}).get("required_exceptions") or []
    if any(
        isinstance(item, dict) and item.get("artifact") == REQUIRED_RULE_ARTIFACT
        for item in exceptions
    ):
        raise DeliveryGuardError(
            "design-delivery-approval required rule has an exception; "
            "EIF-managed package/delivery remains blocked"
        )

    runtime_rule = project / ".eif" / "workspace-runtime" / REQUIRED_RULE_PATH
    if not runtime_rule.is_file():
        raise DeliveryGuardError("required design-delivery-approval runtime rule is missing")


def _evidence(project: Path, value: str) -> None:
    if value.startswith("https://"):
        return
    path = Path(value)
    if path.is_absolute() or WINDOWS_DRIVE.match(value) or ".." in path.parts:
        raise DeliveryGuardError("approval evidence_ref escapes project boundary")
    candidate = (project / path).resolve()
    if not candidate.is_relative_to(project.resolve()):
        raise DeliveryGuardError("approval evidence_ref escapes project boundary")
    if not candidate.is_file():
        raise DeliveryGuardError(f"approval evidence_ref is missing: {value}")


def check_delivery(
    project: Path,
    *,
    action: str,
    scope: str,
    at: datetime | None = None,
) -> dict[str, Any]:
    """Повертає valid approval або fail-closed з exact reason."""
    project = project.expanduser().resolve()
    _scope(scope)
    if action not in {"package", "final_delivery"}:
        raise DeliveryGuardError(f"unsupported delivery action: {action}")

    read_yaml(project / ".eif" / "config.yaml", "eif-config.schema.json", "EIF config")
    read_yaml(
        project / ".eif" / "framework.lock.yaml",
        "framework-lock.schema.json",
        "framework lock",
    )
    workspace_lock = read_yaml(
        project / ".eif" / "workspace.lock.yaml",
        "workspace-lock.schema.json",
        "workspace lock",
    )
    workspace_problems = verify_workspace_materialization(project)
    if workspace_problems:
        raise DeliveryGuardError(
            "workspace materialization is invalid: " + "; ".join(workspace_problems)
        )
    _required_rule(workspace_lock, project)

    approval_path = project / APPROVAL_PATH
    if not approval_path.is_file():
        raise DeliveryGuardError(
            f"approval state is missing at {APPROVAL_PATH.as_posix()}; "
            "package_allowed defaults to false"
        )
    approval = read_yaml(approval_path, APPROVAL_SCHEMA, "design delivery approval")
    if approval.get("package_allowed") is not True:
        raise DeliveryGuardError("package_allowed is false")

    decision = approval.get("decision") or {}
    if decision.get("scope") != scope:
        raise DeliveryGuardError(
            f"approval scope mismatch: requested={scope!r} approved={decision.get('scope')!r}"
        )
    if action not in (decision.get("actions") or []):
        raise DeliveryGuardError(f"approval does not include action {action!r}")

    decided_at = _timestamp(str(decision.get("decided_at", "")), "decided_at")
    valid_until = _timestamp(str(decision.get("valid_until", "")), "valid_until")
    now = (at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if decided_at > now:
        raise DeliveryGuardError("approval decision timestamp is in the future")
    if valid_until <= decided_at:
        raise DeliveryGuardError("valid_until must be after decided_at")
    if now >= valid_until:
        raise DeliveryGuardError("approval has expired")

    _evidence(project, str(decision.get("evidence_ref", "")))
    return approval


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eifctl delivery", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser(
        "check",
        help="Validate owner-gated package/final-delivery state without packaging files.",
    )
    check.add_argument("--action", required=True, choices=("package", "final_delivery"))
    check.add_argument("--scope", required=True)
    check.add_argument("--instance-path", default=".", type=Path)
    return parser


def run(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    try:
        check_delivery(
            args.instance_path,
            action=args.action,
            scope=args.scope,
        )
    except (DeliveryGuardError, WorkspaceContractError, OSError) as error:
        print(f"BLOCKED delivery approval: {error}", file=sys.stderr)
        print("enforcement=machine", file=sys.stderr)
        print("approval_origin=owner_gate", file=sys.stderr)
        print("external_shell_enforcement=instruction_only", file=sys.stderr)
        return 1

    print(f"PASS delivery approval: action={args.action} scope={args.scope}")
    print("enforcement=machine")
    print("approval_origin=owner_gate")
    print("external_shell_enforcement=instruction_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
