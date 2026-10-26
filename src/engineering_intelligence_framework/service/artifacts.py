"""Section access to pinned, named policy artifacts; cursors stay in memory."""
from __future__ import annotations

import re
import time
import uuid

from .instance import Instance, Result, ServiceError


def sections(text: str) -> list[dict]:
    headings, offset, fenced = [], 0, False
    counts: dict[str, int] = {}
    for line in text.splitlines(keepends=True):
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line.rstrip()) if not fenced else None
        if match:
            title = match.group(2)
            slug = re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", title.lower())).strip("-")
            ordinal = counts.get(slug, 0)
            counts[slug] = ordinal + 1
            headings.append({"slug": slug + (f"-{ordinal}" if ordinal else ""), "title": title, "start": offset})
        offset += len(line)
    for i, heading in enumerate(headings):
        heading["end"] = headings[i + 1]["start"] if i + 1 < len(headings) else len(text)
        heading["bytes"] = len(text[heading["start"]:heading["end"]].encode("utf-8"))
    return headings


def artifact_get(instance: Instance, kind: str, name: str, section: str | None = None, max_chars: int = 4000, cursor: str | None = None) -> Result:
    if kind not in {"skill", "playbook", "template", "rule"} or type(max_chars) is not int or not 1 <= max_chars <= 12000:
        raise ServiceError("validation_failed", "Invalid artifact kind or page size.")
    if section is not None and (not isinstance(section, str) or not re.fullmatch(r"[\w-]{1,200}", section)):
        raise ServiceError("validation_failed", "Section must be a heading slug.")
    item, text = instance.artifact(kind, name)
    headings = sections(text)
    if section is None:
        if cursor:
            raise ServiceError("validation_failed", "A cursor requires a section.")
        return {"status": "ok", "data": {"path": item["relative"], "sections": [{k: h[k] for k in ("slug", "title", "bytes")} for h in headings]}}
    match = next((h for h in headings if h["slug"] == section), None)
    if not match:
        raise ServiceError("not_found", "The heading slug is not present in this artifact.")
    now = time.monotonic()
    instance.cursors = {k: v for k, v in instance.cursors.items() if v["expires"] > now}
    offset = 0
    key = (kind, name, section, item["sha256"])
    if cursor:
        saved = instance.cursors.get(cursor)
        if saved is None or saved["key"] != key:
            raise ServiceError("validation_failed", "Cursor is expired or belongs to another artifact section.")
        offset = saved["offset"]
    body = text[match["start"]:match["end"]]
    page = body[offset:offset + max_chars]
    truncated = offset + len(page) < len(body)
    result: Result = {"status": "truncated" if truncated else "ok", "data": {"path": item["relative"], "section": section, "text": page}, "truncated": truncated}
    if truncated:
        if len(instance.cursors) >= 256:
            instance.cursors.pop(next(iter(instance.cursors)))
        next_cursor = uuid.uuid4().hex
        instance.cursors[next_cursor] = {"key": key, "offset": offset + len(page), "expires": now + 600}
        result["next_cursor"] = next_cursor
    return result
