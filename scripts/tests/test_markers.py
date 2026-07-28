#!/usr/bin/env python3
"""Tests for eif_markers.py: marker safety (round-3 review, Finding G).

Every malformed-marker shape must raise MarkerConflict and leave the merge
un-attempted - the naive substring approach silently corrupted content for
exactly these shapes (confirmed by direct reproduction: reversed markers
duplicated project content into the merged output with no error at all).

Usage:
    python scripts/tests/test_markers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eif_markers import find_managed_block, render_merged_content, MarkerConflict  # noqa: E402

BEGIN = "<!-- EIF:BEGIN"
END = "<!-- EIF:END -->"
BLOCK = f"{BEGIN} block -->\nmanaged content\n{END}\n"


def check(name: str, condition: bool, detail: str = "") -> bool:
    condition = bool(condition)
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def expect_conflict(name: str, text: str) -> bool:
    try:
        find_managed_block(text, BEGIN, END)
        return check(name, False, "expected MarkerConflict, none raised")
    except MarkerConflict:
        return check(name, True)


def main() -> int:
    results = []

    # --- No markers at all: valid "fresh file" case, not a conflict ---
    results.append(check("no markers at all -> None (not a conflict, means 'append')",
                         find_managed_block("just some text\n", BEGIN, END) is None))

    # --- Exactly one well-formed pair: valid ---
    ok_text = f"before\n{BEGIN} x -->\nmanaged\n{END}\nafter\n"
    found = find_managed_block(ok_text, BEGIN, END)
    results.append(check("well-formed single pair returns real indices", found is not None and found[0] < found[1]))

    # --- Malformed shapes: every one must raise, not silently pick a side ---
    results.append(expect_conflict("BEGIN with no END raises", f"before\n{BEGIN} x -->\nmanaged\nafter\n"))
    results.append(expect_conflict("END with no BEGIN raises", f"before\n{END}\nafter\n"))
    results.append(expect_conflict("reversed order (END before BEGIN) raises",
                                   f"{END}\nstray content\n{BEGIN} x -->\n"))
    results.append(expect_conflict("duplicate BEGIN raises",
                                   f"{BEGIN} a -->\n{BEGIN} b -->\nmanaged\n{END}\n"))
    results.append(expect_conflict("duplicate END raises",
                                   f"{BEGIN} a -->\nmanaged\n{END}\n{END}\n"))
    results.append(expect_conflict("nested markers (BEGIN...BEGIN...END...END) raises",
                                   f"{BEGIN} outer -->\n{BEGIN} inner -->\nmanaged\n{END}\n{END}\n"))

    # --- render_merged_content: valid shapes ---
    new_text, action = render_merged_content(None, BLOCK, BEGIN, END, new_file_footer="\nfooter\n")
    results.append(check("render_merged_content: no existing file -> create", action == "create" and BLOCK in new_text and "footer" in new_text))

    appended, action2 = render_merged_content("existing project content\n", BLOCK, BEGIN, END)
    results.append(check("render_merged_content: existing file, no markers -> append, content preserved",
                         action2 == "append-block" and "existing project content" in appended and BLOCK.strip() in appended))

    existing_with_block = f"head text\n{BEGIN} old -->\nold managed content\n{END}\ntail text\n"
    updated, action3 = render_merged_content(existing_with_block, BLOCK, BEGIN, END)
    results.append(check("render_merged_content: existing well-formed block -> update, head/tail preserved",
                         action3 == "update-block" and "head text" in updated and "tail text" in updated
                         and "old managed content" not in updated and "managed content" in updated))

    # The tail already contains the line break immediately after END. A
    # canonical managed block contains one too, so an update must collapse
    # that duplicated boundary and remain byte-identical on every rerun.
    expected_lf = f"head text\n{BLOCK}tail text\n"
    updated_lf, action4 = render_merged_content(expected_lf, BLOCK, BEGIN, END)
    rerun_lf, action5 = render_merged_content(updated_lf, BLOCK, BEGIN, END)
    results.append(check(
        "render_merged_content: LF update does not grow a trailing blank line",
        action4 == "update-block" and updated_lf == expected_lf,
        repr(updated_lf),
    ))
    results.append(check(
        "render_merged_content: repeated LF update is byte-idempotent",
        action5 == "update-block" and rerun_lf == expected_lf,
        repr(rerun_lf),
    ))

    block_crlf = BLOCK.replace("\n", "\r\n")
    expected_crlf = f"head text\r\n{block_crlf}tail text\r\n"
    updated_crlf, action6 = render_merged_content(expected_crlf, block_crlf, BEGIN, END)
    rerun_crlf, action7 = render_merged_content(updated_crlf, block_crlf, BEGIN, END)
    results.append(check(
        "render_merged_content: repeated CRLF update is byte-idempotent",
        action6 == action7 == "update-block"
        and updated_crlf == expected_crlf
        and rerun_crlf == expected_crlf,
        repr(rerun_crlf),
    ))

    # --- render_merged_content: malformed shapes raise, caller writes nothing ---
    try:
        render_merged_content(f"{END}\nstray\n{BEGIN} x -->\n", BLOCK, BEGIN, END)
        results.append(check("render_merged_content propagates MarkerConflict on reversed markers", False))
    except MarkerConflict:
        results.append(check("render_merged_content propagates MarkerConflict on reversed markers", True))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_markers: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
