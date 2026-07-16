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
category + file + line number + a one-way content fingerprint only. This
matters most for CI logs, which are easy to accidentally leave world-
readable even on an otherwise private repository.

Fail-closed: if `git ls-files` fails (wrong directory, corrupted repo,
git not installed), this script exits 1 with an error rather than
silently reporting "0 findings" over an empty file list - a scan that
covered nothing must not look identical to a clean scan.

Suppressions (adoption-hardening round, independent-review redesign):
a FINDING-specific exception mechanism read from `.eif/config.yaml`'s
`privacy.suppressions` - never a change to a detection pattern itself
(patterns stay equally sensitive for everyone). Each entry identifies one
exact finding: rule + exact repo-relative path (no globs - see
core/schemas/eif-config.schema.json) + a 16-hex-char content fingerprint
(sha256 of rule+path+the finding's own line, normalized - never the
matched secret value itself). A second, real finding of the same rule at
the same path is a DIFFERENT fingerprint and stays active - one narrow
suppression can never blanket-cover a whole rule+file. An unrecognized
rule ID, a glob-shaped path, or an unparseable reviewed/expires date is a
hard config error (fail loudly, refuse to run) - not a silently-skipped
suppression entry. A suppression that has expired, or no longer matches
any real finding (fingerprint moved because the line's content changed,
or the finding is gone), is itself reported as a "suppression hygiene"
finding, its own exit-1 condition - it does not just keep silently
working forever.

Usage:
    python scripts/eif_privacy_scan.py [--repo PATH] [--denylist PATH] [--config PATH] [--json]

