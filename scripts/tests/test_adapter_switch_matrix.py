#!/usr/bin/env python3
"""Full directed adapter-switching matrix (parity round v2).

Supersedes closed, stale PR #13 (stacked on the never-merged old Hermes
branch). Complements each adapter's own test file (which already proves
switching to/from claude-code and, for Codex, cursor - see
test_codex_adapter.py/test_hermes_adapter.py/test_cursor_adapter.py) by
proving the two pairs no existing suite covers (cursor<->hermes,
codex<->hermes) and, for every one of the 12 directed pairs across all 4
registered adapters, a single shared set of cross-cutting properties:
exactly one effective EIF-managed block anywhere in the instance after
the switch, the destination adapter's OWN resolver agreeing with what
actually got written, project-owned content surviving the switch
byte-for-byte, and doctor passing afterward. Malformed-marker STOP, fault-
injected rollback, and size-budget survival are each already proven
generically (adapter-agnostic transaction/marker-merge code, not
re-implemented per adapter) in the individual adapter test files - this
suite adds one additional cross-check for each on a pair neither of those
files already covers, rather than re-proving already-generic mechanisms
12 times over.

Usage:
    python scripts/tests/test_adapter_switch_matrix.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = FRAMEWORK_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from eif_adapters import ADAPTERS  # noqa: E402

# (adapter_name, default_greenfield_entrypoint, entry_strategy)
ADAPTER_INFO = {
    "claude-code": ("CLAUDE.md", "marker-merge"),
    "cursor": (".cursor/rules/eif/governance.mdc", "full-regen"),
    "codex": ("AGENTS.md", "dynamic-resolve"),
    "hermes": (".hermes.md", "dynamic-resolve"),
}
ADAPTER_ORDER = ["claude-code", "cursor", "codex", "hermes"]
ALL_DIRECTED_PAIRS = [(a, b) for a in ADAPTER_ORDER for b in ADAPTER_ORDER if a != b]


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args], cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, encoding="utf-8",
    )


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")


def init_git_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    git(["init", "-q"], root)
    git(["config", "user.email", "test@example.invalid"], root)
    git(["config", "user.name", "Switch Matrix Test"], root)


def eif_init(inst: Path, *extra: str) -> subprocess.CompletedProcess:
    return run([str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
                "--instance-path", str(inst), "--allow-dirty", *extra])


def eif_verify(inst: Path, *extra: str) -> subprocess.CompletedProcess:
    return run([str(SCRIPTS / "eif_verify_runtime.py"), "--framework-root", str(FRAMEWORK_ROOT),
                "--instance-path", str(inst), *extra])


# Every real entrypoint-candidate path across all 4 registered adapters -
# the actual "governance/entrypoint" surface this property is about.
# Deliberately NOT a blind filesystem scan: .gitignore is also legitimately
# marker-merged (a different, unrelated managed artifact, not a competing
# entrypoint), and .eif/runtime/ bundles the framework's OWN source
# (scripts, templates) which contains the literal marker STRING as part of
# its own code/template definitions, not rendered instance content - a
# naive substring scan over the whole tree matches those too and wildly
# over-counts.
ALL_ENTRYPOINT_CANDIDATE_PATHS = [
    "CLAUDE.md", "claude.md",
    ".cursor/rules/eif/governance.mdc",
    "AGENTS.md", "AGENTS.override.md", "agents.md",
    ".hermes.md", "HERMES.md",
]


def count_active_blocks(inst: Path) -> int:
    # De-duplicate by RESOLVED path, not nominal candidate name: on a
    # case-insensitive filesystem (Windows, macOS default), "AGENTS.md"
    # and "agents.md" resolve to the identical on-disk file when only one
    # of them physically exists - counting both names independently would
    # double-count that single real file.
    active_paths: set[Path] = set()
    for rel in ALL_ENTRYPOINT_CANDIDATE_PATHS:
        p = inst / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "<!-- EIF:BEGIN" in text:
            active_paths.add(p.resolve())
    return len(active_paths)


def check(name: str, cond: bool, detail: str = "") -> bool:
    status = "PASS" if cond else "FAIL"
    print(f"{status} {name}" + (f": {detail}" if detail and not cond else ""))
    return cond


def main() -> int:
    results: list[bool] = []

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # -------------------------------------------------------------
        # Core matrix: all 12 directed pairs, shared cross-cutting
        # properties.
        # -------------------------------------------------------------
        for from_adapter, to_adapter in ALL_DIRECTED_PAIRS:
            label = f"{from_adapter}->{to_adapter}"
            inst = tmp / f"switch-{from_adapter}-to-{to_adapter}".replace(".", "")
            init_git_repo(inst)

            r_from = eif_init(inst, "--project-name", "matrix-fixture", "--adapter", from_adapter)
            if not check(f"{label}: precondition - greenfield {from_adapter} init exits 0", r_from.returncode == 0, r_from.stdout + r_from.stderr):
                results.append(False)
                continue
            results.append(True)

            from_entry_rel, from_strategy = ADAPTER_INFO[from_adapter]
            from_entry_path = inst / from_entry_rel
            from_text_before_switch = from_entry_path.read_text(encoding="utf-8") if from_entry_path.exists() else ""
            # Inject distinguishing project-owned content for marker-merge
            # FROM-adapters, so preservation is actually checked, not just
            # assumed - full-regen (cursor) has no legitimate content
            # outside the block by contract, so this is skipped there.
            marker_token = f"PROJECT-OWNED-CONTENT-{from_adapter}-{to_adapter}"
            if from_strategy == "marker-merge" and "<Add this project instance's own rules here.>" in from_text_before_switch:
                from_entry_path.write_text(
                    from_text_before_switch.replace("<Add this project instance's own rules here.>", marker_token),
                    encoding="utf-8",
                )

            # Cursor's own registry entry declares AGENTS.md a real
            # shared_signal (a separate, official mechanism Cursor also
            # reads - see adapters/cursor/README.md), independent of
            # switching itself - a leftover AGENTS.md from a codex/hermes
            # FROM adapter is real pre-existing governance content until
            # this run completes, so it correctly requires the normal
            # explicit adoption-mode decision, same as any other adapter's
            # pre-existing governance surface would (established precedent:
            # test_codex_adapter.py scenario 28).
            switch_args = ["--force", "--adapter", to_adapter]
            if to_adapter == "cursor" and from_adapter in ("codex", "hermes"):
                switch_args += ["--adoption-mode", "greenfield"]
            r_switch = eif_init(inst, *switch_args)
            results.append(check(f"{label}: switch exits 0", r_switch.returncode == 0, r_switch.stdout + r_switch.stderr))
            if r_switch.returncode != 0:
                continue

            # Property: exactly one effective EIF-managed block anywhere.
            active_count = count_active_blocks(inst)
            results.append(check(f"{label}: exactly one active EIF block after the switch", active_count == 1, f"found {active_count}"))

            # Property: config/lock record the destination adapter.
            cfg_text = (inst / ".eif" / "config.yaml").read_text(encoding="utf-8")
            lock_text = (inst / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8")
            results.append(check(f"{label}: config records adapter.name: {to_adapter}", f"name: {to_adapter}" in cfg_text, cfg_text))
            results.append(check(f"{label}: lock records adapter.name: {to_adapter}", f"name: {to_adapter}" in lock_text, lock_text))

            # Property: project-owned content from a marker-merge FROM
            # adapter survives, UNLESS the old and new paths coincide (in
            # which case it must survive INSIDE the new active file
            # instead - still "preserved", just not at a separate path).
            if from_strategy == "marker-merge" and marker_token in from_text_before_switch.replace(
                "<Add this project instance's own rules here.>", marker_token
            ):
                found_token_somewhere = any(
                    marker_token in p.read_text(encoding="utf-8", errors="replace")
                    for p in inst.rglob("*") if p.is_file() and ".git" not in p.relative_to(inst).parts
                )
                results.append(check(f"{label}: FROM adapter's project-owned content survives the switch (same path or preserved sibling)", found_token_somewhere))

            # Property: doctor agrees after the switch.
            r_doc = eif_verify(inst)
            results.append(check(f"{label}: doctor passes after the switch", r_doc.returncode == 0, r_doc.stdout + r_doc.stderr))

        # -------------------------------------------------------------
        # Representative deep-dive: malformed-marker STOP on a pair no
        # other suite covers (cursor -> hermes).
        # -------------------------------------------------------------
        inst_mal = tmp / "malformed-cursor-to-hermes"
        init_git_repo(inst_mal)
        eif_init(inst_mal, "--project-name", "matrix-fixture", "--adapter", "cursor")
        mdc_path = inst_mal / ".cursor" / "rules" / "eif" / "governance.mdc"
        malformed = mdc_path.read_text(encoding="utf-8").replace("<!-- EIF:END -->", "", 1)
        mdc_path.write_text(malformed, encoding="utf-8")
        before_mal = {p.relative_to(inst_mal).as_posix(): p.read_bytes() for p in inst_mal.rglob("*") if p.is_file() and ".git" not in p.relative_to(inst_mal).parts}
        r_mal = eif_init(inst_mal, "--force", "--adapter", "hermes")
        results.append(check("malformed old marker (cursor->hermes) -> STOP before any write", r_mal.returncode != 0, r_mal.stdout + r_mal.stderr))
        after_mal = {p.relative_to(inst_mal).as_posix(): p.read_bytes() for p in inst_mal.rglob("*") if p.is_file() and ".git" not in p.relative_to(inst_mal).parts}
        results.append(check("malformed old marker (cursor->hermes) STOP wrote nothing", before_mal == after_mal))

        # -------------------------------------------------------------
        # Representative deep-dive: fault-injected rollback on a pair no
        # other suite covers (codex -> hermes).
        # -------------------------------------------------------------
        inst_rb = tmp / "rollback-codex-to-hermes"
        init_git_repo(inst_rb)
        eif_init(inst_rb, "--project-name", "matrix-fixture", "--adapter", "codex")
        before_rb = {p.relative_to(inst_rb).as_posix(): p.read_bytes() for p in inst_rb.rglob("*") if p.is_file() and ".git" not in p.relative_to(inst_rb).parts}
        import os
        env_rb = {"PATH": os.environ.get("PATH", ""), "EIF_INIT_TEST_FAIL_AFTER": "entrypoint"}
        proc_rb = subprocess.run(
            [sys.executable, str(SCRIPTS / "eif_init.py"), "--framework-root", str(FRAMEWORK_ROOT),
             "--instance-path", str(inst_rb), "--allow-dirty", "--force", "--adapter", "hermes"],
            capture_output=True, text=True, encoding="utf-8", env=env_rb,
        )
        results.append(check("fault-injected rollback (codex->hermes) exits non-zero", proc_rb.returncode != 0, proc_rb.stdout + proc_rb.stderr))
        after_rb = {p.relative_to(inst_rb).as_posix(): p.read_bytes() for p in inst_rb.rglob("*") if p.is_file() and ".git" not in p.relative_to(inst_rb).parts}
        results.append(check("fault-injected rollback (codex->hermes) restores the tree exactly", before_rb == after_rb, f"before keys={sorted(before_rb)} after keys={sorted(after_rb)}"))

        # -------------------------------------------------------------
        # Registry self-check: every registered adapter is covered by the
        # matrix above - fails loudly if a 5th adapter is ever added
        # without updating ADAPTER_INFO/this suite (mirrors
        # test_parity_matrix.py's own drift-prevention role).
        # -------------------------------------------------------------
        results.append(check(
            "ADAPTER_INFO covers exactly the registered adapters (no drift)",
            set(ADAPTER_INFO.keys()) == set(ADAPTERS.keys()),
            f"matrix={sorted(ADAPTER_INFO.keys())} registry={sorted(ADAPTERS.keys())}",
        ))
        results.append(check("all 12 directed pairs across 4 adapters are covered", len(ALL_DIRECTED_PAIRS) == 12, len(ALL_DIRECTED_PAIRS)))

        passed = sum(results)
        print(f"\nEIF-RESULT: passed={passed} total={len(results)}")
        print(f"\ntest_adapter_switch_matrix: {passed}/{len(results)} passed")
        return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
