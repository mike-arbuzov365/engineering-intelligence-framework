#!/usr/bin/env python3
"""Packet readers inspect bounded status sources, not embedded workspaces."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests"), str(ROOT / "scripts/tests/fixtures/eif_mcp")]

from engineering_intelligence_framework.service import Instance, ServiceError
from engineering_intelligence_framework.service.packets import packet_status
from seed import seed

LAB = Path(tempfile.mkdtemp(prefix="eif-packet-sources-"))


class PacketSourceTests(unittest.TestCase):
    def setUp(self):
        self.root = seed(LAB / self._testMethodName)
        self.instance = Instance(self.root)
        self.packet = self.root / "planning/packets/demo"

    def add_workspace(self):
        nested = self.packet / "evidence/workspace"
        nested.mkdir(parents=True)
        # Exceeds the old recursive byte budget without allocating a large blob.
        with (nested / "asset.bin").open("wb") as stream:
            stream.truncate(20_971_521)
        return nested

    def make_link(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError:
            if os.name != "nt" or not directory:
                raise
            result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                                     "New-Item -ItemType Junction -Path $env:EIF_TEST_LINK -Target $env:EIF_TEST_TARGET | Out-Null"],
                                    env=dict(os.environ, EIF_TEST_LINK=str(link), EIF_TEST_TARGET=str(target)), capture_output=True)
            self.assertEqual(result.returncode, 0)

    def test_large_unrelated_workspace_does_not_change_status(self):
        before = packet_status(self.instance, "demo")
        self.add_workspace()
        self.assertEqual(packet_status(self.instance, "demo"), before)

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "optional mcp extra not installed")
    def test_real_stdio_brief_with_embedded_workspace(self):
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
        self.add_workspace()
        async def run():
            env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
            params = StdioServerParameters(command=sys.executable, args=["-B", "-m", "engineering_intelligence_framework.cli", "mcp", "serve", "--instance-path", str(self.root)], env=env)
            async with Client(params, read_timeout_seconds=30) as client:
                brief = await client.call_tool("eif_brief", {"task_kind": "packet_run"})
                self.assertFalse(brief.is_error, brief.structured_content)
                self.assertEqual(brief.structured_content["data"]["route"]["skill"], "run-execution-packet")
                progress = await client.call_tool("eif_packet_status", {"packet": "demo"})
                self.assertFalse(progress.is_error, progress.structured_content)
                self.assertEqual(progress.structured_content["data"]["next_session"], "SESSION-001")
        asyncio.run(run())

    def test_external_sessions_directory_refused_before_enumeration(self):
        (self.packet / "sessions").rename(self.packet / "original-sessions")
        outside = LAB / (self._testMethodName + "-external")
        outside.mkdir()
        self.make_link(self.packet / "sessions", outside, directory=True)
        with self.assertRaises(ServiceError) as caught:
            packet_status(self.instance, "demo")
        self.assertEqual(caught.exception.code, "source_unavailable")

    def test_external_roadmap_source_refused(self):
        roadmap = self.packet / "04-ROADMAP-demo.md"
        roadmap.rename(self.packet / "saved-roadmap.md")
        outside = LAB / (self._testMethodName + ".md")
        if os.name == "nt":
            outside.mkdir()
            self.make_link(roadmap, outside, directory=True)
        else:
            outside.write_text("outside sentinel", encoding="utf-8")
            self.make_link(roadmap, outside)
        with self.assertRaises(ServiceError) as caught:
            packet_status(self.instance, "demo")
        self.assertEqual(caught.exception.code, "source_unavailable")

    def test_unrelated_prohibited_names_are_not_status_sources(self):
        before = packet_status(self.instance, "demo")
        nested = self.packet / "evidence/workspace"
        (nested / ".git").mkdir(parents=True)
        (nested / ".git/config").write_text("unrelated nested checkout", encoding="utf-8")
        (nested / ".env").write_text("SYNTHETIC_ONLY=not-a-credential", encoding="utf-8")
        self.assertEqual(packet_status(self.instance, "demo"), before)

    def test_relevant_file_limit_is_preserved(self):
        source = self.packet / "sessions/SESSION-001-demo.md"
        with source.open("wb") as stream:
            stream.truncate(2_097_153)
        with self.assertRaises(ServiceError) as caught:
            packet_status(self.instance, "demo")
        self.assertEqual(caught.exception.code, "source_unavailable")

    def test_relevant_aggregate_limit_is_preserved(self):
        for index in range(2, 13):
            with (self.packet / f"sessions/SESSION-{index:03}-large.md").open("wb") as stream:
                stream.truncate(2_000_000)
        with self.assertRaises(ServiceError) as caught:
            packet_status(self.instance, "demo")
        self.assertEqual(caught.exception.code, "source_unavailable")

    def test_direct_entry_limit_is_bounded(self):
        import engineering_intelligence_framework.service.packets as packets
        # Small injected budget exercises the same boundary without 5001 files.
        with patch.object(packets, "MAX_PACKET_ENTRIES", 1):
            with self.assertRaises(ServiceError) as caught:
                packet_status(self.instance, "demo")
        self.assertEqual(caught.exception.code, "source_unavailable")

    def test_legacy_packet_and_checkpoint_boundary(self):
        session = self.packet / "sessions/SESSION-001-demo.md"
        session.write_text("---\nid: SESSION-001\nstatus: historical\n---\n", encoding="utf-8")
        result = packet_status(self.instance, "demo")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["data"]["sessions"][0]["status"], "legacy")
        session.write_text("---\nid: SESSION-001\nstatus: prepared\nsession_context: ../outside\n---\n", encoding="utf-8")
        with self.assertRaises(ServiceError) as caught:
            packet_status(self.instance, "demo")
        self.assertEqual(caught.exception.code, "validation_failed")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PacketSourceTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"lab": str(LAB), "preserved": True}))
    print(f"EIF-RESULT: passed={result.testsRun - len(result.errors) - len(result.failures) - len(result.skipped)} total={result.testsRun}")
    raise SystemExit(0 if result.wasSuccessful() else 1)