Exit code 1 if any UNSUPPRESSED finding is reported, if any suppression
hygiene issue is found (expired or no-longer-matching), if the suppression
config itself is invalid (fail loudly), or if the scan could not run at
all (fail-closed). Exit code 0 only when every finding is either absent or
covered by a currently-valid suppression, and every suppression on file
still applies.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
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
# not its exact value; findings report file + line + fingerprint only,
# never the matched text.
SECRET_PATTERNS = [
    ("api_key_assignment", re.compile(r"(?i)(api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}")),
    ("bearer_token", re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-.]{16,}")),
    ("password_assignment", re.compile(r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{6,}")),
    ("connection_string", re.compile(r"(?i)(Host=|Server=|postgresql://|mongodb://)[^\s'\"]{6,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
]

# The complete, hand-maintained set of rule IDs this scanner can ever emit -
# a suppression naming anything else is a config error (independent-review
# requirement), not silently ignored. denylisted_token IDs are dynamic
# (keyed by the local denylist file's own line numbers), matched by shape.
KNOWN_RULE_IDS = {"absolute_path_leak"} | {f"secret_shaped:{name}" for name, _ in SECRET_PATTERNS}
_DENYLIST_RULE_RE = re.compile(r"^denylisted_token:\d+$")
_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{16}$")
_GLOB_CHARS = set("*?[]")


def is_known_rule_id(rule: str) -> bool:
    return rule in KNOWN_RULE_IDS or bool(_DENYLIST_RULE_RE.match(rule))


def compute_fingerprint(rule: str, path: str, line_text: str) -> str:
    """16 hex chars of sha256(rule\\0 normalized_path\\0 normalized_line).
    A one-way hash - cannot be reversed to recover the original line, so
    printing it (unlike the line itself) never violates the redaction
    invariant. Normalizes the path separator and strips the line's
    surrounding whitespace so the fingerprint survives re-indentation and
    Windows/POSIX path-separator differences, while still changing the
    instant the line's actual content changes."""
    normalized_path = path.replace("\\", "/")
    normalized_line = line_text.strip()
    h = hashlib.sha256()
    h.update(rule.encode("utf-8"))
    h.update(b"\x00")
    h.update(normalized_path.encode("utf-8"))
    h.update(b"\x00")
    h.update(normalized_line.encode("utf-8"))
    return h.hexdigest()[:16]


DEFAULT_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "graphify-out"}

# This scanner's own source necessarily contains pattern-shaped substrings
# (e.g. the literal text "postgresql://" inside a regex definition), and
# its own test suite necessarily constructs fake-secret fixture strings to
# verify detection - both would otherwise self-trigger the patterns they
# define/test. Skip pattern matching against exactly this one file, nothing
# broader. Independent-review fix: scripts/tests/test_adoption.py used to
# be added here too when its own adoption fixture tripped this scanner on
# CI - the actual fix was making that fixture's secret-shaped strings get
# assembled from split literals at runtime (so the SOURCE file's contiguous
# text never matches the pattern, but the in-memory value used to write the
# separate fixture file still does), not excluding the whole test file from
# scanning. The real, gitignored denylist file is never returned by
# `git ls-files` in the first place, and its committed `.example` template
# is scanned like any other file.
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


class SuppressionConfigError(Exception):
    """The suppression config EXISTS but cannot be trusted to read -
    independent-review requirement: a broken existing config must fail the
    scan loudly, never be silently treated as an empty suppression list
    (which would let a real finding through if the config the operator
    thinks is suppressing something is actually not being read at all)."""


def load_suppressions(config_path: Path) -> list[dict]:
    """Read privacy.suppressions from .eif/config.yaml, UNvalidated - call
    validate_suppressions() on the result before trusting it.

    Five states, deliberately distinguished (independent-review fix - the
    previous version collapsed the broken ones into a silent empty list,
    and treated an EMPTY existing file as a valid suppression-free config):
      - config ABSENT            -> [] (no suppressions; scan continues
                                        exactly as for a repo with no
                                        .eif/config.yaml yet)
      - config exists + VALID    -> the suppressions list (possibly empty)
      - config exists + EMPTY    -> SuppressionConfigError. eif_init.py never
        (yaml.safe_load -> None)   writes an empty config, so an existing
                                  empty one is a truncated/hand-cleared file,
                                  not a legitimate "no suppressions" signal -
                                  reading it as [] could silently let through
                                  a finding the operator believes is suppressed.
      - config exists + invalid  -> SuppressionConfigError (bad YAML, not a
        YAML / not a mapping      mapping, or privacy/suppressions of the
                                  wrong type)
      - config exists + PyYAML   -> SuppressionConfigError (cannot read it,
        UNAVAILABLE               so cannot honor its suppressions - do not
                                  pretend there are none)
    """
    if not config_path.exists():
        return []
    if yaml is None:
        raise SuppressionConfigError(
            f"{config_path} exists but PyYAML is not installed, so its "
            f"privacy.suppressions cannot be read - refusing to scan as if there "
            f"were no suppressions (a real one could be silently ignored). Install "
            f"with: pip install -r scripts/requirements.txt"
        )
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8", errors="replace"))
    except yaml.YAMLError as e:
        raise SuppressionConfigError(f"{config_path} is not valid YAML: {e}")
    if data is None:
        # An EXISTING but empty config is NOT a valid suppression-free config
        # (unlike an absent one, handled above). eif_init.py always writes a
        # non-empty config (header + real data), so an empty existing file is
        # an anomaly - a truncated or hand-cleared write - that must fail
        # loudly, never be read as "no suppressions" (which could silently let
        # through a finding the operator thinks is covered). This matches
        # eif_init.py, which also refuses an empty existing config.
        raise SuppressionConfigError(
            f"{config_path} exists but is empty - refusing to treat an empty "
            f"config as a valid suppression-free config (a truncated or "
            f"hand-cleared file). Restore it from version control, or remove it "
            f"entirely if this repo genuinely has no .eif/config.yaml."
        )
    if not isinstance(data, dict):
        raise SuppressionConfigError(
            f"{config_path} does not contain a YAML mapping at the top level "
            f"(got {type(data).__name__})"
        )
    privacy = data.get("privacy")
    if privacy is None:
        return []
    if not isinstance(privacy, dict):
        raise SuppressionConfigError(f"{config_path}: 'privacy' must be a mapping, got {type(privacy).__name__}")
    suppressions = privacy.get("suppressions")
    if suppressions is None:
        return []
    if not isinstance(suppressions, list):
        raise SuppressionConfigError(
            f"{config_path}: 'privacy.suppressions' must be a list, got {type(suppressions).__name__}"
        )
    return suppressions


def validate_suppressions(suppressions: list[dict]) -> list[str]:
    """Returns error strings - empty means every suppression is well-formed
    enough to apply. Independent-review requirement: an unrecognized rule
    ID, a glob-shaped path, a missing/malformed fingerprint, or an
    unparseable reviewed/expires date must fail the whole run loudly, not
    be silently skipped or partially applied."""
    errors: list[str] = []
    for i, s in enumerate(suppressions):
        if not isinstance(s, dict):
            errors.append(f"suppression[{i}]: must be a mapping, got {type(s).__name__}")
            continue
        rule = s.get("rule")
        if not rule or not isinstance(rule, str) or not is_known_rule_id(rule):
            errors.append(f"suppression[{i}]: unrecognized rule id {rule!r} - not one of this scanner's known rules")
        path = s.get("path")
        if not path or not isinstance(path, str):
            errors.append(f"suppression[{i}]: missing or non-string 'path'")
        elif _GLOB_CHARS & set(path):
            errors.append(f"suppression[{i}]: path {path!r} looks like a glob (contains {sorted(_GLOB_CHARS & set(path))}) - suppressions require an exact path")
        fingerprint = s.get("fingerprint")
        if not fingerprint or not isinstance(fingerprint, str) or not _FINGERPRINT_RE.match(fingerprint):
            errors.append(f"suppression[{i}]: fingerprint must be exactly 16 lowercase hex characters, got {fingerprint!r}")
        if not s.get("rationale"):
            errors.append(f"suppression[{i}]: missing required 'rationale'")
        if not s.get("reviewed"):
            errors.append(f"suppression[{i}]: missing required 'reviewed' date")
        for date_field in ("reviewed", "expires"):
            val = s.get(date_field)
            if val is None:
                continue
            try:
                datetime.date.fromisoformat(str(val))
            except ValueError:
                errors.append(f"suppression[{i}]: {date_field} {val!r} is not a valid ISO-8601 date (YYYY-MM-DD)")
    return errors


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
    """Split `findings` (the raw scan() output, each hit already carrying
    its own fingerprint) into (active, suppressed, hygiene_issues) using
    the config's suppression list. `today` is an ISO-8601 date string
    (plain string comparison against `expires` is correct for ISO-8601).
    A suppression only ever REMOVES a finding from `active` into
    `suppressed` - it never changes what scan() detected. Matching is
    exact: rule + exact path + exact fingerprint - a second, different
    finding of the same rule at the same path (different fingerprint,
    e.g. a real secret a few lines below a reviewed false positive) is
    NEVER covered by this suppression and stays active.

    hygiene_issues is a flat list of {"rule", "path", "issue"} dicts:
    issue is "expired" (matched at least one finding historically but its
    expires date has passed - the finding stays ACTIVE) or "no longer
    matches any finding" (the rule/path/fingerprint combination never
    matched anything this run - either the line's content changed, it
    moved to a different rule/path, or it's gone; dead configuration, not
    a live exception)."""
    used = [False] * len(suppressions)
    expired = [False] * len(suppressions)

    def find_suppression(rule_id: str, hit: dict) -> int | None:
        hit_path = hit.get("file", "").replace("\\", "/")
        hit_fp = hit.get("fingerprint")
        for i, s in enumerate(suppressions):
            if s.get("rule") != rule_id:
                continue
            if s.get("path", "").replace("\\", "/") != hit_path:
                continue
            if s.get("fingerprint") != hit_fp:
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
            "issue": "expired" if expired[i] else "no longer matches any finding (fingerprint mismatch or finding gone)",
        })
    return active, suppressed, hygiene


def scan(repo: Path, denylist: list[str]) -> dict:
    # Every finding list holds {"file", "line", "fingerprint"} dicts only -
    # never the matched text itself, and never the denylist token's own
    # value. fingerprint is a one-way hash, safe to print (independent-
    # review addition - makes each finding suppressible individually).
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
                    findings["absolute_path_leak"].append(
                        {"file": rel, "line": line_no, "fingerprint": compute_fingerprint("absolute_path_leak", rel, line_text)}
                    )

            for name, pat in SECRET_PATTERNS:
                if pat.search(line_text):
                    rule_id = f"secret_shaped:{name}"
                    findings["secret_shaped"].setdefault(name, []).append(
                        {"file": rel, "line": line_no, "fingerprint": compute_fingerprint(rule_id, rel, line_text)}
                    )

            lowered = line_text.lower()
            for idx, token in enumerate(denylist, start=1):
                if token.lower() in lowered:
                    rule_id = f"denylisted_token:{idx}"
                    findings["denylisted_token"].setdefault(str(idx), []).append(
                        {"file": rel, "line": line_no, "fingerprint": compute_fingerprint(rule_id, rel, line_text)}
                    )

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
            print(f"    {f['file']}:{f['line']} [fp:{f['fingerprint']}]")
    for name, hits in findings["secret_shaped"].items():
        locs = ", ".join(f"{h['file']}:{h['line']} [fp:{h['fingerprint']}]" for h in hits[:5])
        print(f"  secret_shaped[{name}]: {len(hits)} hit(s): {locs}")
    for idx, hits in findings["denylisted_token"].items():
        # Report the denylist line number, never the token's own text.
        locs = ", ".join(f"{h['file']}:{h['line']} [fp:{h['fingerprint']}]" for h in hits[:5])
        print(f"  denylisted_token[denylist line {idx}]: {len(hits)} hit(s): {locs}")


def print_report(active: dict, suppressed: dict, hygiene: list[dict], as_json: bool) -> None:
    if as_json:
        # `active` keeps the original top-level shape (backward-compatible
        # with a config that has no suppressions - CI can gate on the
        # top-level keys exactly as before). suppressed/suppression_issues
        # are new, additive keys, never containing a matched secret value -
        # fingerprint is a one-way hash, safe to include.
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="Repository root (default: current directory)")
    ap.add_argument("--denylist", default=None, help="Path to local denylist file (default: <repo>/.eif/local-denylist.txt)")
    ap.add_argument("--config", default=None, help="Path to config.yaml holding privacy.suppressions (default: <repo>/.eif/config.yaml)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a summary")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    denylist_path = Path(args.denylist) if args.denylist else repo / ".eif" / "local-denylist.txt"
    denylist = load_denylist(denylist_path)
    config_path = Path(args.config) if args.config else repo / ".eif" / "config.yaml"
    try:
        suppressions = load_suppressions(config_path)
    except SuppressionConfigError as e:
        # A broken EXISTING config fails loudly here (independent-review
        # requirement) - never silently degrade to "no suppressions",
        # which would let a finding the operator believes is suppressed
        # through, or hide that the config isn't being read at all.
        print(f"eif-privacy-scan: cannot load suppression config - {e}", file=sys.stderr)
        return 1

    suppression_errors = validate_suppressions(suppressions)
    if suppression_errors:
        # Fail loudly (independent-review requirement) - an invalid
        # suppression config must stop the run, not be silently skipped
        # or partially applied.
        print(f"eif-privacy-scan: INVALID privacy.suppressions config in {config_path} - refusing to run:", file=sys.stderr)
        for e in suppression_errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

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
