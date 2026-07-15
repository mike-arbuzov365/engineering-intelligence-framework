#!/usr/bin/env python3
"""Offline, lifecycle-aware keyword search over an EIF instance's knowledge.

GENERALIZE of the private EI's knowledge-search skill: same design constraint
(lean, offline, no embeddings, no external service - a reproducible local
search beats an opaque ranked one for this use case), reimplemented in Python
against this framework's own index.

Two properties this adds over a naive grep, both required by the public
ontology:

1. Lifecycle awareness. By default only *eligible* statuses are returned
   (validated). draft/superseded/deprecated/rejected are NOT treated as
   equivalent to validated knowledge - retrieving a `rejected` hypothesis as
   if it were a validated lesson is a correctness bug, not a feature. Use
   --status or --all-statuses to widen deliberately. Every result shows its
   status, evidence, confidence, and a staleness flag if past review_after.

2. Honest failure. A malformed knowledge artifact (unparseable frontmatter)
   is reported explicitly, so "no results" is never silently confused with
   "the relevant artifact was invalid and skipped." --strict turns any
   malformed artifact into a non-zero exit.

Unicode: query terms are tokenized with a Unicode-aware pattern, so Ukrainian
(and any non-ASCII) queries and artifact bodies are searchable - a Ukrainian
instance that can generate Ukrainian docs but not retrieve Ukrainian
knowledge is not a complete locale implementation.

Usage:
    python scripts/eif_search_knowledge.py --knowledge-root PATH "<query>" [--type TYPE]
        [--status validated,draft] [--all-statuses] [--top N] [--strict] [--json]
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eif_generate_index import build_index  # noqa: E402

# \w is Unicode-aware for str patterns in Python 3, so this matches Cyrillic
# (високосний), ASCII (leap), digits, and hyphenated terms alike. The previous
# [A-Za-z0-9_-] pattern silently dropped every Cyrillic term, making Ukrainian
# queries return nothing.
WORD_RE = re.compile(r"\w[\w-]*", re.UNICODE)

DEFAULT_ELIGIBLE = {"validated"}
HEADING_RE = re.compile(r"^#\s+(.*)$", re.M)


def score(query_terms: list[str], type_value: str, path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="ignore").lower()
    heading_match = HEADING_RE.search(text)
    title = (heading_match.group(1) if heading_match else "").lower()
    total = 0
    for term in query_terms:
        term_lower = term.lower()
        total += text.count(term_lower)
        if term_lower in title:
            total += 5  # weight title/heading matches higher than body hits
        if term_lower in type_value.lower():
            total += 2
    return total


def _is_stale(review_after: str) -> bool:
    if not review_after:
        return False
    try:
        return datetime.date.fromisoformat(review_after) < datetime.date.today()
    except ValueError:
        return False


def search(knowledge_root: Path, query: str, type_filter: str | None, top: int,
           eligible: set[str] | None) -> dict:
    """Return a structured result: matched artifacts, plus what was skipped and
    why (status-ineligible, malformed) so callers can tell 'nothing matched'
    from 'the match was filtered out'."""
    rows, malformed = build_index(knowledge_root)
    terms = WORD_RE.findall(query)

    results = []
    skipped_by_status = []
    for row in rows:
        if type_filter and row["type"] != type_filter:
            continue
        path = knowledge_root / row["path"]
        s = score(terms, row["type"], path)
        if s <= 0:
            continue
        if eligible is not None and row["status"] not in eligible:
            skipped_by_status.append({**row, "score": s})
            continue
        results.append({**row, "score": s, "stale": _is_stale(row["review_after"])})

    results.sort(key=lambda r: r["score"], reverse=True)
    skipped_by_status.sort(key=lambda r: r["score"], reverse=True)
    return {
        "query": query,
        "terms": terms,
        "results": results[:top],
        "skipped_by_status": skipped_by_status,
        "malformed": [p.relative_to(knowledge_root).as_posix() for p in malformed],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--knowledge-root", required=True)
    ap.add_argument("query")
    ap.add_argument("--type", default=None, help="Filter to this frontmatter 'type' only")
    ap.add_argument("--status", default=None, help="Comma-separated eligible statuses (default: validated)")
    ap.add_argument("--all-statuses", action="store_true", help="Return artifacts of any status (overrides --status)")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--strict", action="store_true", help="Exit non-zero if any malformed artifact is found")
    ap.add_argument("--json", action="store_true", help="Emit structured JSON")
    args = ap.parse_args()

    knowledge_root = Path(args.knowledge_root).resolve()
    if not knowledge_root.is_dir():
        print(f"eif-search-knowledge: not a directory: {knowledge_root}", file=sys.stderr)
        return 1

    if args.all_statuses:
        eligible = None
    elif args.status:
        eligible = {s.strip() for s in args.status.split(",") if s.strip()}
    else:
        eligible = set(DEFAULT_ELIGIBLE)

    out = search(knowledge_root, args.query, args.type, args.top, eligible)

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        results = out["results"]
        if not results:
            print(f"eif-search-knowledge: no eligible knowledge found for query: {args.query}")
        else:
            print(f"eif-search-knowledge: {len(results)} result(s) for query: {args.query}")
            for r in results:
                flags = " [STALE - past review_after]" if r.get("stale") else ""
                meta = f"status={r['status']}"
                if r.get("evidence"):
                    meta += f", evidence={r['evidence']}"
                if r.get("confidence"):
                    meta += f", confidence={r['confidence']}"
                print(f"  [{r['score']:>3}] {r['path']}  ({meta}, type={r['type']}){flags}")
                if r["excerpt"]:
                    print(f"        {r['excerpt']}")
        if out["skipped_by_status"]:
            print(f"  ({len(out['skipped_by_status'])} matching artifact(s) skipped as status-ineligible; "
                  f"pass --all-statuses or --status to include)")
        if out["malformed"]:
            print(f"  WARNING: {len(out['malformed'])} malformed artifact(s) skipped (unparseable frontmatter): "
                  f"{', '.join(out['malformed'])}")

    if args.strict and out["malformed"]:
        print("eif-search-knowledge: --strict: malformed artifacts present", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
