"""Read explicit session progress; never infer completion from Git or prose."""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path
import re
from typing import Iterator

import yaml

from .instance import Instance, Result, ServiceError, identifier

STATUSES = {"prepared", "in_progress", "completed", "blocked", "deferred"}
MAX_PACKET_ENTRIES = 5000
MAX_PACKET_SOURCE_BYTES = 20_971_520


def _entries(directory: Path, budget: list[int]) -> Iterator[Path]:
    """Bound directory enumeration before sorting or opening selected sources."""
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                budget[0] -= 1
                if budget[0] < 0:
                    raise ServiceError("source_unavailable", "Packet directory exceeds reader limits.")
                yield Path(entry.path)
    except OSError:
        raise ServiceError("source_unavailable", "The packet directory is unavailable.") from None


def _status_sources(instance: Instance, folder: Path) -> dict[str, list[Path]]:
    """Only direct status documents participate in progress, never attachments.

    Embedded checkouts/assets can be large or contain prohibited filenames.
    They are not read. Every selected path (including the sessions directory)
    still passes containment checks, with the existing aggregate byte budget
    and Instance.read's per-file limit. Enumeration is bounded as well.
    """
    sources: dict[str, list[Path]] = {"sessions": [], "roadmaps": [], "closeouts": []}
    budget = [MAX_PACKET_ENTRIES]
    total = 0

    def add(group: str, path: Path) -> None:
        nonlocal total
        path = instance.safe(path.relative_to(instance.root))
        try:
            if not path.is_file():
                raise ServiceError("source_unavailable", "A packet status source is not a regular file.")
            total += path.stat().st_size
        except OSError:
            raise ServiceError("source_unavailable", "A packet status source is unavailable.") from None
        if total > MAX_PACKET_SOURCE_BYTES:
            raise ServiceError("source_unavailable", "Packet status sources exceed reader limits.")
        sources[group].append(path)

    for path in _entries(folder, budget):
        if fnmatch.fnmatch(path.name, "04-ROADMAP*.md"):
            add("roadmaps", path)
        elif fnmatch.fnmatch(path.name, "07-CLOSEOUT*.md"):
            add("closeouts", path)
    sessions = instance.safe((folder / "sessions").relative_to(instance.root))
    if sessions.exists():
        if not sessions.is_dir():
            raise ServiceError("source_unavailable", "The packet sessions source is not a directory.")
        for path in _entries(sessions, budget):
            if fnmatch.fnmatch(path.name, "SESSION-*.md"):
                add("sessions", path)
    return {group: sorted(paths) for group, paths in sources.items()}


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
        for path in sorted(_entries(root, [MAX_PACKET_ENTRIES])):
            instance.safe(path.relative_to(instance.root))
            if path.is_dir():
                directories.append(path.name)
        return {"status": "ok", "data": {"packets": directories}}
    identifier(packet)
    folder = instance.safe(f"{instance.packets_root}/{packet}")
    if not folder.is_dir():
        raise ServiceError("not_found", "The packet identifier is not present.")
    sources = _status_sources(instance, folder)
    sessions = []
    for file in sources["sessions"]:
        data = frontmatter(instance, file.relative_to(instance.root).as_posix())
        raw_status = data.get("status")
        sid = str(data.get("id") or file.stem.split("-", 2)[0] + "-" + file.stem.split("-", 2)[1])
        dependencies = data.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(isinstance(x, str) for x in dependencies):
            dependencies = ["invalid-dependency"]
        checkpoint = data.get("session_context")
        has_checkpoint = bool(checkpoint and instance.safe(str(checkpoint)).is_file())
        sessions.append({"id": sid, "status": raw_status if isinstance(raw_status, str) and raw_status in STATUSES else "legacy", "raw_status": raw_status, "depends_on": dependencies, "checkpoint": has_checkpoint})
    roadmaps = sources["roadmaps"]
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
    closeouts = sources["closeouts"]
    closeout = frontmatter(instance, closeouts[0].relative_to(instance.root).as_posix()).get("status", "unknown") if len(closeouts) == 1 else "unknown"
    # Preserve every observed launch file even when roadmap coverage is
    # incomplete or IDs are duplicated. Partial coverage cannot erase rows.
    ordered = sorted(sessions, key=lambda row: order.index(row["id"]) if row["id"] in order else len(order))
    return {"status": "partial" if reason and reason != "completed_or_no_ready_session" else "ok", "data": {"packet": packet, "sessions": ordered, "closeout": str(closeout), "next_session": next_session, "reason": reason}}
