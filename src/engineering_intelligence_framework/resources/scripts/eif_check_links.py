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


def list_tracked_markdown(repo: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "*.md"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return [repo / line for line in out.stdout.splitlines() if line.strip()]


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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="Repository root")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    broken = []
    for md_file in list_tracked_markdown(repo):
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
