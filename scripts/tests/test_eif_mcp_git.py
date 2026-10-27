#!/usr/bin/env python3
"""Git filters and metadata redirects through the real MCP stdio transport."""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests"), str(ROOT / "scripts/tests/fixtures/eif_mcp")]


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True).stdout


def commit(root, *paths):
    git(root, "add", "--", *paths)
    git(root, "-c", "user.name=Synthetic Test", "-c", "user.email=synthetic@example.invalid",
        "-c", "core.hooksPath=" + os.devnull, "commit", "-m", "Synthetic Git fixture")


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


@contextmanager
def file_content(path, content):
    original = path.read_bytes() if path.exists() else None
    path.write_bytes(content)
    try:
        yield
    finally:
        if original is None:
            path.unlink()
        else:
            path.write_bytes(original)


@contextmanager
def linked_directory(path, target, base):
    saved = base / ("saved-" + path.name)
    path.rename(saved)
    try:
        try:
            path.symlink_to(target, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            quoted = [str(p).replace("'", "''") for p in (path, target)]
            subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            f"New-Item -ItemType Junction -Path '{quoted[0]}' -Target '{quoted[1]}' | Out-Null"],
                           capture_output=True, check=True)
        try:
            yield
        finally:
            if path.is_symlink():
                path.unlink()
            else:
                os.rmdir(path)
    finally:
        saved.rename(path)


