"""Read explicit session progress; never infer completion from Git or prose."""
from __future__ import annotations

import re

import yaml

from .instance import Instance, Result, ServiceError, identifier

STATUSES = {"prepared", "in_progress", "completed", "blocked", "deferred"}


def frontmatter(instance: Instance, path: str) -> dict:
    try:
        text = instance.read(path).decode("utf-8")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        data = yaml.safe_load(match.group(1)) if match else {}
        return data if isinstance(data, dict) else {}
    except (UnicodeError, yaml.YAMLError):
        raise ServiceError("validation_failed", "Artifact frontmatter is invalid.") from None


def packet_status(instance: Instance, packet: str | None = None) -> Result:
    root = instance.safe(instance.packets_root)
    if not root.is_dir():
        raise ServiceError("source_unavailable", "The packet directory is unavailable.")
    if packet is None:
        directories = []
        for path in sorted(root.iterdir()):
            instance.safe(path.relative_to(instance.root))
            if path.is_dir():
                directories.append(path.name)
        return {"status": "ok", "data": {"packets": directories}}
    identifier(packet)
    folder = instance.safe(f"{instance.packets_root}/{packet}")
    if not folder.is_dir():
        raise ServiceError("not_found", "The packet identifier is not present.")
    instance.guard_tree(f"{instance.packets_root}/{packet}")
    sessions = []
    for file in sorted((folder / "sessions").glob("SESSION-*.md")):
        data = frontmatter(instance, file.relative_to(instance.root).as_posix())
        raw_status = data.get("status")
        sid = str(data.get("id") or file.stem.split("-", 2)[0] + "-" + file.stem.split("-", 2)[1])
        dependencies = data.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(isinstance(x, str) for x in dependencies):
            dependencies = ["invalid-dependency"]
        checkpoint = data.get("session_context")
        has_checkpoint = bool(checkpoint and instance.safe(str(checkpoint)).is_file())
        sessions.append({"id": sid, "status": raw_status if raw_status in STATUSES else "legacy", "raw_status": raw_status, "depends_on": dependencies, "checkpoint": has_checkpoint})
    roadmaps = sorted(folder.glob("04-ROADMAP*.md"))
    order = []
    if len(roadmaps) == 1:
        text = instance.read(roadmaps[0].relative_to(instance.root)).decode("utf-8")
        order = list(dict.fromkeys(f"SESSION-{int(n):03d}" for n in re.findall(r"(?im)^##\s+Session\s+(\d+)\b", text)))
        if not order:
            order = list(dict.fromkeys(re.findall(r"sessions/(SESSION-\d+)-", text)))
    by_id = {s["id"]: s for s in sessions}
    reason = None
    if len(by_id) != len(sessions) or not order or set(order) != set(by_id):
        reason = "missing_or_ambiguous_session_order"
    elif any(s["status"] == "legacy" for s in sessions):
        reason = "legacy_or_missing_status"
    visiting, visited = set(), set()

    def visit(sid: str) -> bool:
        if sid in visiting or sid not in by_id:
            return False
        if sid in visited:
            return True
        visiting.add(sid)
        if not all(visit(dep) for dep in by_id[sid]["depends_on"]):
            return False
        visiting.remove(sid)
        visited.add(sid)
        return True

    if not all(visit(sid) for sid in by_id):
        reason = "invalid_or_cyclic_dependencies"
    next_session = None
    if reason is None:
        next_session = next((sid for sid in order if by_id[sid]["status"] in {"prepared", "in_progress"} and all(by_id[d]["status"] == "completed" for d in by_id[sid]["depends_on"])), None)
        if next_session is None:
            reason = "completed_or_no_ready_session"
    closeouts = sorted(folder.glob("07-CLOSEOUT*.md"))
    closeout = frontmatter(instance, closeouts[0].relative_to(instance.root).as_posix()).get("status", "unknown") if len(closeouts) == 1 else "unknown"
    return {"status": "partial" if reason and reason != "completed_or_no_ready_session" else "ok", "data": {"packet": packet, "sessions": [by_id[sid] for sid in order if sid in by_id] if order else sessions, "closeout": str(closeout), "next_session": next_session, "reason": reason}}
