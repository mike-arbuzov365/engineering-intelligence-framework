#!/usr/bin/env python3
"""Check that relative Markdown links (and anchor links) resolve to a real
file/section within the repository. Skips external (http/https/mailto)
links entirely - this is not a dead-external-link checker.

Usage:
    python scripts/eif_check_links.py [--repo PATH]

Exit code 1 if any relative link target is missing.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.M)


# Byte-for-byte relocated copies (scripts/sync_package_sources.py --check
# is what verifies these stay identical to their source), not files
# authored at this path - their relative links are only meaningful
# relative to the ORIGINAL tree location they were copied from, which is
# a different question than "does this link resolve from where the file
# now lives" that this checker asks everywhere else. A real bug this
# check itself caught while building the package: the first sync produced
# these copies with 7 now-broken relative links, invisible to a local
# pre-`git add` run (git ls-files only sees tracked files) but caught by
# CI running against the actual committed tree.
RELOCATED_COPY_PREFIX = "src/engineering_intelligence_framework/resources/"


def list_tracked_markdown(repo: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "*.md"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return [
        repo / line for line in out.stdout.splitlines()
        if line.strip() and not line.startswith(RELOCATED_COPY_PREFIX)
    ]


def slugify(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s


def anchors_in(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {slugify(h) for h in HEADING_RE.findall(text)}


def main() -> int:
    # Windows may default a redirected console/pipe to a legacy code page.
    # Link targets are project data and may be in any configured locale; a
    # diagnostic must never crash while trying to print the finding itself.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="Repository root")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    broken = []
    for md_file in list_tracked_markdown(repo):
        # git ls-files reflects the index. During an intentional unstaged
        # deletion the working-tree file is already absent; skip it instead of
        # crashing before the intended tree can be staged and checked.
        if not md_file.is_file():
            continue
        text = md_file.read_text(encoding="utf-8", errors="ignore")
        for match in LINK_RE.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("#"):
                # same-file anchor
                if slugify(target[1:]) not in anchors_in(md_file):
                    broken.append((md_file, target))
                continue
            path_part, _, anchor = target.partition("#")
            if not path_part:
                continue
            resolved = (md_file.parent / path_part).resolve()
            if not resolved.exists():
                broken.append((md_file, target))
                continue
            if anchor and resolved.suffix == ".md":
                if slugify(anchor) not in anchors_in(resolved):
                    broken.append((md_file, target))

    if broken:
        print(f"eif-check-links: {len(broken)} broken link(s)")
        for src, target in broken:
            print(f"  {src.relative_to(repo)} -> {target}")
        return 1

    print("eif-check-links: all relative links resolve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
