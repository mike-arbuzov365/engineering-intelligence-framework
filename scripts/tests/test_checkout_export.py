#!/usr/bin/env python3
"""Export a dirty tracked tree byte-for-byte despite ambient CRLF settings."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from test_package_build import clean_checkout_export


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True).stdout


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def main():
    checks = []

    def check(name, value):
        checks.append(bool(value))
        print(f"{'PASS' if value else 'FAIL'} {name}")

    with tempfile.TemporaryDirectory(prefix="eif-export-") as tmp:
        base = Path(tmp)
        system_config = base / "system-config"
        system_config.write_bytes(b"[core]\n\tautocrlf = true\n")
        env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
        env.update(GIT_CONFIG_SYSTEM=str(system_config), GIT_CONFIG_GLOBAL=os.devnull)
        with patch.dict(os.environ, env, clear=True):
            root = base / "source"
            root.mkdir()
            git(root, "init", "--initial-branch=main")
            check("fixture uses ambient autocrlf=true", git(root, "config", "--get", "core.autocrlf").strip() == b"true")
            files = {".gitattributes": b"* text eol=lf\n*.bin -text\n", "text.txt": b"original\n",
                     "rename.txt": b"rename me\n", "deleted.txt": b"delete me\n", "binary.bin": bytes(range(256))}
            for name, content in files.items():
                (root / name).write_bytes(content)
            git(root, "add", ".")
            git(root, "-c", "user.name=Synthetic Test", "-c", "user.email=synthetic@example.invalid",
                "-c", "core.hooksPath=" + os.devnull, "commit", "-m", "Synthetic export fixture")
            (root / "text.txt").write_bytes(b"staged edit\n")
            (root / "new.bin").write_bytes(b"\0new binary\xff")
            git(root, "add", "text.txt", "new.bin")
            (root / "text.txt").write_bytes(b"staged edit\nunstaged edit\n")
            git(root, "mv", "rename.txt", "renamed.txt")
            (root / "renamed.txt").write_bytes(b"rename me\nwith an unstaged edit\n")
            (root / "binary.bin").write_bytes(b"\0changed binary\xff")
            (root / "deleted.txt").unlink()
            (root / "untracked.txt").write_bytes(b"excluded\n")
            tracked = [p.decode() for p in git(root, "ls-files", "-z").split(b"\0") if p]
            expected = {p: (root / p).read_bytes() for p in tracked if (root / p).is_file()}
            before = hashes(root)
            index = (root / ".git/index").read_bytes()
            refs = git(root, "for-each-ref")
            destination = base / "export"
            clean_checkout_export(root, destination)
            actual = {p.relative_to(destination).as_posix(): p.read_bytes() for p in destination.rglob("*") if p.is_file()}
            check("export preserves all normalized tracked bytes", actual == expected)
            for name in ("text.txt", "renamed.txt", "binary.bin", "new.bin"):
                check(name + " exact bytes", actual.get(name) == expected[name])
            check("untracked file excluded", "untracked.txt" not in actual)
            check("deletion retained", "deleted.txt" not in actual and "rename.txt" not in actual)
            check("source files unchanged", before == hashes(root))
            check("source index unchanged", index == (root / ".git/index").read_bytes())
            check("source refs unchanged", refs == git(root, "for-each-ref"))
    print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
