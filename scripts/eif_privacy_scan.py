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

Suppressions (adoption-hardening round): a narrow, auditable exception
mechanism read from `.eif/config.yaml`'s `privacy.suppressions` - never a
change to a detection pattern itself (patterns stay equally sensitive for
everyone; see core/schemas/eif-config.schema.json for the required shape:
rule, path/glob, rationale, reviewed date, optional expires date). A
suppression that has expired, or no longer matches any real finding, is
itself reported (as a "suppression hygiene" issue, own exit-1 condition) -
it does not just keep silently working forever.

Usage:
    python scripts/eif_privacy_scan.py [--repo PATH] [--denylist PATH] [--config PATH] [--json]

Exit code 1 if any UNSUPPRESSED finding is reported, if any suppression
hygiene issue is found (expired or no-longer-matching), or if the scan
could not run at all (fail-closed). Exit code 0 only when every finding is
either absent or covered by a currently-valid suppression, and every
suppression on file still applies.
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

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
# files, nothing broader (the fixture *data* files under
# scripts/tests/fixtures/ are still scanned normally - they don't contain
# secret-shaped content by design). This is the ONLY path-based exclusion
# in this script - the real, gitignored denylist file is never returned by
# `git ls-files` in the first place, and its committed `.example` template
# is scanned like any other file (a regression fixed 2026-07-16 - it used
# to be excluded by an over-broad startswith() check that also matched the
# .example suffix). test_adoption.py added the same round its own
# secret/keychain-shaped fixture content was written (self-caught in CI,
# not by inspection - a live demonstration of exactly the false-positive
# class the adoption-hardening suppression mechanism exists to handle,
# just on the framework's own repo instead of an adopted one).
SELF_EXCLUDE_FILES = {
    "scripts/eif_privacy_scan.py",
    "scripts/tests/test_privacy_scan.py",
    "scripts/tests/test_adoption.py",
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


def load_suppressions(config_path: Path) -> list[dict]:
    """Read privacy.suppressions from .eif/config.yaml. Missing file, missing
    key, or missing PyYAML all mean "no suppressions configured" - not an
    error; a project with no .eif/config.yaml yet (or none written to disk
    for a test fixture) scans exactly like today, unsuppressed."""
    if yaml is None or not config_path.exists():
        return []
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8", errors="replace")) or {}
    except yaml.YAMLError:
        return []
    return (data.get("privacy") or {}).get("suppressions") or []


def _path_matches(file_rel: str, pattern: str) -> bool:
    norm_file = file_rel.replace("\\", "/")
    norm_pattern = pattern.replace("\\", "/")
    return norm_file == norm_pattern or fnmatch.fnmatch(norm_file, norm_pattern)


def _rule_ids_and_hits(findings: dict) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for hit in findings.get("absolute_path_leak", []):
        out.append(("absolute_path_leak", hit))
    for name, hits in findings.get("secret_shaped", {}).items():
        for hit in hits:
            out.append((f"secret_shaped:{name}", hit))
    for idx, hits in findings.get("denylisted_token", {}).items():
        for hit in hits:
            out.append((f"denylisted_token:{idx}", hit))
    return out


def _bucket_hit(target: dict, rule_id: str, hit: dict) -> None:
    if rule_id == "absolute_path_leak":
        target["absolute_path_leak"].append(hit)
    elif rule_id.startswith("secret_shaped:"):
        target["secret_shaped"].setdefault(rule_id.split(":", 1)[1], []).append(hit)
    elif rule_id.startswith("denylisted_token:"):
        target["denylisted_token"].setdefault(rule_id.split(":", 1)[1], []).append(hit)


def apply_suppressions(findings: dict, suppressions: list[dict], today: str) -> tuple[dict, dict, list[dict]]:
    """Split `findings` (the raw scan() output) into (active, suppressed,
    hygiene_issues) using the config's suppression list. `today` is an
    ISO-8601 date string (plain string comparison against `expires` is
    correct for ISO-8601). A suppression only ever REMOVES a finding from
    `active` into `suppressed` - it never changes what scan() detected.

    hygiene_issues is a flat list of {"rule", "path", "issue"} dicts:
    issue is "expired" (matched at least one finding historically but its
    expires date has passed - the finding stays ACTIVE) or "no longer
    matches any finding" (the rule/path combination never matched
    anything this run - dead configuration, not a live exception)."""
    used = [False] * len(suppressions)
    expired = [False] * len(suppressions)

    def find_suppression(rule_id: str, hit: dict) -> int | None:
        for i, s in enumerate(suppressions):
            if s.get("rule") != rule_id or not _path_matches(hit.get("file", ""), s.get("path", "")):
                continue
            expires = s.get("expires")
            if expires and str(expires) < today:
                expired[i] = True
                continue
            used[i] = True
            return i
        return None

    active = {"absolute_path_leak": [], "secret_shaped": {}, "denylisted_token": {}}
    suppressed = {"absolute_path_leak": [], "secret_shaped": {}, "denylisted_token": {}}
    for rule_id, hit in _rule_ids_and_hits(findings):
        target = suppressed if find_suppression(rule_id, hit) is not None else active
        _bucket_hit(target, rule_id, hit)

    hygiene = []
    for i, s in enumerate(suppressions):
        if used[i]:
            continue
        hygiene.append({
            "rule": s.get("rule"), "path": s.get("path"),
            "issue": "expired" if expired[i] else "no longer matches any finding",
        })
    return active, suppressed, hygiene


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


def _print_findings_block(findings: dict) -> None:
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


def print_report(active: dict, suppressed: dict, hygiene: list[dict], as_json: bool) -> None:
    if as_json:
        # `active` keeps the original top-level shape (backward-compatible
        # with a config that has no suppressions - CI can gate on the
        # top-level keys exactly as before). suppressed/suppression_issues
        # are new, additive keys, never containing a matched secret value.
        output = dict(active)
        output["suppressed"] = suppressed
        output["suppression_issues"] = hygiene
        print(json.dumps(output, indent=1, ensure_ascii=False))
        return

    active_total = count_findings(active)
    suppressed_total = count_findings(suppressed)
    print(f"eif-privacy-scan: {active_total} unsuppressed finding(s), "
          f"{suppressed_total} suppressed (reviewed), {len(hygiene)} suppression hygiene issue(s)")
    _print_findings_block(active)
    if suppressed_total:
        print("  --- suppressed (reviewed, not counted above) ---")
        _print_findings_block(suppressed)
    if hygiene:
        print("  --- suppression hygiene issues (these count as findings) ---")
        for h in hygiene:
            print(f"    {h['rule']} @ {h['path']}: {h['issue']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="Repository root (default: current directory)")
    ap.add_argument("--denylist", default=None, help="Path to local denylist file (default: <repo>/.eif/local-denylist.txt)")
    ap.add_argument("--config", default=None, help="Path to config.yaml holding privacy.suppressions (default: <repo>/.eif/config.yaml)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a summary")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    denylist_path = Path(args.denylist) if args.denylist else repo / ".eif" / "local-denylist.txt"
    denylist = load_denylist(denylist_path)
    config_path = Path(args.config) if args.config else repo / ".eif" / "config.yaml"
    suppressions = load_suppressions(config_path)

    try:
        findings = scan(repo, denylist)
    except RuntimeError as e:
        # Fail closed: a scan that couldn't run must not look like a clean
        # scan (0 findings) to a caller only checking the exit code.
        print(f"eif-privacy-scan: FAILED TO RUN - {e}", file=sys.stderr)
        return 1

    today = datetime.date.today().isoformat()
    active, suppressed, hygiene = apply_suppressions(findings, suppressions, today)
    print_report(active, suppressed, hygiene, args.json)
    return 1 if (count_findings(active) > 0 or hygiene) else 0


if __name__ == "__main__":
    raise SystemExit(main())
