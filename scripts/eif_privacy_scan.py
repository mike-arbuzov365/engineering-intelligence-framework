#!/usr/bin/env python3
"""Scan tracked files for absolute-path leaks, secret-shaped patterns, and
instance-specific private tokens (read from .eif/local-denylist.txt, which
is gitignored and never committed).

This is the tool this framework used on itself before its first commit -
see core/policies/decisions.md D-03 and docs/architecture/HOW-EIF-WORKS.md
Limitations. It is a heuristic scanner, not a guarantee: false negatives
are possible. See SECURITY.md#automated-checks.

Usage:
    python scripts/eif_privacy_scan.py [--repo PATH] [--denylist PATH] [--json]

Exit code 1 if any finding is reported (useful for CI), 0 otherwise.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"C:\\Users\\[^\\\s\"'`]+", re.I),
    re.compile(r"/home/[a-z0-9_.\-]+/[^\s\"'`]*", re.I),
    re.compile(r"/Users/[a-zA-Z0-9_.\-]+/[^\s\"'`]*"),
    re.compile(r"[A-Za-z]:[\\/][A-Za-z0-9_.\-]+[\\/][^\s\"'`]{3,}"),
]

# (name, compiled pattern) - pattern should match the *shape* of a secret,
# not its exact value; findings report file + pattern name only, never the
# matched text.
SECRET_PATTERNS = [
    ("api_key_assignment", re.compile(r"(?i)(api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")),
    ("bearer_token", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-.]{16,}")),
    ("password_assignment", re.compile(r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{6,}")),
    ("connection_string", re.compile(r"(?i)(Host=|Server=|postgresql://|mongodb://)[^\s'\"]{6,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
]

DEFAULT_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "graphify-out"}

# This scanner's own source necessarily contains pattern-shaped substrings
# (e.g. the literal text "postgresql://" inside a regex definition), which
# would otherwise self-trigger the very patterns it defines. Skip pattern
# matching against files that just define the patterns.
SELF_EXCLUDE_FILES = {"scripts/eif_privacy_scan.py"}


def list_tracked_files(repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def load_denylist(path: Path) -> list[str]:
    if not path.exists():
        return []
    tokens = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tokens.append(line)
    return tokens


def scan(repo: Path, denylist: list[str]) -> dict:
    # denylisted_token findings are keyed by the token's 1-based *position*
    # in the denylist file, never by the token's literal text - the token
    # itself is the sensitive string, and this dict is what --json prints,
    # so the raw value must never appear as a key or a value here.
    findings = {"absolute_path_leak": [], "secret_shaped": {}, "denylisted_token": {}}
    for rel in list_tracked_files(repo):
        parts = rel.split("/")
        if any(p in DEFAULT_SKIP_DIRS for p in parts):
            continue
        # Never scan the denylist file itself, or its .example template -
        # the template legitimately contains the word "example" tokens and
        # the real file legitimately contains the private strings it exists
        # to hold.
        if rel.startswith(".eif/local-denylist.txt"):
            continue
        if rel.replace("\\", "/") in SELF_EXCLUDE_FILES:
            continue
        full = repo / rel
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pat in ABSOLUTE_PATH_PATTERNS:
            for m in pat.findall(text):
                findings["absolute_path_leak"].append({"file": rel, "match": m[:100]})

        for name, pat in SECRET_PATTERNS:
            if pat.search(text):
                findings["secret_shaped"].setdefault(name, []).append(rel)

        for idx, token in enumerate(denylist, start=1):
            if token.lower() in text.lower():
                findings["denylisted_token"].setdefault(str(idx), []).append(rel)

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="Repository root (default: current directory)")
    ap.add_argument("--denylist", default=None, help="Path to local denylist file (default: <repo>/.eif/local-denylist.txt)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a summary")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    denylist_path = Path(args.denylist) if args.denylist else repo / ".eif" / "local-denylist.txt"
    denylist = load_denylist(denylist_path)

    findings = scan(repo, denylist)
    total = (
        len(findings["absolute_path_leak"])
        + sum(len(v) for v in findings["secret_shaped"].values())
        + sum(len(v) for v in findings["denylisted_token"].values())
    )

    if args.json:
        print(json.dumps(findings, indent=1, ensure_ascii=False))
    else:
        print(f"eif-privacy-scan: {total} finding(s)")
        if findings["absolute_path_leak"]:
            print(f"  absolute_path_leak: {len(findings['absolute_path_leak'])}")
            for f in findings["absolute_path_leak"][:10]:
                print(f"    {f['file']}: {f['match']}")
        for name, files in findings["secret_shaped"].items():
            print(f"  secret_shaped[{name}]: {len(files)} file(s): {', '.join(files[:5])}")
        for idx, files in findings["denylisted_token"].items():
            # Report the denylist line number, never the token's own text -
            # the token IS the sensitive string.
            print(f"  denylisted_token[line {idx}]: {len(files)} file(s): {', '.join(files[:5])}")

    return 1 if total > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
