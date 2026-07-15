#!/usr/bin/env python3
"""Tests for eif_privacy_scan.py: detection, false positives, fail-closed
behavior on git failure, and redaction (no raw secret/path/token value
ever appears in output, text or --json).

Usage:
    python scripts/tests/test_privacy_scan.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "eif_privacy_scan.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import eif_privacy_scan  # noqa: E402


def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def make_git_repo(tmp: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp, check=True)


def git_add(tmp: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True)


SECRET_VALUE = "sk-abcdef0123456789abcdef"
DENYLIST_TOKEN = "SecretProjectCodename"
LEAK_PATH_FRAGMENT = "Test User"  # part of a C:\Users\Test User\... path


def main() -> int:
    failures = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        status = "PASS" if cond else "FAIL"
        print(f"{status} {name}" + (f": {detail}" if detail and not cond else ""))
        if not cond:
            failures.append(name)

    # --- 1. Clean repo -> 0 findings, exit 0 ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "clean.md").write_text("Nothing sensitive here. Just prose.\n", encoding="utf-8")
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        check("clean repo: exit 0", proc.returncode == 0)
        result = json.loads(proc.stdout)
        check("clean repo: 0 findings", sum(len(v) if isinstance(v, list) else sum(len(x) for x in v.values()) for v in result.values()) == 0)

    # --- 2. Absolute path leak detected ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "leaky.md").write_text(f"See C:\\Users\\{LEAK_PATH_FRAGMENT}\\Documents\\notes.txt\n", encoding="utf-8")
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        check("absolute path: detected", len(result["absolute_path_leak"]) >= 1)
        check("absolute path: exit 1", proc.returncode == 1)
        check("absolute path: line number reported", result["absolute_path_leak"] and result["absolute_path_leak"][0].get("line") == 1)

    # --- 3. Secret-shaped pattern detected ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "config.md").write_text(f"api_key: {SECRET_VALUE}\n", encoding="utf-8")
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        check("secret: detected", "api_key_assignment" in result["secret_shaped"])
        check("secret: exit 1", proc.returncode == 1)

    # --- 4. Denylisted token detected ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "local-denylist.txt").write_text(f"{DENYLIST_TOKEN}\n", encoding="utf-8")
        (tmp / "other.md").write_text(f"This mentions {DENYLIST_TOKEN} by accident.\n", encoding="utf-8")
        # local-denylist.txt itself is real, local, gitignored - but this
        # temp repo has no .gitignore, so `git add -A` would track it too.
        # Simulate the real setup: only `other.md` is tracked.
        subprocess.run(["git", "add", "other.md"], cwd=tmp, check=True)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        check("denylist: detected", "1" in result["denylisted_token"])
        check("denylist: exit 1", proc.returncode == 1)

    # --- 5. False-positive check: ordinary relative paths and prose don't trigger ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "ordinary.md").write_text(
            "See scripts/eif_privacy_scan.py and core/schemas/eif-config.schema.json.\n"
            "Run `pip install -r scripts/requirements.txt`.\n"
            "The password field in the config schema documents a password policy.\n",
            encoding="utf-8",
        )
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        total = len(result["absolute_path_leak"]) + sum(len(v) for v in result["secret_shaped"].values())
        check("false positive: ordinary relative paths/prose clean", total == 0, f"got {total} findings: {result}")

    # --- 6. Fail-closed when git ls-files fails (not a git repo at all) ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "somefile.md").write_text("no git repo here\n", encoding="utf-8")
        proc = run(["--repo", str(tmp)])
        check("fail-closed: non-git directory exits 1 (not a silent 0-findings pass)", proc.returncode == 1)
        check("fail-closed: stderr explains why", "FAILED TO RUN" in proc.stderr or "git ls-files" in proc.stderr, proc.stderr)

    # --- 7. Redaction: raw values never appear in stdout/stderr, text or json ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "local-denylist.txt").write_text(f"{DENYLIST_TOKEN}\n", encoding="utf-8")
        (tmp / "combo.md").write_text(
            f"See C:\\Users\\{LEAK_PATH_FRAGMENT}\\file.txt and api_key: {SECRET_VALUE} "
            f"and {DENYLIST_TOKEN}.\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "combo.md"], cwd=tmp, check=True)
        for extra_args, label in ([], "text"), (["--json"], "json"):
            proc = run(["--repo", str(tmp), *extra_args])
            combined = proc.stdout + proc.stderr
            check(f"redaction ({label}): secret value not printed", SECRET_VALUE not in combined)
            check(f"redaction ({label}): denylist token value not printed", DENYLIST_TOKEN not in combined)
            check(f"redaction ({label}): user path fragment not printed", LEAK_PATH_FRAGMENT not in combined)

    # Line content used across 8b-8g - fingerprint is computed the same way
    # the scanner itself computes it, matching what a real reviewer would
    # copy from the scanner's own output, not an independently-guessed value.
    KEYTAR_LINE = "setPassword(service: string, account: string, password: string): Promise<void>;"
    keytar_fp = eif_privacy_scan.compute_fingerprint("secret_shaped:password_assignment", "keytar.d.ts", KEYTAR_LINE)

    # --- 8b. Suppressions: exact (rule, path, fingerprint) match suppresses, exit 0, reported separately ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "keytar.d.ts").write_text(KEYTAR_LINE + "\n", encoding="utf-8")
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "config.yaml").write_text(
            "privacy:\n  suppressions:\n"
            "    - rule: \"secret_shaped:password_assignment\"\n"
            "      path: \"keytar.d.ts\"\n"
            f"      fingerprint: \"{keytar_fp}\"\n"
            "      rationale: \"TS interface signature, not a real value.\"\n"
            "      reviewed: \"2026-07-15\"\n",
            encoding="utf-8",
        )
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        check("suppression: exact (rule,path,fingerprint) match -> exit 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("suppression: finding removed from active top-level keys", "password_assignment" not in result.get("secret_shaped", {}))
        check("suppression: finding present under suppressed instead", "password_assignment" in result.get("suppressed", {}).get("secret_shaped", {}))
        check("suppression: no hygiene issues for a suppression that matched", result.get("suppression_issues") == [])
        check("suppression: the finding's own fingerprint is echoed in output (safe - one-way hash)",
             result.get("suppressed", {}).get("secret_shaped", {}).get("password_assignment", [{}])[0].get("fingerprint") == keytar_fp)

    # --- 8c. Suppressions: wrong path does not suppress; unsuppressed finding still fails ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "keytar.d.ts").write_text(KEYTAR_LINE + "\n", encoding="utf-8")
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "config.yaml").write_text(
            "privacy:\n  suppressions:\n"
            "    - rule: \"secret_shaped:password_assignment\"\n"
            "      path: \"some/other/file.ts\"\n"
            f"      fingerprint: \"{keytar_fp}\"\n"
            "      rationale: \"Does not apply to keytar.d.ts.\"\n"
            "      reviewed: \"2026-07-15\"\n",
            encoding="utf-8",
        )
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        check("suppression: wrong path -> finding stays active", "password_assignment" in result.get("secret_shaped", {}))
        check("suppression: wrong path -> exit 1 (unsuppressed finding + hygiene issue both fail closed)", proc.returncode == 1)
        check("suppression: wrong path -> reported as a hygiene issue (never matched anything)",
             any("no longer matches" in h["issue"] for h in result.get("suppression_issues", [])))

    # --- 8c2. Suppressions: right rule+path but WRONG fingerprint (finding-
    # specific, independent-review core requirement) does not suppress. ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "keytar.d.ts").write_text(KEYTAR_LINE + "\n", encoding="utf-8")
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "config.yaml").write_text(
            "privacy:\n  suppressions:\n"
            "    - rule: \"secret_shaped:password_assignment\"\n"
            "      path: \"keytar.d.ts\"\n"
            "      fingerprint: \"0000000000000000\"\n"  # right rule+path, deliberately wrong fingerprint
            "      rationale: \"Wrong fingerprint on purpose.\"\n"
            "      reviewed: \"2026-07-15\"\n",
            encoding="utf-8",
        )
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        check("suppression: right rule+path, wrong fingerprint -> finding stays active", "password_assignment" in result.get("secret_shaped", {}))
        check("suppression: right rule+path, wrong fingerprint -> exit 1", proc.returncode == 1)

    # --- 8d. Suppressions: expired -> finding reactivates, hygiene issue fires ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "keytar.d.ts").write_text(KEYTAR_LINE + "\n", encoding="utf-8")
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "config.yaml").write_text(
            "privacy:\n  suppressions:\n"
            "    - rule: \"secret_shaped:password_assignment\"\n"
            "      path: \"keytar.d.ts\"\n"
            f"      fingerprint: \"{keytar_fp}\"\n"
            "      rationale: \"Reviewed, but the review window closed.\"\n"
            "      reviewed: \"2020-01-01\"\n"
            "      expires: \"2020-06-01\"\n",
            encoding="utf-8",
        )
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        check("suppression: expired -> finding reactivates (back in active findings)", "password_assignment" in result.get("secret_shaped", {}))
        check("suppression: expired -> exit 1", proc.returncode == 1)
        check("suppression: expired -> hygiene issue says 'expired'",
             any(h["issue"] == "expired" for h in result.get("suppression_issues", [])))

    # --- 8f. Same rule+path, DIFFERENT line/fingerprint - a second, real
    # finding must NOT be hidden by a suppression that reviewed a different
    # line in the same file (independent-review core requirement). ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        real_secret_line = f"const debugPassword = \"{SECRET_VALUE}\";"
        (tmp / "keytar.d.ts").write_text(KEYTAR_LINE + "\n" + real_secret_line + "\n", encoding="utf-8")
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "config.yaml").write_text(
            "privacy:\n  suppressions:\n"
            "    - rule: \"secret_shaped:password_assignment\"\n"
            "      path: \"keytar.d.ts\"\n"
            f"      fingerprint: \"{keytar_fp}\"\n"
            "      rationale: \"Only the TS interface signature is reviewed here.\"\n"
            "      reviewed: \"2026-07-15\"\n",
            encoding="utf-8",
        )
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        active_pw = result.get("secret_shaped", {}).get("password_assignment", [])
        check("regression: second real finding in the SAME file (different fingerprint) stays active", len(active_pw) == 1, str(active_pw))
        check("regression: exit code is still 1 (one suppressed finding does not hide a new one in the same file)", proc.returncode == 1)
        suppressed_pw = result.get("suppressed", {}).get("secret_shaped", {}).get("password_assignment", [])
        check("regression: the reviewed interface-signature finding IS suppressed", len(suppressed_pw) == 1)

    # --- 8g. Invalid suppression config fails loudly, does not silently skip ---
    for label, bad_suppression_yaml in (
        ("unknown_rule", "    - rule: \"totally_made_up_rule\"\n      path: \"x.ts\"\n      fingerprint: \"0000000000000000\"\n      rationale: \"r\"\n      reviewed: \"2026-07-15\"\n"),
        ("glob_path", "    - rule: \"secret_shaped:password_assignment\"\n      path: \"src/**/*.ts\"\n      fingerprint: \"0000000000000000\"\n      rationale: \"r\"\n      reviewed: \"2026-07-15\"\n"),
        ("bad_reviewed_date", "    - rule: \"secret_shaped:password_assignment\"\n      path: \"x.ts\"\n      fingerprint: \"0000000000000000\"\n      rationale: \"r\"\n      reviewed: \"not-a-date\"\n"),
        ("bad_expires_date", "    - rule: \"secret_shaped:password_assignment\"\n      path: \"x.ts\"\n      fingerprint: \"0000000000000000\"\n      rationale: \"r\"\n      reviewed: \"2026-07-15\"\n      expires: \"15/10/2026\"\n"),
        ("short_fingerprint", "    - rule: \"secret_shaped:password_assignment\"\n      path: \"x.ts\"\n      fingerprint: \"abc\"\n      rationale: \"r\"\n      reviewed: \"2026-07-15\"\n"),
    ):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            make_git_repo(tmp)
            (tmp / "clean.md").write_text("Nothing sensitive.\n", encoding="utf-8")
            os.makedirs(tmp / ".eif", exist_ok=True)
            (tmp / ".eif" / "config.yaml").write_text("privacy:\n  suppressions:\n" + bad_suppression_yaml, encoding="utf-8")
            git_add(tmp)
            proc = run(["--repo", str(tmp), "--json"])
            check(f"invalid config ({label}): exits 1 (fails loudly)", proc.returncode == 1, proc.stdout + proc.stderr)
            check(f"invalid config ({label}): stdout has no JSON (refused before scanning, not a partial result)", proc.stdout.strip() == "")
            check(f"invalid config ({label}): stderr explains what's wrong", "INVALID" in proc.stderr, proc.stderr)

    # --- 8e. Suppression rationale/path values are never treated as the matched secret - redaction still holds ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "combo.md").write_text(f"api_key: {SECRET_VALUE}\n", encoding="utf-8")
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "config.yaml").write_text(
            "privacy:\n  suppressions:\n"
            "    - rule: \"secret_shaped:api_key_assignment\"\n"
            "      path: \"unrelated.md\"\n"
            "      fingerprint: \"0000000000000000\"\n"
            "      rationale: \"Unrelated suppression, present to prove redaction still holds.\"\n"
            "      reviewed: \"2026-07-15\"\n",
            encoding="utf-8",
        )
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        check("suppression config present: secret value still never printed", SECRET_VALUE not in proc.stdout)

    # --- 8. .example files are not specially excluded (only the scanner's own source is) ---
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "config.yaml.example").write_text(f"api_key: {SECRET_VALUE}\n", encoding="utf-8")
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        result = json.loads(proc.stdout)
        check(".example files are scanned normally, not excluded", "api_key_assignment" in result["secret_shaped"])

    # --- 8h. Suppression-config STATE distinctions (independent-review
    # finding): a broken EXISTING config must fail loudly, never be treated
    # as an empty suppression list (which would let a finding the operator
    # believes is suppressed through, or silently ignore a config that isn't
    # being read at all). Four states, one behavior each. ---
    # (i) config ABSENT -> scan runs normally, unsuppressed
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "clean.md").write_text("Nothing sensitive.\n", encoding="utf-8")
        git_add(tmp)  # no .eif/config.yaml at all
        proc = run(["--repo", str(tmp), "--json"])
        check("config absent: scan continues, exit 0", proc.returncode == 0, proc.stdout + proc.stderr)

    # (ii) config exists + VALID (no privacy key) -> scan runs normally
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "clean.md").write_text("Nothing sensitive.\n", encoding="utf-8")
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "config.yaml").write_text("project:\n  name: p\n", encoding="utf-8")
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        check("config valid (no privacy key): scan continues, exit 0", proc.returncode == 0, proc.stdout + proc.stderr)

    # (iii) config exists + INVALID YAML -> exit 1, no JSON, clear message
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "clean.md").write_text("Nothing sensitive.\n", encoding="utf-8")
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "config.yaml").write_text("privacy:\n  suppressions: 'unterminated\n", encoding="utf-8")
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        check("config invalid YAML: exits 1 (not a silent empty-suppressions pass)", proc.returncode == 1, proc.stdout + proc.stderr)
        check("config invalid YAML: no JSON on stdout (refused before scanning)", proc.stdout.strip() == "")
        check("config invalid YAML: stderr says it cannot load the suppression config", "cannot load suppression config" in proc.stderr, proc.stderr)

    # (iv) config exists but is NOT A MAPPING (top-level list) -> exit 1
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        make_git_repo(tmp)
        (tmp / "clean.md").write_text("Nothing sensitive.\n", encoding="utf-8")
        os.makedirs(tmp / ".eif", exist_ok=True)
        (tmp / ".eif" / "config.yaml").write_text("- not\n- a\n- mapping\n", encoding="utf-8")
        git_add(tmp)
        proc = run(["--repo", str(tmp), "--json"])
        check("config not-a-mapping: exits 1", proc.returncode == 1, proc.stdout + proc.stderr)
        check("config not-a-mapping: stderr says it cannot load the suppression config", "cannot load suppression config" in proc.stderr, proc.stderr)

    # (v) PyYAML UNAVAILABLE while config EXISTS -> hard error (tested at the
    # function level: forcing a clean-runner uninstall in a subprocess is not
    # worth it, but the code path must be exercised). Absent config with no
    # PyYAML still returns [] (no error).
    saved_yaml = eif_privacy_scan.yaml
    try:
        eif_privacy_scan.yaml = None
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "config.yaml"
            cfg.write_text("privacy:\n  suppressions: []\n", encoding="utf-8")
            try:
                eif_privacy_scan.load_suppressions(cfg)
                check("PyYAML unavailable + config exists: raises (does not silently skip)", False)
            except eif_privacy_scan.SuppressionConfigError as e:
                check("PyYAML unavailable + config exists: raises SuppressionConfigError", True)
                check("PyYAML unavailable: message names the missing dependency", "PyYAML" in str(e), str(e))
            check("PyYAML unavailable + config absent: still returns [] (no error)",
                  eif_privacy_scan.load_suppressions(Path(td) / "does-not-exist.yaml") == [])
    finally:
        eif_privacy_scan.yaml = saved_yaml

    total_checks = failures
    print(f"\ntest_privacy_scan: {'ALL PASSED' if not failures else str(len(failures)) + ' FAILED'}")
    if failures:
        print("Failed checks:", ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
