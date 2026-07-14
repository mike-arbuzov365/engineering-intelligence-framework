#!/usr/bin/env python3
"""Check whether a PR body has a meaningfully completed Knowledge Delta.

The PR template (.github/pull_request_template.md) always contains a
'## Knowledge Delta' heading with empty '### Added'/'### Changed'/'### Not
yet ratified' subsections, so a bare "does '## Knowledge Delta' appear in
the body" check always passes, even for an untouched template. This script
distinguishes three cases:

  meaningful  - a '## Knowledge Delta' section exists and has real content
                under it (something other than the empty subheadings/HTML
                comments the template ships with).
  mechanical  - the exact '<!-- no-knowledge-delta: mechanical task -->'
                marker is present (checked first - short-circuits).
  empty       - neither: either no 'Knowledge Delta' heading at all, or
                the section is present but contains only the untouched
                template skeleton.

Usage:
    python scripts/eif_check_knowledge_delta.py --body-file PATH
    python scripts/eif_check_knowledge_delta.py --body-stdin < body.txt
    echo "$PR_BODY" | python scripts/eif_check_knowledge_delta.py --body-stdin

Exit code 0 for meaningful or mechanical, 1 for empty/untouched/missing.
"""
from __future__ import annotations

import argparse
import re
import sys

MECHANICAL_MARKER = "<!-- no-knowledge-delta: mechanical task -->"

# Matches the '## Knowledge Delta' heading and everything up to the next
# '## ' heading (or end of string).
SECTION_RE = re.compile(r"##\s*Knowledge Delta\s*\n(.*?)(?=\n##\s|\Z)", re.S | re.I)

# Lines that are part of the untouched template skeleton, not real content:
# subheadings and HTML comments.
SKELETON_LINE_RE = re.compile(r"^\s*(#{1,6}\s.*|<!--.*-->)\s*$")


def classify(body: str) -> str:
    if MECHANICAL_MARKER in body:
        return "mechanical"

    m = SECTION_RE.search(body)
    if not m:
        return "empty"

    section = m.group(1)
    meaningful_lines = [
        line for line in section.splitlines()
        if line.strip() and not SKELETON_LINE_RE.match(line)
    ]
    return "meaningful" if meaningful_lines else "empty"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--body-file", help="Path to a file containing the PR body")
    src.add_argument("--body-stdin", action="store_true", help="Read the PR body from stdin")
    args = ap.parse_args()

    if args.body_stdin:
        body = sys.stdin.read()
    else:
        with open(args.body_file, encoding="utf-8") as f:
            body = f.read()

    result = classify(body)
    print(f"knowledge-delta-check: {result}")
    if result == "empty":
        print(
            "PR body must contain either a meaningfully completed "
            "'## Knowledge Delta' section (real content under Added/"
            "Changed/Not yet ratified, not just the empty template) or "
            "the exact '<!-- no-knowledge-delta: mechanical task -->' "
            "marker for purely mechanical changes. See CONTRIBUTING.md."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
