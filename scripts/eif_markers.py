#!/usr/bin/env python3
"""Shared marker-safety logic for EIF-managed blocks (CLAUDE.md, .gitignore).

A managed block is delimited by a BEGIN/END marker pair. The naive approach
- `text.index(BEGIN)` / `text.index(END)` - silently mishandles anything
that isn't exactly one well-formed pair: a missing partner, reversed order
(END before BEGIN), duplicate BEGIN or END lines, or nested markers all
produce corrupted output with no error (confirmed by direct reproduction
during the round-3 review - reversed markers duplicated project content
into the output silently).

find_managed_block() is the single place that decides whether an existing
file's markers are safe to merge into. Callers must not write anything if it
raises MarkerConflict.
"""
from __future__ import annotations


class MarkerConflict(Exception):
    """Existing markers are missing a partner, reversed, or duplicated -
    refuse to merge rather than silently corrupt the file."""


def find_managed_block(text: str, begin_marker: str, end_marker: str) -> tuple[int, int] | None:
    """Return (begin_index, index_just_after_end_marker) for a single,
    well-formed BEGIN...END pair, or None if there is no managed block at
    all (zero of both markers - a fresh file to append to).

    Raises MarkerConflict for any other shape: a duplicate BEGIN or END, a
    marker with no partner, or END appearing before BEGIN (reversed).
    """
    begin_count = text.count(begin_marker)
    end_count = text.count(end_marker)
    if begin_count == 0 and end_count == 0:
        return None
    if begin_count != 1 or end_count != 1:
        raise MarkerConflict(
            f"expected exactly one {begin_marker!r} and one {end_marker!r}, "
            f"found {begin_count} BEGIN and {end_count} END marker(s) - "
            f"refusing to merge (this would silently corrupt content)"
        )
    begin_idx = text.index(begin_marker)
    end_idx = text.index(end_marker)
    if end_idx < begin_idx:
        raise MarkerConflict(
            f"{end_marker!r} appears before {begin_marker!r} - markers are "
            f"reversed, refusing to merge"
        )
    return begin_idx, end_idx + len(end_marker)


def render_merged_content(existing_text: str | None, managed_block: str,
                          begin_marker: str, end_marker: str,
                          new_file_footer: str = "") -> tuple[str, str]:
    """Compute the merged text for a managed block. Returns (new_text,
    action) where action is 'create' | 'append-block' | 'update-block'.

    Raises MarkerConflict (propagated from find_managed_block) if the
    existing file's markers are malformed - the caller must not write
    anything in that case; the conflict must be reported, not silently
    resolved by picking a side.
    """
    if existing_text is None:
        return managed_block + new_file_footer, "create"
    found = find_managed_block(existing_text, begin_marker, end_marker)
    if found is None:
        return existing_text.rstrip("\n") + "\n\n" + managed_block + "\n", "append-block"
    begin_idx, end_idx = found
    head = existing_text[:begin_idx]
    tail = existing_text[end_idx:]
    return head + managed_block + tail, "update-block"


def check_marker_integrity(text: str, begin_marker: str, end_marker: str) -> list[str]:
    """Non-raising variant for read-only integrity checks (eif_verify_runtime.py)
    - returns a list of problems (empty = fine, including the 'no block at
    all yet' case, which is not itself a problem)."""
    try:
        find_managed_block(text, begin_marker, end_marker)
        return []
    except MarkerConflict as e:
        return [str(e)]