def main():
    if importlib.util.find_spec("mcp") is None:
        print("SKIPPED: mcp extra not installed\nEIF-RESULT: passed=0 total=0")
        return 0
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    from engineering_intelligence_framework.commands import session
    from engineering_intelligence_framework.service import Instance, ServiceError
    from engineering_intelligence_framework.service.operations import session_resume_audit
    from seed import seed

    checks = []

    def check(name, value):
        checks.append(bool(value))
        print(f"{'PASS' if value else 'FAIL'} {name}", flush=True)

    async def run(base):
        root = seed(base / "project")
        commit(root, ".gitignore")
        foreign = base / "foreign"
        foreign.mkdir()
        branch = git(root, "symbolic-ref", "--short", "HEAD").decode().strip()
        git(foreign, "init", "--initial-branch=" + branch)
        (foreign / "foreign.txt").write_bytes(b"outside synthetic repository\n")
        commit(foreign, "foreign.txt")
        foreign_head = git(foreign, "rev-parse", "HEAD").decode().strip()
        check("synthetic repositories have distinct HEADs on the same branch",
              foreign_head != git(root, "rev-parse", "HEAD").decode().strip())
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        env.pop("EIF_INSTANCE_PATH", None)
        params = StdioServerParameters(command=sys.executable,
            args=["-W", "ignore", "-m", "engineering_intelligence_framework.cli", "mcp", "serve", "--instance-path", str(root)], env=env)

        async def refusal(label, *, before_git=False):
            if before_git:
                instance = Instance(root)
                with patch.object(session, "_run_git", side_effect=AssertionError("unexpected Git subprocess")) as called:
                    try:
                        session_resume_audit(instance, "demo")
                    except (ServiceError, AssertionError) as error:
                        check(label + " refused before first Git subprocess",
                              isinstance(error, ServiceError) and error.code == "source_unavailable" and called.call_count == 0)
                    else:
                        check(label + " refused before first Git subprocess", False)
            async with Client(params, read_timeout_seconds=25) as client:
                value = await client.call_tool("eif_session_resume_audit", {"session_id": "demo"})
                data = value.structured_content
                check(label + " typed stdio refusal", value.is_error and data.get("error", {}).get("code") == "source_unavailable")
                check(label + " foreign HEAD never returned", foreign_head not in value.content[0].text)
                check(label + " direct CLI fallback", "eifctl session resume-audit" in data.get("error", {}).get("message", ""))

        probe = root / "probe.txt"
        probe.write_bytes(b"original\n")
        attributes = root / ".gitattributes"
        with attributes.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\nprobe.txt -text\n")
        commit(root, "probe.txt", ".gitattributes")
        attributes_original = attributes.read_bytes()
        config = root / ".git/config"
        config_original = config.read_bytes()
        marker = root / "FILTER_SIDE_EFFECT.txt"
        canary = base / "filter_canary.py"
        command = '"' + Path(sys.executable).as_posix() + '" "' + canary.as_posix() + '"'
        requests = [
            ("eif_capabilities", {}), ("eif_brief", {"task_kind": "packet_run"}),
            ("eif_artifact_get", {"kind": "skill", "name": "run-execution-packet"}),
            ("eif_knowledge_search", {"query": "cobalt"}), ("eif_packet_status", {"packet": "demo"}),
            ("eif_doctor", {}), ("eif_session_validate", {"session_id": "demo"}),
            ("eif_session_resume_audit", {"session_id": "demo"}),
            ("eif_delivery_check", {"action": "package", "scope": "synthetic"}),
        ]
        for driver in ("clean", "process", "smudge"):
            canary.write_text("from pathlib import Path\nimport sys\nPath(" + repr(str(marker)) + ").write_text('filter ran')\n" +
                              ("raise SystemExit(1)\n" if driver == "process" else "sys.stdout.buffer.write(sys.stdin.buffer.read())\n"), encoding="utf-8")
            with file_content(attributes, attributes_original + b"\nprobe.txt filter=fixture\n"), file_content(config, config_original):
                git(root, "config", "filter.fixture." + driver, command)
                probe.write_bytes(b"modified\n")
                os.utime(probe, (time.time() + 2, time.time() + 2))
                check(driver + " fixture preserves index file size", len(probe.read_bytes()) == len(b"original\n"))
                before = hashes(root)
                async with Client(params, read_timeout_seconds=25) as client:
                    for name, arguments in requests:
                        value = await client.call_tool(name, arguments)
                        check(driver + " " + name + " never runs filter", not marker.exists())
                        if name == "eif_session_resume_audit":
                            check(driver + " audit has typed refusal", value.is_error and value.structured_content.get("error", {}).get("code") == "source_unavailable")
                            check(driver + " audit has CLI fallback", "eifctl session resume-audit" in value.structured_content.get("error", {}).get("message", ""))
                check(driver + " all nine readers preserve instance bytes", before == hashes(root))
                marker.unlink(missing_ok=True)

        hooks = base / "hooks"
        hooks.mkdir()
        hook = hooks / "post-index-change"
        hook.write_text("#!/bin/sh\n" + command + "\n", encoding="utf-8", newline="\n")
        hook.chmod(0o755)
        with file_content(config, config_original):
            git(root, "config", "core.fsmonitor", command)
            git(root, "config", "core.hooksPath", str(hooks))
            before = hashes(root)
            async with Client(params, read_timeout_seconds=25) as client:
                value = await client.call_tool("eif_session_resume_audit", {"session_id": "demo"})
                check("disabled fsmonitor and hooks still allow ordinary audit", not value.is_error)
                check("configured fsmonitor and hook programs never run", not marker.exists())
            check("disabled programs preserve instance bytes", before == hashes(root))

        for relative, content in [
            ("commondir", (str(foreign / ".git") + "\n").encode()),
            ("commondir", b"../../foreign/.git\n"),
            ("objects/info/alternates", (str(foreign / ".git/objects") + "\n").encode()),
            ("objects/info/http-alternates", b"file:../../foreign/.git/objects\n"),
            ("config.worktree", b"[include]\npath = ../../external-config\n"),
            ("gitdir", (str(foreign) + "\n").encode()),
        ]:
            with file_content(root / ".git" / relative, content):
                await refusal(relative, before_git=True)

        git_dir = root / ".git"
        for relative in (".git", ".git/objects", ".git/refs"):
            target = foreign / relative
            with linked_directory(root / relative, target, base):
                await refusal(relative + " directory link", before_git=True)
        saved = base / "held-git"
        git_dir.rename(saved)
        try:
            with file_content(git_dir, ("gitdir: " + str(foreign / ".git") + "\n").encode()):
                await refusal("external gitdir file", before_git=True)
        finally:
            saved.rename(git_dir)
        for relative in ("HEAD", "config"):
            local = git_dir / relative
            original = local.read_bytes()
            local.unlink()
            os.link(foreign / ".git" / relative, local)
            try:
                await refusal(relative + " external hardlink", before_git=True)
            finally:
                local.unlink()
                local.write_bytes(original)

        for key, value in [("core.worktree", str(foreign)), ("core.attributesFile", str(foreign / "attributes")),
                           ("core.excludesFile", str(foreign / "excludes")), ("extensions.worktreeConfig", "true"),
                           ("remote.fixture.promisor", "true"), ("extensions.partialClone", "fixture")]:
            with file_content(config, config_original):
                git(root, "config", key, value)
                await refusal(key)

    with tempfile.TemporaryDirectory(prefix="eif-mcp-git-") as tmp:
        asyncio.run(run(Path(tmp)))
    print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
