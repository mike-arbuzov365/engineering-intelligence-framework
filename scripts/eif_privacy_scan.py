#!/usr/bin/env python3
"""Scan tracked files for absolute-path leaks, secret-shaped patterns, and
instance-specific private tokens (read from .eif/local-denylist.txt, which
is gitignored and never committed).

This is the tool this framework used on itself before its first commit -
see core/policies/decisions.md D-03 and docs/architecture/HOW-EIF-WORKS.md
Limitations. It is a heuristic scanner, not a guarantee: false negatives
are possible.

Redaction: no matched value (absolute path, secret text, or denylisted
token) is ever printed, in either text or --json output. Findings report
category + file + line number only. This matters most for CI logs, which
are easy to accidentally leave world-readable even on an otherwise private
repository.

Fail-closed: if `git ls-files` fails (wrong directory, corrupted repo,
git not installed), this script exits 1 with an error rather than
silently reporting "0 findings" over an empty file list - a scan that
covered nothing must not look identical to a clean scan.

Usage:
    python scripts/eif_privacy_scan.py [--repo PATH] [--denylist PATH] [--json]

Exit code 1 if any finding is reported, or if the scan could not run at
all (fail-closed). Exit code 0 only on a completed scan with 0 findings.
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
# not its exact value; findings report file + line only, never the matched
# text.
SECRET_PATTERNS = [
    ("api_key_assignment", re.compile(r"(?i)(api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")),
    ("bearer_token", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-.]{16,}")),
    ("password_assignment", re.compile(r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{6,}")),
    ("connection_string", re.compile(r"(?i)(Host=|Server=|postgresql://|mongodb://)[^\s'\"]{6,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
]

DEFAULT_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "graphify-out"}

# This scanner's own source necessarily contains pattern-shaped substrings
# (e.g. the literal text "postgresql://" inside a regex definition), and
# its own test suite necessarily constructs fake-secret/fake-path fixture
# strings to verify detection - both would otherwise self-trigger the
# patterns they define/test. Skip pattern matching against exactly these
# two files, nothing broader (the fixture *data* files under
# scripts/tests/fixtures/ are still scanned normally - they don't contain
# secret-shaped content by design). This is the ONLY path-based exclusion
# in this script - the real, gitignored denylist file is never returned by
# `git ls-files` in the first place, and its committed `.example` template
# is scanned like any other file (a regression fixed 2026-07-16 - it used
# to be excluded by an over-broad startswith() check that also matched the
# .example suffix).
SELF_EXCLUDE_FILES = {
    "scripts/eif_privacy_scan.py",
    "scripts/tests/test_privacy_scan.py",
}


def list_tracked_files(repo: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "ls-files"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git ls-files failed (exit {proc.returncode}) in {repo}: "
            f"{proc.stderr.strip()}"
        )
    return [line for line in proc.stdout.splitlines() if line.strip()]


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
    # Every finding list holds {"file", "line"} dicts only - never the
    # matched text itself, and never the denylist token's own value.
    findings = {"absolute_path_leak": [], "secret_shaped": {}, "denylisted_token": {}}
    for rel in list_tracked_files(repo):
        parts = rel.split("/")
        if any(p in DEFAULT_SKIP_DIRS for p in parts):
            continue
        if rel.replace("\\", "/") in SELF_EXCLUDE_FILES:
            continue
        full = repo / rel
        try:
            lines = full.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        for line_no, line_text in enumerate(lines, start=1):
            for pat in ABSOLUTE_PATH_PATTERNS:
                if pat.search(line_text):
                    findings["absolute_path_leak"].append({"file": rel, "line": line_no})

            for name, pat in SECRET_PATTERNS:
                if pat.search(line_text):
                    findings["secret_shaped"].setdefault(name, []).append({"file": rel, "line": line_no})

            lowered = line_text.lower()
            for idx, token in enumerate(denylist, start=1):
                if token.lower() in lowered:
                    findings["denylisted_token"].setdefault(str(idx), []).append({"file": rel, "line": line_no})

    return findings


def count_findings(findings: dict) -> int:
    return (
        len(findings["absolute_path_leak"])
        + sum(len(v) for v in findings["secret_shaped"].values())
        + sum(len(v) for v in findings["denylisted_token"].values())
    )


def print_report(findings: dict, as_json: bool) -> None:
    if as_json:
        # Findings already contain only {file, line} - safe to dump as-is.
        print(json.dumps(findings, indent=1, ensure_ascii=False))
        return

    total = count_findings(findings)
    print(f"eif-privacy-scan: {total} finding(s)")
    if findings["absolute_path_leak"]:
        print(f"  absolute_path_leak: {len(findings['absolute_path_leak'])}")
        for f in findings["absolute_path_leak"][:10]:
            print(f"    {f['file']}:{f['line']}")
    for name, hits in findings["secret_shaped"].items():
        locs = ", ".join(f"{h['file']}:{h['line']}" for h in hits[:5])
        print(f"  secret_shaped[{name}]: {len(hits)} hit(s): {locs}")
    for idx, hits in findings["denylisted_token"].items():
        # Report the denylist line number, never the token's own text.
        locs = ", ".join(f"{h['file']}:{h['line']}" for h in hits[:5])
        print(f"  denylisted_token[denylist line {idx}]: {len(hits)} hit(s): {locs}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="Repository root (default: current directory)")
    ap.add_argument("--denylist", default=None, help="Path to local denylist file (default: <repo>/.eif/local-denylist.txt)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a summary")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    denylist_path = Path(args.denylist) if args.denylist else repo / ".eif" / "local-denylist.txt"
    denylist = load_denylist(denylist_path)

    try:
        findings = scan(repo, denylist)
    except RuntimeError as e:
        # Fail closed: a scan that couldn't run must not look like a clean
        # scan (0 findings) to a caller only checking the exit code.
        print(f"eif-privacy-scan: FAILED TO RUN - {e}", file=sys.stderr)
        return 1

    print_report(findings, args.json)
    return 1 if count_findings(findings) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
