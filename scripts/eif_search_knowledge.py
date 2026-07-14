#!/usr/bin/env python3
"""Offline keyword search over an EIF project instance's knowledge artifacts.

GENERALIZE of the private EI's knowledge-search skill: same design
constraint (lean, offline, no embeddings, no external service - see
core/ontology's evidence/authority model for why a reproducible local
search beats an opaque ranked one for this use case), reimplemented in
Python against this framework's own index generator instead of `rg` +
PowerShell.

Not a general search engine: case-insensitive substring/keyword matching
over each artifact's title, frontmatter type, and body text, ranked by
match count. Good enough to reliably surface a handful of seeded lessons in
a small project instance; if a project instance's knowledge base grows
large enough that this stops being good enough, that is itself worth a
Knowledge Delta entry, not a silent upgrade to embeddings.

Usage:
    python scripts/eif_search_knowledge.py --knowledge-root PATH "<query>" [--type TYPE] [--top N]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    # See scripts/eif_init.py for why: Windows console codepages cannot
    # encode non-ASCII excerpt text without this.
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eif_generate_index import build_index  # noqa: E402

WORD_RE = re.compile(r"[A-Za-z0-9_\-]+")


def score(query_terms: list[str], fm: dict, path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    title_match = 0
    heading_match = re.search(r"^#\s+(.*)$", text, re.M)
    title = heading_match.group(1) if heading_match else ""
    total = 0
    for term in query_terms:
        term_lower = term.lower()
        total += text.count(term_lower)
        if term_lower in title.lower():
            total += 5  # weight title/heading matches higher than body hits
        if term_lower in str(fm.get("type", "")).lower():
            total += 2
    return total


def search(knowledge_root: Path, query: str, type_filter: str | None, top: int) -> list[dict]:
    rows, _ = build_index(knowledge_root)
    terms = WORD_RE.findall(query)
    results = []
    for row in rows:
        if type_filter and row["type"] != type_filter:
            continue
        path = knowledge_root / row["path"]
        s = score(terms, {"type": row["type"]}, path)
        if s > 0:
            results.append({**row, "score": s})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge-root", required=True, help="Directory to search for *.md knowledge artifacts")
    ap.add_argument("query", help="Search query")
    ap.add_argument("--type", default=None, help="Filter to this frontmatter 'type' only")
    ap.add_argument("--top", type=int, default=5, help="Max results to return (default 5)")
    args = ap.parse_args()

    knowledge_root = Path(args.knowledge_root).resolve()
    if not knowledge_root.is_dir():
        print(f"eif-search-knowledge: not a directory: {knowledge_root}", file=sys.stderr)
        return 1

    results = search(knowledge_root, args.query, args.type, args.top)

    if not results:
        print(f"eif-search-knowledge: no relevant knowledge found for query: {args.query}")
        return 0

    print(f"eif-search-knowledge: {len(results)} result(s) for query: {args.query}")
    for r in results:
        print(f"  [{r['score']:>3}] {r['path']}  (type={r['type']}, status={r['status']})")
        if r["excerpt"]:
            print(f"        {r['excerpt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
