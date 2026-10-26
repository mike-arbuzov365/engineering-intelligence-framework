#!/usr/bin/env python3
"""All reader tools through the actual SDK, plus limits and failure paths."""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import importlib.util
import io
import importlib.metadata
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests"), str(ROOT / "scripts/tests/fixtures/eif_mcp")]


def main() -> int:
    if importlib.util.find_spec("mcp") is None:
        print("SKIPPED: mcp extra not installed")
        print("EIF-RESULT: passed=0 total=0")
        return 0
    from mcp import Client
    from engineering_intelligence_framework.eif_mcp.server import CATALOG, compact, create_server, wire_bytes
    from engineering_intelligence_framework.service import operations
    from engineering_intelligence_framework import cli
    from seed import seed

    checks = []

    def check(name, value):
        checks.append(bool(value))
        print(f"{'PASS' if value else 'FAIL'} {name}")

    async def run(root):
        server = create_server(root)
        before = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
        try:
            async with Client(server) as client:
                listed = await client.list_tools()
                serialized = compact(listed.model_dump(by_alias=True, exclude_none=True))
                check("catalog has nine tools", len(listed.tools) == 9)
                check("catalog budget", len(serialized.encode()) <= 6144)
                print(f"tools/list bytes={len(serialized.encode())}")
                for tool in listed.tools:
                    annotations = tool.annotations.model_dump(by_alias=True, exclude_none=True)
                    check(tool.name + " strict read schema", tool.input_schema.get("additionalProperties") is False and annotations == {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})
                requests = [
                    ("eif_capabilities", {}), ("eif_brief", {"task_kind": "packet_run"}),
                    ("eif_artifact_get", {"kind": "skill", "name": "run-execution-packet"}),
                    ("eif_knowledge_search", {"query": "cobalt"}), ("eif_packet_status", {"packet": "demo"}),
                    ("eif_doctor", {"detail": True}), ("eif_session_validate", {"session_id": "demo"}),
                    ("eif_session_resume_audit", {"session_id": "demo"}),
                    ("eif_delivery_check", {"action": "package", "scope": "synthetic"}),
                ]
                results = {}
                for name, args in requests:
                    value = await client.call_tool(name, args)
                    data = value.structured_content
                    results[name] = data
                    check(name + " structured roundtrip", isinstance(data, dict) and json.loads(value.content[0].text) == data and len(data["request_id"]) == 32 and not value.is_error)
                    check(name + " byte limit", wire_bytes(value) <= (4096 if name == "eif_brief" else 24576))
                check("pinned packet route", results["eif_brief"]["data"].get("route", {}).get("skill") == "run-execution-packet")
                check("search result grounded", len(results["eif_knowledge_search"]["data"]["results"]) == 1)
                check("dependency-ready session", results["eif_packet_status"]["data"]["next_session"] == "SESSION-001")
                check("session validation pass", results["eif_session_validate"]["data"]["verdict"] == "pass")
                check("resume audit pass", results["eif_session_resume_audit"]["data"]["verdict"] == "pass")
                check("doctor partial coverage", results["eif_doctor"]["status"] == "partial")
                check("design guard unavailable for core", results["eif_delivery_check"]["status"] == "unavailable")
                outline = results["eif_artifact_get"]["data"]["sections"]
                page = await client.call_tool("eif_artifact_get", {"kind": "skill", "name": "run-execution-packet", "section": outline[0]["slug"], "max_chars": 8})
                check("explicit pagination", page.structured_content["status"] == "truncated" and bool(page.structured_content.get("next_cursor")))
                for name, args in [("eif_capabilities", {"approved": True}), ("eif_artifact_get", {"kind": "skill", "name": "../other"}), ("eif_session_validate", {"session_id": "/other"}), ("eif_knowledge_search", {"query": "query", "top": 21})]:
                    error = await client.call_tool(name, args)
                    check(name + " invalid input typed", error.is_error and error.structured_content["error"]["code"] == "validation_failed")
                unknown = await client.call_tool("unregistered", {})
                check("unknown tool typed", unknown.structured_content["error"]["code"] == "not_found")
                missing = await client.call_tool("eif_session_validate", {"session_id": "missing"})
                check("missing object typed", missing.structured_content["error"]["code"] == "not_found")
                saved = importlib.metadata.version
                importlib.metadata.version = lambda name: "99.0.0" if name == "engineering-intelligence-framework" else saved(name)
                try:
                    stale = await client.call_tool("eif_capabilities", {})
                    check("version mismatch explicit", stale.structured_content["status"] == "stale")
                finally:
                    importlib.metadata.version = saved
                saved_search = operations.knowledge_search
                operations.knowledge_search = lambda *args, **kw: {"status": "ok", "data": {"results": ["\\\"😀" * 20000]}}
                try:
                    huge = await client.call_tool("eif_knowledge_search", {"query": "synthetic"})
                    check("oversized Unicode result explicit", huge.structured_content["status"] == "truncated" and huge.structured_content["error"]["code"] == "result_truncated" and wire_bytes(huge) <= 24576)
                finally:
                    operations.knowledge_search = saved_search
        finally:
            server.close()
        after = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
        check("reader writes no instance files", before == after)
        slow = create_server(root, deadline=0.03)
        lock = threading.Lock()
        active = maximum = 0

        def sleeping(*args):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.15)
            with lock:
                active -= 1
            return {"status": "ok", "data": {}}

        slow._dispatch = sleeping
        try:
            values = await asyncio.gather(slow.call_tool("eif_capabilities", {}), slow.call_tool("eif_capabilities", {}))
            check("read deadlines typed", all(v.structured_content["error"]["code"] == "source_unavailable" for v in values))
            await asyncio.sleep(0.2)
            check("worker remains serialized after timeout", maximum == 1)
        finally:
            slow.close()

    with tempfile.TemporaryDirectory(prefix="eif-mcp-memory-") as tmp:
        root = seed(Path(tmp) / "project")
        asyncio.run(run(root))
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            rc = cli.main(["mcp", "serve"])
        check("no implicit cwd root", rc == 3 and not out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            rc = cli.main(["mcp", "serve", "--instance-path", str(Path(tmp))])
        check("non-instance startup rejected", rc == 3 and not out.getvalue())
    print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
