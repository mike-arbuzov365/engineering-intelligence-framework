#!/usr/bin/env python3
"""Real SDK stdio and raw framing: negative matrix, cancel, kill and EOF."""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests"), str(ROOT / "scripts/tests/fixtures/eif_mcp")]


def main() -> int:
    if importlib.util.find_spec("mcp") is None:
        print("SKIPPED: mcp extra not installed")
        print("EIF-RESULT: passed=0 total=0")
        return 0
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    from seed import seed
    checks = []
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env.pop("EIF_INSTANCE_PATH", None)
    cmd = [sys.executable, "-W", "ignore", "-m", "engineering_intelligence_framework.cli", "mcp", "serve"]

    def check(name, value):
        checks.append(bool(value))
        print(f"{'PASS' if value else 'FAIL'} {name}", flush=True)

    def hashes(root):
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}

    async def sdk_checks(root):
        args = [*cmd[1:], "--instance-path", str(root)]
        params = StdioServerParameters(command=sys.executable, args=args, env=env)
        async with Client(params, read_timeout_seconds=20) as client:
            check("stdio catalog", len((await client.list_tools()).tools) == 9)
            values = await asyncio.gather(client.call_tool("eif_capabilities", {}), client.call_tool("eif_packet_status", {"packet": "demo"}))
            check("simultaneous calls complete", all(v.structured_content.get("request_id") for v in values))
            for name in ("..", "/outside", "C:/outside", ".env", "credentials"):
                result = await client.call_tool("eif_artifact_get", {"kind": "skill", "name": name})
                check("unsafe named source " + name, result.is_error and result.structured_content["error"]["code"] in {"not_found", "validation_failed"} and str(root) not in result.content[0].text)
            extra = await client.call_tool("eif_capabilities", {"path": "outside", "approved": True})
            check("extra fields refused", extra.structured_content["error"]["code"] == "validation_failed")
            missing = root / "knowledge"
            missing.rename(root / "knowledge-saved")
            try:
                response = await client.call_tool("eif_knowledge_search", {"query": "synthetic"})
                check("missing knowledge unavailable", response.structured_content["status"] == "unavailable")
            finally:
                (root / "knowledge-saved").rename(missing)
            runtime = root / ".eif/runtime"
            runtime.rename(root / ".eif/runtime-saved")
            try:
                response = await client.call_tool("eif_artifact_get", {"kind": "skill", "name": "run-execution-packet"})
                check("missing runtime unavailable", response.structured_content["error"]["code"] == "source_unavailable")
            finally:
                (root / ".eif/runtime-saved").rename(runtime)
            lockfile = root / ".eif/framework.lock.yaml"
            original = lockfile.read_bytes()
            lock = yaml.safe_load(original)
            lock["package"]["resource_manifest_digest"] = "sha256:" + "0" * 64
            lockfile.write_text(yaml.safe_dump(lock, sort_keys=False), encoding="utf-8")
            try:
                response = await client.call_tool("eif_capabilities", {})
                # Source-only execution has no installed version: unknown is
                # required rather than pretending a version comparison ran.
                check("drift never silently healthy", response.structured_content["status"] in {"stale", "unknown"})
            finally:
                lockfile.write_bytes(original)
            # A very large outline forces the real transport's generic byte
            # guard; it is packet metadata, never an unpinned policy file.
            folder = root / "planning/packets/demo/sessions"
            large = folder / "SESSION-002-huge.md"
            large.write_text("---\nid: SESSION-002\nstatus: prepared\ndepends_on: [" + ",".join("SESSION-001" for _ in range(10000)) + "]\n---\n", encoding="utf-8")
            try:
                response = await client.call_tool("eif_packet_status", {"packet": "demo"})
                check("large response explicit", response.structured_content["status"] == "truncated" and response.structured_content["truncated"])
            finally:
                large.unlink()
            external = root.parent / "external"
            external.mkdir()
            (external / "note.md").write_text("outside sentinel", encoding="utf-8")
            link = missing / "external"
            try:
                link.symlink_to(external, target_is_directory=True)
            except OSError:
                if os.name == "nt":
                    made = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", f"New-Item -ItemType Junction -Path '{link}' -Target '{external}' | Out-Null"], capture_output=True)
                    assert made.returncode == 0
                else:
                    raise
            try:
                response = await client.call_tool("eif_knowledge_search", {"query": "sentinel"})
                check("external symlink or junction refused", response.structured_content["error"]["code"] == "source_unavailable")
            finally:
                if link.is_symlink():
                    link.unlink()
                else:
                    os.rmdir(link)
        slow_params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "scripts/tests/fixtures/eif_mcp/slow_server.py"), str(root)], env=env)
        async with Client(slow_params, read_timeout_seconds=20) as client:
            task = asyncio.create_task(client.call_tool("eif_doctor", {}))
            await asyncio.sleep(0.25)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            follow = await client.call_tool("eif_capabilities", {})
            check("cancel followed by usable transport", follow.structured_content["data"]["mode"] == "reader")

    async def raw_checks(root, *, kill=False):
        command = [sys.executable, str(ROOT / "scripts/tests/fixtures/eif_mcp/slow_server.py"), str(root)] if kill else [*cmd, "--instance-path", str(root)]
        proc = await asyncio.create_subprocess_exec(*command, env=env, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        async def send(value):
            proc.stdin.write((json.dumps(value) + "\n").encode())
            await proc.stdin.drain()

        async def response(expected):
            while True:
                line = await asyncio.wait_for(proc.stdout.readline(), 15)
                assert line, "transport closed before reply"
                value = json.loads(line)
                assert value.get("jsonrpc") == "2.0"
                if value.get("id") == expected:
                    return value

        try:
            await send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "synthetic-raw", "version": "0"}}})
            initialized = await response(1)
            check("server identity", initialized["result"]["serverInfo"]["name"] == "eif-mcp")
            await send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            await send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "eif_doctor", "arguments": {}}})
            if kill:
                while True:
                    line = await asyncio.wait_for(proc.stderr.readline(), 15)
                    if b"call_started" in line:
                        break
                proc.kill()
                await asyncio.wait_for(proc.wait(), 10)
                check("kill during active call exits", proc.returncode != 0)
            else:
                reply = await response(2)
                check("stdout contains protocol only", "structuredContent" in reply["result"])
                proc.stdin.close()
                await asyncio.wait_for(proc.wait(), 10)
                check("EOF clean exit", proc.returncode == 0)
                logs = (await proc.stderr.read()).decode("utf-8", "replace")
                rows = [json.loads(line) for line in logs.splitlines() if line.strip()]
                check("logs contain metadata only", rows and all(set(row) == {"time", "request_id", "tool", "status", "duration_ms", "response_bytes"} for row in rows))
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()

    with tempfile.TemporaryDirectory(prefix="eif-mcp-stdio-") as tmp:
        root = seed(Path(tmp) / "project")
        initial = hashes(root)
        asyncio.run(sdk_checks(root))
        check("SDK reader leaves files unchanged", initial == hashes(root))
        asyncio.run(raw_checks(root))
        asyncio.run(raw_checks(root, kill=True))
        check("kill leaves files unchanged", initial == hashes(root))
        for args in ([], ["--instance-path", str(Path(tmp))], ["--instance-path", str(root), "--packets-root", "../outside"]):
            result = subprocess.run([*cmd, *args], env=env, capture_output=True, timeout=15)
            check("invalid startup code 3", result.returncode == 3 and not result.stdout and b"Traceback" not in result.stderr)
        lock = root / ".eif/framework.lock.yaml"
        original = lock.read_bytes()
        lock.write_text("broken: lock\n", encoding="utf-8")
        result = subprocess.run([*cmd, "--instance-path", str(root)], env=env, capture_output=True, timeout=15)
        check("broken lock startup rejected", result.returncode == 3 and not result.stdout)
        lock.write_bytes(original)
        result = subprocess.run([*cmd, "--instance-path", str(root)], env=env, input=b"", capture_output=True, timeout=15)
        check("empty stdin exits cleanly", result.returncode == 0 and not result.stdout)
    print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
