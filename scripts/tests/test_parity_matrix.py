#!/usr/bin/env python3
"""Adapter parity-matrix drift test.

adapters/parity-matrix.json is hand-authored, which means it can silently
go stale: a new adapter added to scripts/eif_adapters.py.ADAPTERS with no
matching matrix entry, or a dimension added to the matrix's own
`dimensions` list without every adapter being updated for it. This suite
fails loudly on either case instead of letting the matrix quietly drift
out of sync with the actual registry.

Usage:
    python scripts/tests/test_parity_matrix.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FRAMEWORK_ROOT / "scripts"))
from eif_adapters import ADAPTERS  # noqa: E402

MATRIX_PATH = FRAMEWORK_ROOT / "adapters" / "parity-matrix.json"


def main() -> int:
    results: list[bool] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        ok = bool(cond)
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else ": " + str(detail)[:300]))
        results.append(ok)

    check("parity-matrix.json exists", MATRIX_PATH.exists())
    if not MATRIX_PATH.exists():
        print(f"EIF-RESULT: passed={sum(results)} total={len(results)}")
        return 1

    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    dimensions = matrix.get("dimensions") or []
    adapters_in_matrix = matrix.get("adapters") or {}

    check("matrix declares at least one dimension", len(dimensions) > 0)

    registered = set(ADAPTERS.keys())
    in_matrix = set(adapters_in_matrix.keys())

    check(
        "every registered adapter has a matrix entry (no adapter added without updating parity-matrix.json)",
        registered.issubset(in_matrix),
        f"registered={sorted(registered)} matrix={sorted(in_matrix)} missing={sorted(registered - in_matrix)}",
    )
    check(
        "the matrix has no entry for an adapter that isn't actually registered (stale leftover)",
        not (in_matrix - registered),
        f"stale entries not in ADAPTERS: {sorted(in_matrix - registered)}",
    )

    for adapter_name in sorted(registered & in_matrix):
        entry = adapters_in_matrix[adapter_name]
        missing_dims = [d for d in dimensions if d not in entry or not str(entry[d]).strip()]
        check(
            f"'{adapter_name}' matrix entry covers every declared dimension",
            not missing_dims,
            f"missing/empty: {missing_dims}",
        )

    # Cross-check a couple of matrix claims against the registry itself, so
    # the matrix can't assert something the registry contradicts.
    for adapter_name in sorted(registered & in_matrix):
        entry_text = adapters_in_matrix[adapter_name].get("entrypoint", "")
        real_entrypoint = ADAPTERS[adapter_name]["entrypoint"]
        check(
            f"'{adapter_name}' matrix entrypoint text mentions the real registered entrypoint ({real_entrypoint!r})",
            real_entrypoint in entry_text,
            entry_text,
        )

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_parity_matrix: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
