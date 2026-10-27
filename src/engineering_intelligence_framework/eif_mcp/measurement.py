"""Deterministic SDK response-byte sampling, without model calls."""
from __future__ import annotations

from pathlib import Path

from mcp import Client

from .server import compact, create_server, wire_bytes

SCENARIOS = {
    "knowledge_search": {"name": "knowledge-search", "sections": ["recording-the-result", "how"]},
    "packet_plan": {"name": "execution-packet-planning", "sections": ["workflow", "when-a-packet-is-needed"]},
    "packet_run": {"name": "execution-packet-execution", "sections": ["step-1---enter-via-the-start-file", "step-2---execute-sessions-in-roadmap-order"]},
}


async def measure_responses(root: Path) -> dict:
    server = create_server(root)
    try:
        async with Client(server) as client:
            listed = await client.list_tools()
            scenarios = {}
            for task in ("light", *SCENARIOS):
                brief = await client.call_tool("eif_brief", {"task_kind": task})
                if brief.is_error or brief.structured_content.get("truncated"):
                    raise ValueError("brief did not provide the scenario metadata")
                sections = []
                outline_bytes = 0
                if task in SCENARIOS:
                    spec = SCENARIOS[task]
                    outline = await client.call_tool("eif_artifact_get", {"kind": "playbook", "name": spec["name"]})
                    if outline.is_error or not outline.structured_content.get("data", {}).get("sections"):
                        raise ValueError("artifact outline is unavailable")
                    outline_bytes = wire_bytes(outline)
                    available = {row["slug"] for row in outline.structured_content["data"]["sections"]}
                    for slug in spec["sections"]:
                        if slug not in available:
                            raise ValueError("frozen scenario section drift")
                        arguments = {"kind": "playbook", "name": spec["name"], "section": slug}
                        page = await client.call_tool("eif_artifact_get", arguments)
                        pages, count, chars = 0, 0, 0
                        while True:
                            value = page.structured_content
                            if page.is_error or "text" not in value["data"]:
                                raise ValueError("section is unavailable in the pinned source")
                            pages += 1
                            count += wire_bytes(page)
                            chars += len(value["data"]["text"])
                            if not value.get("next_cursor"):
                                break
                            page = await client.call_tool("eif_artifact_get", {**arguments, "cursor": value["next_cursor"]})
                        sections.append({"kind": "playbook", "name": spec["name"], "section": slug, "pages": pages, "response_bytes": count, "text_chars": chars})
                scenarios[task] = {"brief_bytes": wire_bytes(brief), "outline_bytes": outline_bytes, "section_reads": sections, "response_bytes": wire_bytes(brief) + outline_bytes + sum(section["response_bytes"] for section in sections)}
            return {"tools_list_bytes": len(compact(listed.model_dump(by_alias=True, exclude_none=True)).encode("utf-8")), "scenarios": scenarios}
    finally:
        server.close()
