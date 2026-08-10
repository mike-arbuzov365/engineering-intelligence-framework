"""Deterministic model-free команди для session continuity."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, urlencode

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .._impl import eif_locale
from ..resources import framework_root
from ..workspace_contract import WorkspaceContractError, read_yaml, schema_data, stable_project_id

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SECRET_SOURCE_NAMES = {"credentials", "credential", "secrets", "secret"}


class SessionError(ValueError):
    """Session state is absent, invalid, stale, or bound to another project."""


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(
    path: Path,
    content: str,
    *,
    replace: Callable[[Path, Path], None] = os.replace,
) -> None:
    """Write one complete checkpoint or preserve the prior file unchanged."""
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f"{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        with staging.open("wb") as stream:
            stream.write(content.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        replace(staging, path)
    except BaseException:
        staging.unlink(missing_ok=True)
        raise


def _normalize_yaml_scalars(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_yaml_scalars(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_yaml_scalars(item) for item in value]
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return value


def _parse_checkpoint(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SessionError(f"checkpoint not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SessionError(f"cannot read checkpoint {path}: {exc}") from exc
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise SessionError(f"checkpoint has no YAML frontmatter: {path}")
    try:
        data = _normalize_yaml_scalars(yaml.safe_load(match.group(1)) or {})
    except yaml.YAMLError as exc:
        raise SessionError(f"checkpoint has invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise SessionError("checkpoint frontmatter must be a YAML mapping")
    return data


def _schema_errors(data: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(
        schema_data("session-context.schema.json"),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    return [
        f"{'.'.join(str(item) for item in error.path) or '(root)'}: {error.message}"
        for error in errors
    ]


def _continuity_matrix() -> dict[str, Any]:
    with framework_root() as root:
        path = root / "adapters" / "parity-matrix.json"
        if not path.is_file():
            raise SessionError(f"adapter continuity matrix is missing: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SessionError(f"cannot read adapter continuity matrix: {exc}") from exc
    errors = sorted(
        Draft202012Validator(
            schema_data("adapter-continuity-capabilities.schema.json")
        ).iter_errors(data),
        key=lambda error: list(error.path),
    )
    if errors:
        rendered = []
        for error in errors:
            dotted = ".".join(str(part) for part in error.path) or "<root>"
            rendered.append(f"{dotted}: {error.message}")
        raise SessionError("invalid adapter continuity matrix: " + "; ".join(rendered))
    return data


def _codex_deep_link(project_root: Path, prompt: str) -> str:
    root = project_root.expanduser().resolve()
    query = urlencode(
        {"prompt": prompt, "path": str(root)},
        quote_via=quote,
        safe="",
    )
    return f"codex://threads/new?{query}"


def _safe_source_artifact(project_root: Path, raw: str) -> tuple[Path, str]:
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()
    try:
        relative = resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise SessionError(
            f"source artifact resolves outside the project root: {raw!r}"
        ) from exc
    lower_parts = [part.casefold() for part in relative.parts]
    if any(
        part == ".git"
        or part == ".env"
        or part.startswith(".env.")
        or part in SECRET_SOURCE_NAMES
        for part in lower_parts
    ):
        raise SessionError(
            "source artifact must not be a Git-internal, environment, credential, or secret file"
        )
    if not resolved.is_file():
        raise SessionError(f"source artifact is not a file: {relative.as_posix()}")
    return resolved, relative.as_posix()


def _load_project(project_root: Path) -> dict[str, Any]:
    project_root = project_root.expanduser().resolve()
    config_path = project_root / ".eif" / "config.yaml"
    lock_path = project_root / ".eif" / "framework.lock.yaml"
    if not project_root.is_dir() or not config_path.is_file() or not lock_path.is_file():
        raise SessionError(
            f"not a complete EIF project at {project_root}; "
            ".eif/config.yaml and .eif/framework.lock.yaml are required"
        )
    config = read_yaml(
        config_path,
        "eif-config.schema.json",
        "project config",
    )
    lock = read_yaml(
        lock_path,
        "framework-lock.schema.json",
        "framework lock",
    )
    name = str((config.get("project") or {}).get("name", ""))
    config_adapter = str((config.get("adapter") or {}).get("name", ""))
    lock_adapter = str((lock.get("adapter") or {}).get("name", ""))
    if not name:
        raise SessionError("project config has no project.name")
    if config_adapter != lock_adapter:
        raise SessionError(
            f"config-lock adapter mismatch: config={config_adapter!r}, lock={lock_adapter!r}"
        )
    locale = str(
        ((config.get("localization") or {}).get("documentation_locale")) or "en"
    )
    return {
        "id": stable_project_id(name),
        "name": name,
        "root": str(project_root),
        "config_path": ".eif/config.yaml",
        "config_sha256": _sha256(config_path),
        "lock_path": ".eif/framework.lock.yaml",
        "lock_sha256": _sha256(lock_path),
        "adapter": config_adapter,
        "locale": locale,
    }


def _run_git(project_root: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        capture_output=True,
        check=False,
    )


def _decode_path(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace").replace("\\", "/")


def _git_snapshot(project_root: Path) -> dict[str, Any]:
    top = _run_git(project_root, ["rev-parse", "--show-toplevel"])
    if top.returncode != 0:
        payload = json.dumps({"repository": False}, sort_keys=True).encode("utf-8")
        return {
            "repository": False,
            "root": None,
            "branch": None,
            "head": None,
            "status_fingerprint": hashlib.sha256(payload).hexdigest(),
            "changed_files": [],
        }

    git_root = Path(_decode_path(top.stdout).strip()).resolve()
    branch_proc = _run_git(project_root, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    branch = _decode_path(branch_proc.stdout).strip() if branch_proc.returncode == 0 else None
    head_proc = _run_git(project_root, ["rev-parse", "--verify", "HEAD"])
    head = _decode_path(head_proc.stdout).strip() if head_proc.returncode == 0 else None
    status_proc = _run_git(
        project_root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    )
    if status_proc.returncode != 0:
        detail = _decode_path(status_proc.stderr).strip()
        raise SessionError(f"cannot inspect Git status: {detail or 'unknown error'}")

    records = status_proc.stdout.split(b"\0")
    status_items: list[tuple[str, str]] = []
    changed: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4:
            raise SessionError("Git returned an invalid porcelain status record")
        code = record[:2].decode("ascii", errors="replace")
        path = _decode_path(record[3:])
        status_items.append((code, path))
        changed.add(path)
        if "R" in code or "C" in code:
            if index < len(records) and records[index]:
                old_path = _decode_path(records[index])
                status_items.append(("source", old_path))
                changed.add(old_path)
                index += 1

    metadata: list[dict[str, Any]] = []
    for path in sorted(changed):
        candidate = (git_root / path).resolve()
        try:
            candidate.relative_to(git_root)
        except ValueError:
            metadata.append({"path": path, "outside": True})
            continue
        try:
            stat = candidate.lstat()
        except OSError:
            metadata.append({"path": path, "missing": True})
        else:
            metadata.append(
                {
                    "path": path,
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                    "directory": candidate.is_dir(),
                }
            )

    payload = json.dumps(
        {
            "root": str(git_root),
            "branch": branch,
            "head": head,
            "status": sorted(status_items),
            "metadata": metadata,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "repository": True,
        "root": str(git_root),
        "branch": branch,
        "head": head,
        "status_fingerprint": hashlib.sha256(payload).hexdigest(),
        "changed_files": sorted(changed),
    }


def _parse_verification(values: list[str] | None) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    for raw in values or []:
        parts = raw.split("::", 2)
        if len(parts) < 2 or parts[0] not in {"pass", "fail", "skipped", "not_run"}:
            raise SessionError(
                "--verification must be RESULT::COMMAND or RESULT::COMMAND::EVIDENCE, "
                "where RESULT is pass, fail, skipped, or not_run"
            )
        result, command = parts[0], parts[1].strip()
        if not command:
            raise SessionError("--verification command must not be empty")
        item = {"command": command, "result": result}
        if len(parts) == 3 and parts[2].strip():
            item["evidence"] = parts[2].strip()
        checks.append(item)
    if not checks:
        status = "not_run"
    elif any(item["result"] == "fail" for item in checks):
        status = "fail"
    elif all(item["result"] == "pass" for item in checks):
        status = "pass"
    else:
        status = "partial"
    return {"status": status, "checks": checks}


def _render_checkpoint(data: dict[str, Any], locale: str) -> str:
    with framework_root() as root:
        body, _used_locale = eif_locale.render_template(
            root,
            locale,
            "session-context.md",
            session_id=data["logical_session"]["id"],
        )
    frontmatter = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    return f"---\n{frontmatter}---\n{body}"


def _validate_checkpoint(
    path: Path,
    *,
    project_root: Path | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        data = _parse_checkpoint(path)
    except SessionError as exc:
        return None, [str(exc)]
    errors = _schema_errors(data)
    if errors:
        return data, errors

    stored_root = Path(data["project"]["root"]).resolve()
    effective_root = project_root.expanduser().resolve() if project_root else stored_root
    expected_parent = effective_root / ".session-context"
    if path.resolve().parent != expected_parent.resolve():
        errors.append(
            f"checkpoint_path: expected a direct child of {expected_parent}, got {path.resolve()}"
        )
    expected_name = f"{data['logical_session']['id']}.md"
    if path.name != expected_name:
        errors.append(
            f"checkpoint_name: expected {expected_name!r}, got {path.name!r}"
        )
    try:
        _safe_source_artifact(effective_root, data["source_artifact"]["path"])
    except SessionError as exc:
        errors.append(f"source_artifact: {exc}")
    return data, errors


def _audit_checkpoint(
    path: Path,
    project_root: Path,
) -> tuple[dict[str, Any] | None, list[tuple[str, Any, Any]]]:
    data, validation_errors = _validate_checkpoint(path)
    if validation_errors or data is None:
        return data, [("schema", "valid checkpoint", error) for error in validation_errors]

    mismatches: list[tuple[str, Any, Any]] = []
    active = _load_project(project_root)
    for field in (
        "id",
        "name",
        "root",
        "config_sha256",
        "lock_sha256",
        "adapter",
    ):
        expected = data["project"][field]
        actual = active[field]
        if expected != actual:
            mismatches.append((f"project_{field}", expected, actual))

    try:
        source, _relative = _safe_source_artifact(
            project_root.resolve(), data["source_artifact"]["path"]
        )
    except SessionError as exc:
        mismatches.append(("source_artifact", "existing safe file", str(exc)))
    else:
        actual_hash = _sha256(source)
        if data["source_artifact"]["sha256"] != actual_hash:
            mismatches.append(
                (
                    "source_artifact_hash",
                    data["source_artifact"]["sha256"],
                    actual_hash,
                )
            )

    current_git = _git_snapshot(project_root.resolve())
    for field in ("repository", "root", "branch", "head", "status_fingerprint", "changed_files"):
        if data["git"][field] != current_git[field]:
            mismatches.append(
                (f"git_{field}", data["git"][field], current_git[field])
            )
    return data, mismatches


def _checkpoint(args: argparse.Namespace) -> int:
    if not SESSION_ID_RE.fullmatch(args.session_id):
        raise SessionError(
            "--session-id must start with an alphanumeric character and contain "
            "only alphanumerics, dot, underscore, or hyphen"
        )
    project_root = Path(args.project_root).expanduser().resolve()
    project = _load_project(project_root)
    source_path, source_relative = _safe_source_artifact(
        project_root, args.source_artifact
    )
    if args.approval_state == "approved" and not args.approval_evidence:
        raise SessionError(
            "--approval-evidence is required when --approval-state=approved"
        )

    git_state = _git_snapshot(project_root)
    checkpoint_path = project_root / ".session-context" / f"{args.session_id}.md"
    existing: dict[str, Any] | None = None
    if checkpoint_path.exists():
        existing = _parse_checkpoint(checkpoint_path)
        existing_errors = _schema_errors(existing)
        if existing_errors:
            raise SessionError(
                "refusing to replace an invalid existing checkpoint: "
                + "; ".join(existing_errors)
            )
        immutable_pairs = (
            ("project.id", existing["project"]["id"], project["id"]),
            (
                "logical_session.id",
                existing["logical_session"]["id"],
                args.session_id,
            ),
            (
                "source_artifact.path",
                existing["source_artifact"]["path"],
                source_relative,
            ),
        )
        conflicts = [
            f"{label}: existing={old!r}, requested={new!r}"
            for label, old, new in immutable_pairs
            if old != new
        ]
        if conflicts:
            raise SessionError(
                "refusing to change checkpoint identity: " + "; ".join(conflicts)
            )

    observed_at = _utc_now()
    physical_chats = list((existing or {}).get("physical_chats", []))
    if args.physical_chat_ref and not any(
        item["adapter"] == project["adapter"]
        and item["ref"] == args.physical_chat_ref
        for item in physical_chats
    ):
        physical_chats.append(
            {
                "adapter": project["adapter"],
                "ref": args.physical_chat_ref,
                "observed_at": observed_at,
            }
        )

    data = {
        "schema_version": 1,
        "artifact_type": "session_context",
        "status": args.status,
        "updated_at": observed_at,
        "project": {key: value for key, value in project.items() if key != "locale"},
        "source_artifact": {
            "path": source_relative,
            "sha256": _sha256(source_path),
        },
        "logical_session": {
            "id": args.session_id,
            "continuation_mode": args.continuation_mode,
            "adapter": project["adapter"],
        },
        "goal": args.goal,
        "scope": {"in_scope": args.in_scope, "no_touch": args.no_touch},
        "approvals": {
            "state": args.approval_state,
            "evidence": args.approval_evidence or [],
        },
        "decisions": args.decision or [],
        "progress": {
            "completed": args.completed or [],
            "changed_artifacts": git_state["changed_files"],
        },
        "verification": _parse_verification(args.verification),
        "blockers": args.blocker or [],
        "failed_approaches": args.failed_approach or [],
        "unresolved_risks": args.risk or [],
        "next_action": args.next_action,
        "git": git_state,
        "physical_chats": physical_chats,
    }
    errors = _schema_errors(data)
    if errors:
        raise SessionError("generated checkpoint is invalid: " + "; ".join(errors))
    _atomic_write(checkpoint_path, _render_checkpoint(data, project["locale"]))
    print(f"PASS session checkpoint: {checkpoint_path}")
    print(f"project_id={project['id']}")
    print(f"logical_session={args.session_id}")
    print(f"continuation_mode={args.continuation_mode}")
    print(f"status={args.status}")
    return 0


def _validate(args: argparse.Namespace) -> int:
    path = Path(args.checkpoint).expanduser().resolve()
    project_root = (
        Path(args.project_root).expanduser().resolve()
        if args.project_root is not None
        else None
    )
    data, errors = _validate_checkpoint(path, project_root=project_root)
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1
    assert data is not None
    print(f"PASS session checkpoint validation: {path}")
    print(f"logical_session={data['logical_session']['id']}")
    print(f"status={data['status']}")
    return 0


def _resume_audit(args: argparse.Namespace) -> int:
    path = Path(args.checkpoint).expanduser().resolve()
    project_root = Path(args.project_root).expanduser().resolve()
    data, mismatches = _audit_checkpoint(path, project_root)
    if mismatches:
        for key, expected, actual in mismatches:
            print(
                f"FAIL {key}: expected={expected!r} actual={actual!r}",
                file=sys.stderr,
            )
        return 1
    assert data is not None
    print(f"PASS session resume audit: {path}")
    print(f"project_id={data['project']['id']}")
    print(f"logical_session={data['logical_session']['id']}")
    print(f"approval_state={data['approvals']['state']}")
    print(f"next_action={data['next_action']}")
    return 0


def _handoff(args: argparse.Namespace) -> int:
    path = Path(args.checkpoint).expanduser().resolve()
    project_root = Path(args.project_root).expanduser().resolve()
    data, mismatches = _audit_checkpoint(path, project_root)
    if mismatches:
        for key, expected, actual in mismatches:
            print(
                f"FAIL {key}: expected={expected!r} actual={actual!r}",
                file=sys.stderr,
            )
        return 1
    assert data is not None
    mode = args.mode or data["logical_session"]["continuation_mode"]
    adapter = data["project"]["adapter"]
    capabilities = _continuity_matrix()["adapters"][adapter]
    relative = path.relative_to(project_root).as_posix()
    if mode == "same_chat":
        print("strategy=same_chat")
        print("automation=none")
        print(f"adapter={adapter}")
        print(f"same_chat_status={capabilities['same_chat']['status']}")
        print(f"same_chat_action={capabilities['same_chat']['action']}")
        print(f"checkpoint={relative}")
        print(f"action={data['next_action']}")
        return 0

    prompt = (
        "Продовж логічну session "
        f"{data['logical_session']['id']} для project {data['project']['id']}. "
        f"Прочитай і перевір {relative} перед виконанням next action."
    )
    print("strategy=manual_new_chat")
    print("automation=none")
    print(f"adapter={adapter}")
    print(f"requested_mode={mode}")
    for name in ("resume", "create_new_chat", "open_new_chat", "auto_submit"):
        print(f"{name}_status={capabilities[name]['status']}")
        print(f"{name}_evidence_status={capabilities[name]['evidence_status']}")
    print("reason=no adapter capability has observed auto_action=true")
    print(f"manual_action={capabilities['create_new_chat']['action']}")
    print(f"checkpoint={relative}")
    print(f"prompt={prompt}")
    if adapter == "codex":
        print(f"candidate_link={_codex_deep_link(project_root, prompt)}")
        print("candidate_link_status=manual_only_canary_inconclusive")
    if args.open:
        print(
            f"FAIL automatic open is not verified for adapter {adapter}; "
            "use manual_action",
            file=sys.stderr,
        )
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eifctl session",
        description=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    checkpoint = sub.add_parser(
        "checkpoint",
        help="Create or atomically refresh one rolling logical-session checkpoint.",
    )
    checkpoint.add_argument("--session-id", required=True)
    checkpoint.add_argument("--source-artifact", required=True)
    checkpoint.add_argument("--goal", required=True)
    checkpoint.add_argument("--in-scope", action="append", required=True)
    checkpoint.add_argument("--no-touch", action="append", required=True)
    checkpoint.add_argument(
        "--approval-state",
        choices=("approved", "pending", "not_required"),
        required=True,
    )
    checkpoint.add_argument("--approval-evidence", action="append")
    checkpoint.add_argument("--decision", action="append")
    checkpoint.add_argument("--completed", action="append")
    checkpoint.add_argument(
        "--verification",
        action="append",
        help="RESULT::COMMAND or RESULT::COMMAND::EVIDENCE; repeatable.",
    )
    checkpoint.add_argument("--blocker", action="append")
    checkpoint.add_argument("--failed-approach", action="append")
    checkpoint.add_argument("--risk", action="append")
    checkpoint.add_argument("--next-action", required=True)
    checkpoint.add_argument(
        "--continuation-mode",
        choices=("same_chat", "new_chat", "auto"),
        default="same_chat",
    )
    checkpoint.add_argument(
        "--status",
        choices=("in_progress", "blocked", "completed"),
        default="in_progress",
    )
    checkpoint.add_argument("--physical-chat-ref")
    checkpoint.add_argument("--project-root", default=".")

    validate = sub.add_parser(
        "validate",
        help="Validate checkpoint schema, location, and source-artifact containment.",
    )
    validate.add_argument("checkpoint")
    validate.add_argument("--project-root", default=None)

    resume = sub.add_parser(
        "resume-audit",
        help="Fail closed on project, source-artifact, config, lock, or Git drift.",
    )
    resume.add_argument("checkpoint")
    resume.add_argument("--project-root", default=".")

    handoff = sub.add_parser(
        "handoff",
        help="Validate current state and print a truthful continuation strategy.",
    )
    handoff.add_argument("checkpoint")
    handoff.add_argument("--project-root", default=".")
    handoff.add_argument("--mode", choices=("same_chat", "new_chat", "auto"))
    handoff.add_argument(
        "--open",
        action="store_true",
        help="Open only through a behaviorally verified adapter surface; fail closed otherwise.",
    )
    return parser


def run(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "checkpoint":
            return _checkpoint(args)
        if args.command == "validate":
            return _validate(args)
        if args.command == "resume-audit":
            return _resume_audit(args)
        return _handoff(args)
    except (SessionError, WorkspaceContractError, OSError, yaml.YAMLError) as exc:
        print(f"session: {exc}", file=sys.stderr)
        return 1
