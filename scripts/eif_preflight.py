#!/usr/bin/env python3
"""Adoption preflight for eif_init.py: detect pre-existing project state
BEFORE any write, and classify each observation OK / WARN / STOP.

This exists because a naive bootstrap onto an EXISTING repository (as
opposed to a genuinely empty greenfield one) can silently do the wrong
thing even when every individual write is "safe" in isolation:
appending a block that declares itself the project's authority into a
CLAUDE.md that already has its own governance is technically a clean
marker-safe append (scripts/eif_markers.py has no complaint) and still
the wrong outcome - a second, competing authority statement the project
owner never asked for. STOP exists to make that case impossible to sail
past silently; WARN exists for things worth knowing but not blocking.

A STOP here means eif_init.py must not write ANYTHING - not "write
everything except the risky part." Resolving a STOP means the caller
makes an explicit decision (--adoption-mode coexist, or --adoption-mode
greenfield to explicitly proceed anyway) and re-runs; it is never
auto-resolved by picking a default.

Usage (library only - eif_init.py is the caller; no standalone CLI here,
matching eif_markers.py's shape):
    from eif_preflight import run_preflight
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from eif_markers import find_managed_block, MarkerConflict

# Below this many stripped characters, existing entrypoint content is not
# treated as "governance" - a near-empty or placeholder file is not worth
# a STOP. Chosen well below any real rules section (compare: the shortest
# real per-project CLAUDE.md content seen in framework testing is several
# hundred characters).
GOVERNANCE_CONTENT_THRESHOLD = 40


@dataclass
class PreflightCheck:
    level: str  # "OK" | "WARN" | "STOP"
    message: str


@dataclass
class PreflightReport:
    checks: list[PreflightCheck] = field(default_factory=list)

    def add(self, level: str, message: str) -> None:
        self.checks.append(PreflightCheck(level, message))

    @property
    def has_stop(self) -> bool:
        return any(c.level == "STOP" for c in self.checks)

    def render(self, prefix: str = "") -> list[str]:
        return [f"{prefix}{c.level:<4} {c.message}" for c in self.checks]


def run_preflight(
    *,
    mode: str,
    entrypoint_name: str,
    existing_entry_text: str | None,
    existing_gitignore_text: str | None,
    knowledge_root_path: Path,
    knowledge_root_configured: str,
    adoption_mode_explicit: str | None,
    begin_marker: str,
    end_marker: str,
    gitignore_begin: str,
    gitignore_end: str,
) -> PreflightReport:
    """Build the structured OK/WARN/STOP report. Read-only - never writes.

    Called for both --dry-run (to print) and a real run (to enforce
    report.has_stop as a hard exit before any staging begins) - the same
    function, so dry-run's plan cannot drift from what a real run
    actually enforces.
    """
    report = PreflightReport()

    # --- Existing governance in the entrypoint file ---
    has_existing_markers = False
    if existing_entry_text is not None:
        try:
            has_existing_markers = find_managed_block(existing_entry_text, begin_marker, end_marker) is not None
        except MarkerConflict:
            # Surfaced below as its own STOP; do not also double-count it
            # as "existing governance without markers".
            has_existing_markers = True

        substantial = len(existing_entry_text.strip()) >= GOVERNANCE_CONTENT_THRESHOLD
        if substantial and not has_existing_markers:
            if mode == "init" and adoption_mode_explicit is None:
                report.add(
                    "STOP",
                    f"{entrypoint_name} already has substantial content and no EIF markers yet, but "
                    f"no --adoption-mode was given. Pass --adoption-mode coexist (the generated block "
                    f"will not claim sole authority and will defer to your existing rules) or "
                    f"--adoption-mode greenfield (explicit override) before proceeding - refusing to "
                    f"append a competing authority block silently.",
                )
            elif adoption_mode_explicit == "coexist":
                report.add(
                    "OK",
                    f"{entrypoint_name} has existing content; --adoption-mode coexist is set - the "
                    f"generated block will defer to it, not compete with it.",
                )
            elif adoption_mode_explicit == "greenfield":
                report.add(
                    "WARN",
                    f"{entrypoint_name} has existing content, but --adoption-mode greenfield was "
                    f"explicitly passed - proceeding as an explicit override, not a default.",
                )
            else:
                # mode == "upgrade"/"reconfigure" with existing content and no markers is unusual
                # (an upgrade normally implies markers already exist) - surfaced, not silently OK.
                report.add(
                    "WARN",
                    f"{entrypoint_name} has substantial existing content and no EIF markers, on a "
                    f"{mode} run - verify this is expected.",
                )
        elif substantial and has_existing_markers:
            report.add("OK", f"{entrypoint_name}: existing EIF-managed block found, will refresh in place.")
        elif not substantial:
            report.add("OK", f"{entrypoint_name}: no substantial pre-existing content, safe to create/append.")
    else:
        report.add("OK", f"{entrypoint_name}: does not exist yet, will be created.")

    # --- Malformed markers (surfaced here too, not only as eif_init's later hard failure) ---
    for label, text, begin, end in (
        (entrypoint_name, existing_entry_text, begin_marker, end_marker),
        (".gitignore", existing_gitignore_text, gitignore_begin, gitignore_end),
    ):
        if text is None:
            continue
        try:
            find_managed_block(text, begin, end)
        except MarkerConflict as e:
            report.add("STOP", f"{label}: malformed EIF markers, refusing to write - {e}")

    # --- Knowledge root ---
    if knowledge_root_path.is_dir():
        report.add("OK", f"knowledge root '{knowledge_root_configured}' exists - index/search will use it as configured.")
    else:
        report.add(
            "WARN",
            f"knowledge root '{knowledge_root_configured}' does not exist yet - index generation stays "
            f"inert (no directory is created silently) until one exists at that configured path.",
        )

    return report
