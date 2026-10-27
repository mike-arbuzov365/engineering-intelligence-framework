"""Structured adapters to existing EIF implementations, with bounded sources."""
from __future__ import annotations

import importlib.metadata as metadata
import json
import re
from pathlib import Path
from typing import Any

from .._impl import eif_render, eif_search_knowledge, eif_verify_runtime
from ..commands import delivery, doctor, init_cmd, session
from ..resources import framework_root
from ..workspace_materialization import verify_workspace_materialization
from .artifacts import artifact_get
from .instance import Instance, Result, ServiceError, identifier
from .packets import packet_status


def package_version() -> str:
    try:
        return metadata.version(init_cmd.DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return "0.0.0+unknown"


def drift(instance: Instance) -> str:
    if (instance.lock.get("framework") or {}).get("source_type") != "installed-package":
        return "unknown"
    package = instance.lock.get("package") or {}
    if not package.get("version") or not package.get("resource_manifest_digest") or package_version() == "0.0.0+unknown":
        return "unknown"
    with framework_root() as root:
        return "mismatch" if doctor._check_installed_package_consistency(instance.root, root) else "match"


def capabilities(instance: Instance, *, sdk_version: str = "unavailable", elicitation: bool = False, catalog: list[dict] | None = None) -> Result:
    state = drift(instance)
    return {"status": {"match": "ok", "mismatch": "stale", "unknown": "unknown"}[state], "data": {
        "versions": {"server": package_version(), "eifctl": package_version(), "sdk": sdk_version},
        "instance": {"id": instance.project["id"], "name": instance.project["name"], "adapter": instance.project["adapter"], "locale": instance.project["locale"], "profile": (instance.workspace.get("workspace") or {}).get("profile"), "config_sha256": instance.project["config_sha256"][:12], "lock_sha256": instance.project["lock_sha256"][:12]},
        "drift": state, "mode": "reader", "elicitation": elicitation,
        "catalog": catalog or [], "writes": "deferred-to-EIF-022b",
        "limits": {"response_bytes": 24576, "brief_bytes": 4096, "artifact_chars": 12000, "search_top": 20, "deadline_seconds": 15, "cursor_ttl_seconds": 600},
    }}


def _doctor_preflight(instance: Instance) -> None:
    instance.manifest()
    for relative in (".eif/runtime", ".eif/workspace-runtime"):
        if instance.safe(relative).is_dir():
            instance.guard_tree(relative)
    entry = (instance.lock.get("adapter") or {}).get("entrypoint", "CLAUDE.md")
    # Core marker checks require these instance-local adapter files. They
    # cannot be arbitrary filenames supplied through a forged lock.
    if entry not in {"CLAUDE.md", "AGENTS.md", "AGENTS.override.md", ".hermes.md", ".cursor/rules/eif/governance.mdc"}:
        raise ServiceError("source_unavailable", "The adapter entrypoint is outside the bounded doctor surface.")
    for relative in (entry, ".gitignore", ".gitattributes"):
        instance.safe(relative)
    index = instance.lock.get("knowledge_index") or {}
    if index.get("path"):
        instance.safe(index["path"])


def doctor_report(instance: Instance, detail: bool = False) -> Result:
    _doctor_preflight(instance)
    with framework_root() as root:
        collected = eif_verify_runtime.collect_report(root, instance.root, probes=False, contained=True)
        sections = collected["report"].sections
        sections.append(("installed package consistency", doctor._check_installed_package_consistency(instance.root, root)))
    sections.append(("workspace materialization", verify_workspace_materialization(instance.root)))
    # Legacy validator diagnostics may quote values from invalid files. The
    # transport exposes check names and counts; exact local diagnostics stay
    # in the direct CLI, where the owner selected that output deliberately.
    checks = [{"name": name, "problems": ["Check failed; inspect the direct CLI diagnostic." for _ in problems[:5]], "problem_count": len(problems)} for name, problems in sections]
    failed = [row["name"] for row in checks if row["problem_count"]]
    # These checks may inspect ancestors, user-level agent files or execute
    # provider commands. An MCP reader must disclose their omission.
    skipped = ["ancestor size budget", "active source resolution", "agent skill discovery", "optional integration probes"]
    return {"status": "partial", "data": {"verdict": "fail" if failed else "partial", "failed_checks": failed, "checks": checks if detail else [row for row in checks if row["problem_count"]], "skipped_checks": skipped}, "next_action": "Run eifctl doctor --instance-path . for full local coverage."}


def _checkpoint_path(instance: Instance, session_id: str) -> Path:
    identifier(session_id)
    return instance.safe(f".session-context/{session_id}.md")


def _session_sources(instance: Instance, path: Path) -> None:
    instance.read(path.relative_to(instance.root))
    try:
        data = session._parse_checkpoint(path)
    except session.SessionError:
        return
    source = data.get("source_artifact") or {}
    if isinstance(source, dict) and isinstance(source.get("path"), str):
        instance.safe(source["path"])


def session_validate(instance: Instance, session_id: str) -> Result:
    path = _checkpoint_path(instance, session_id)
    if not path.is_file():
        raise ServiceError("not_found", "The session identifier is not present.")
    _session_sources(instance, path)
    data, errors = session.validate_checkpoint(path, project_root=instance.root)
    safe_errors = [error.split(":", 1)[0][:80] + ": validation failed" for error in errors]
    return {"status": "partial" if errors else "ok", "data": {"verdict": "fail" if errors else "pass", "errors": safe_errors, "session_id": session_id}}


def session_resume_audit(instance: Instance, session_id: str) -> Result:
    path = _checkpoint_path(instance, session_id)
    if not path.is_file():
        raise ServiceError("not_found", "The session identifier is not present.")
    _session_sources(instance, path)
    # Reject an inherited parent repository and any external Git indirection
    # before the legacy fixed-command snapshot can inspect its metadata.
    git_dir = instance.root / ".git"
    if not git_dir.is_dir() or git_dir.resolve() != git_dir or git_dir.is_symlink():
        raise ServiceError("source_unavailable", "A self-contained local Git repository is required for resume audit.")
    # Containment of Git's own config is checked by path metadata only; its
    # contents are accessed through a fixed Git command, never a file reader.
    config = git_dir / "config"
    if not config.resolve().is_relative_to(git_dir):
        raise ServiceError("source_unavailable", "Git configuration leaves the selected instance.")
    included = session._run_git(instance.root, ["config", "--no-includes", "--local", "--get-regexp", r"^include(if\..*)?\.path$"], bounded=True)
    if included.returncode != 1:
        raise ServiceError("source_unavailable", "Git includes or unreadable Git configuration require a direct local audit.")
    data, mismatches = session.audit_checkpoint(path, instance.root, bound_project=True)
    return {"status": "partial" if mismatches else "ok", "data": {"verdict": "fail" if mismatches else "pass", "mismatches": [{"category": key, "expected": str(expected)[:240], "actual": "checkpoint validation failed" if key == "schema" else str(actual)[:240]} for key, expected, actual in mismatches], "next_action": (data or {}).get("next_action")}}


def knowledge_search(instance: Instance, query: str, type_filter: str | None = None, top: int = 5, status: str | None = None) -> Result:
    if not isinstance(query, str) or not 1 <= len(query) <= 2000 or type(top) is not int or not 1 <= top <= 20:
        raise ServiceError("validation_failed", "Provide a query and a result count from 1 to 20.")
    relative = str((instance.config.get("knowledge") or {}).get("root", "knowledge"))
    folder = instance.safe(relative)
    if not folder.is_dir():
        raise ServiceError("source_unavailable", "The configured knowledge source is unavailable.")
    instance.guard_tree(relative)
    with framework_root() as root:
        found = eif_search_knowledge.search(folder, query, type_filter, top, {status} if status else {"validated"}, root, include_coverage=True)
    malformed, invalid, skipped = found["malformed"], found["schema_invalid"], found["skipped_by_status"]
    rows = [{k: row.get(k) for k in ("path", "type", "status", "score", "stale")} | {"excerpt": str(row.get("excerpt", ""))[:240]} for row in found["results"]]
    for row in rows:
        row["path"] = (Path(relative) / row["path"]).as_posix()
    coverage = {"indexed": found["indexed"], "malformed": len(malformed), "schema_invalid": len(invalid), "skipped_by_status": len(skipped), "malformed_paths": malformed[:20], "schema_invalid_paths": [row["path"] for row in invalid[:20]], "skipped_paths": [row["path"] for row in skipped[:20]]}
    return {"status": "partial" if malformed or invalid else "ok", "data": {"results": rows, "coverage": coverage}}


def delivery_check(instance: Instance, action: str, scope: str) -> Result:
    if (instance.workspace.get("workspace") or {}).get("profile") != "graphic-design":
        return {"status": "unavailable", "data": {"reason": "The active profile is not graphic-design."}}
    instance.manifest()
    instance.guard_tree(".eif/workspace-runtime")
    relative = delivery.APPROVAL_PATH.as_posix()
    if instance.safe(relative).exists():
        approval = instance.mapping(relative)
        ref = (approval.get("decision") or {}).get("evidence_ref")
        if isinstance(ref, str) and not ref.startswith("https://"):
            instance.safe(ref)
    try:
        delivery.check_delivery(instance.root, action=action, scope=scope)
    except (delivery.DeliveryGuardError, ValueError):
        return {"status": "partial", "data": {"verdict": "blocked", "reason": "Approval or workspace validation blocked the delivery; inspect eifctl delivery check locally.", "enforcement": "machine", "external_shell_enforcement": "instruction_only"}}
    return {"status": "ok", "data": {"verdict": "pass", "enforcement": "machine", "external_shell_enforcement": "instruction_only"}}


def brief(instance: Instance, task_kind: str) -> Result:
    kinds = json.loads(Path(__file__).with_name("task_kinds.json").read_text(encoding="utf-8"))
    if task_kind not in kinds:
        raise ServiceError("validation_failed", "Use a declared task kind.")
    name = kinds[task_kind]
    route, reads = None, []
    if name:
        item, text = instance.artifact("skill", name)
        match = re.match(r"\A---\r?\n(.*?)\r?\n---", text, re.S)
        description = ""
        if match:
            import yaml
            description = str((yaml.safe_load(match.group(1)) or {}).get("description", ""))[:200]
        route = {"skill": name, "path": item["relative"], "bytes": len(text.encode("utf-8")), "description": description}
        for target in re.findall(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)", text):
            if "://" in target:
                continue
            resolved = (instance.root / item["relative"]).parent.joinpath(target).resolve()
            if not resolved.is_relative_to(instance.root):
                raise ServiceError("source_unavailable", "A skill reference leaves the instance.")
            relative = resolved.relative_to(instance.root).as_posix()
            entry = next((x for x in instance.manifest() if x["relative"] == relative), None)
            if entry:
                reads.append({"path": relative, "bytes": len(instance.read(relative))})
    health = doctor_report(instance)
    checkpoints = instance.safe(".session-context")
    count = 0
    if checkpoints.is_dir():
        for path in checkpoints.glob("*.md"):
            _session_sources(instance, instance.safe(path.relative_to(instance.root)))
            try:
                count += session._parse_checkpoint(path).get("status") != "completed"
            except session.SessionError:
                pass
    active = []
    if instance.safe(instance.packets_root).is_dir():
        for packet in packet_status(instance)["data"]["packets"]:
            progress = packet_status(instance, packet)
            if any(row["status"] == "in_progress" for row in progress["data"]["sessions"]):
                active.append(packet)
    gates = ["eif_doctor"] + (["eif_session_validate", "eif_session_resume_audit", "eif_packet_status"] if task_kind.startswith("packet_") else [])
    return {"status": health["status"], "data": {"task_kind": task_kind, "route": route, "read_list": reads, "gates": gates, "state": {"doctor": health["data"]["verdict"], "failed_checks": health["data"]["failed_checks"], "open_checkpoints": count, "active_packet": active[0] if len(active) == 1 else None, "active_packet_ambiguous": len(active) > 1}}}


# Phase-two core primitives are public, but never registered as MCP tools in
# reader mode. Their CLI behavior remains characterized by the golden suite.
session_checkpoint_plan = session.checkpoint_plan
session_checkpoint_apply = session.checkpoint_apply
render_preview = eif_render.render_preview
render_apply = eif_render.render_apply
