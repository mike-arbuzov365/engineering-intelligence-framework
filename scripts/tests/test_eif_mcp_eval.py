#!/usr/bin/env python3
"""Check ten frozen expected answers via SDK calls; no model evaluation."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests"), str(ROOT / "scripts/tests/fixtures/eif_mcp")]


def main() -> int:
    if importlib.util.find_spec("mcp") is None:
        print("SKIPPED: mcp extra not installed")
        print("EIF-RESULT: passed=0 total=0")
        return 0
    from mcp import Client
    from engineering_intelligence_framework.eif_mcp.server import create_server
    from seed import seed
    from test_service_golden import capture
    expected = [pair.findtext("answer") for pair in ET.parse(ROOT / "docs/benchmarks/mcp-eval/questions.xml").getroot().findall("qa_pair")]

    async def answers(root):
        server = create_server(root)
        try:
            async with Client(server) as client:
                async def call(tool_name, **kwargs):
                    return (await client.call_tool(tool_name, kwargs)).structured_content

                values = []
                route = await call("eif_brief", task_kind="packet_run")
                progress = await call("eif_packet_status", packet="launch")
                values.append(route["data"]["route"]["skill"] + "|" + progress["data"]["next_session"])
                legacy = await call("eif_packet_status", packet="legacy")
                assert (await call("eif_packet_status", packet="launch"))["data"]["next_session"] == "SESSION-002"
                values.append(legacy["data"]["reason"])
                search = await call("eif_knowledge_search", query="cobalt")
                caps = await call("eif_capabilities")
                assert caps["data"]["instance"]["name"] == "synthetic-mcp"
                values.append(search["data"]["results"][0]["status"] + "|" + str(search["data"]["coverage"]["malformed"]))
                assert not any(row["name"] == "eif_commit" for row in caps["data"]["catalog"])
                values.append(caps["data"]["mode"] + "|" + caps["data"]["writes"])
                ingest = await call("eif_brief", task_kind="knowledge_ingest")
                outline = await call("eif_artifact_get", kind="skill", name=ingest["data"]["route"]["skill"])
                assert outline["data"]["path"] == ingest["data"]["route"]["path"]
                values.append(outline["data"]["path"])
                assert (await call("eif_session_validate", session_id="demo"))["data"]["verdict"] == "pass"
                audit = await call("eif_session_resume_audit", session_id="demo")
                assert audit["data"]["verdict"] == "pass"
                values.append(audit["data"]["next_action"])
                health = await call("eif_doctor")
                light = await call("eif_brief", task_kind="light")
                assert health["data"]["skipped_checks"] and light["data"]["route"] is None
                values.append(health["data"]["verdict"] + "|" + light["data"]["state"]["doctor"])
                outline = await call("eif_artifact_get", kind="playbook", name="execution-packet-execution")
                args = {"kind": "playbook", "name": "execution-packet-execution", "section": outline["data"]["sections"][0]["slug"], "max_chars": 64}
                page = await call("eif_artifact_get", **args)
                text = page["data"]["text"]
                while page.get("next_cursor"):
                    page = await call("eif_artifact_get", **args, cursor=page["next_cursor"])
                    text += page["data"]["text"]
                assert "only `completed` satisfies" in text
                values.append("completed")
                draft = await call("eif_knowledge_search", query="cobalt", status="draft")
                default = await call("eif_knowledge_search", query="cobalt")
                values.append(draft["data"]["results"][0]["status"] + "|" + default["data"]["results"][0]["status"])
                guard = await call("eif_delivery_check", action="package", scope="synthetic-final")
                values.append((caps["data"]["instance"]["profile"] or "none") + "|" + guard["status"])
                return values
        finally:
            server.close()

    with tempfile.TemporaryDirectory(prefix="eif-mcp-eval-") as tmp:
        root = seed(Path(tmp) / "project")
        for packet, legacy in (("launch", False), ("legacy", True)):
            folder = root / f"planning/packets/{packet}"
            (folder / "sessions").mkdir(parents=True)
            (folder / "04-ROADMAP.md").write_text("## Session 001\n## Session 002\n", encoding="utf-8")
            (folder / "sessions/SESSION-001-first.md").write_text("---\nid: SESSION-001\nstatus: " + ("prepared-awaiting-owner-approval" if legacy else "completed") + "\ndepends_on: []\n---\n", encoding="utf-8")
            (folder / "sessions/SESSION-002-next.md").write_text("---\nid: SESSION-002\nstatus: prepared\ndepends_on: [SESSION-001]\n---\n", encoding="utf-8")
        fact = (root / "knowledge/synthetic.md").read_text(encoding="utf-8")
        (root / "knowledge/draft.md").write_text(fact.replace("status: validated", "status: draft"), encoding="utf-8")
        (root / "knowledge/malformed.md").write_text("---\n[broken: yaml\n---\n", encoding="utf-8")
        assert capture(["session", "checkpoint", "--project-root", str(root), "--source-artifact", "planning/packets/demo/sessions/SESSION-001-demo.md", "--session-id", "demo", "--goal", "Synthetic reader verification", "--in-scope", "planning", "--no-touch", "product", "--next-action", "Inspect the packet", "--approval-state", "not_required"], root)["rc"] == 0
        actual = asyncio.run(answers(root))
    matches = [a == b for a, b in zip(expected, actual)]
    for number, (wanted, value) in enumerate(zip(expected, actual), 1):
        print(f"{'PASS' if wanted == value else 'FAIL'} expected answer {number}: {value}")
    print("Model evaluation: NOT RUN (O-6 = 0)")
    print(f"EIF-RESULT: passed={sum(matches)} total={len(expected)}")
    return 0 if len(expected) == len(actual) == 10 and all(matches) else 1


if __name__ == "__main__":
    raise SystemExit(main())
