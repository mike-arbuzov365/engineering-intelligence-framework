#!/usr/bin/env python3
"""Proof matrix for the controlled merge gate (scripts/eif_merge_pr.py).

`evaluate_gate` is a pure function, so every scenario is driven with a
synthetic PR dict - no `gh`, no live PRs (the Phase B proof matrix explicitly
says NOT to use live product repositories for temporary proof PRs). The
required check contexts come from the same core/policies/merge-policy.json the
real gate reads, so this test also guards that single-source contract.

Usage:
    python scripts/tests/test_merge_gate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_merge_pr as G  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
POLICY = G.load_policy(FRAMEWORK_ROOT / "core" / "policies" / "merge-policy.json")
REQUIRED = POLICY["required_check_contexts"]


def main() -> int:
    results = []

    def check(name, cond, detail=""):
        ok = bool(cond)
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else ": " + str(detail)[:300]))
        results.append(ok)

    def clean_checks():
        return [{"name": n, "status": "COMPLETED", "conclusion": "SUCCESS"} for n in REQUIRED]

    def clean_pr(**over):
        pr = {
            "state": "OPEN", "isDraft": False, "headRefOid": "a" * 40,
            "baseRefName": POLICY["base_branch"], "headRefName": "feature/x",
            "reviewDecision": "", "statusCheckRollup": clean_checks(), "url": "https://x",
        }
        pr.update(over)
        return pr

    def gate(pr, **kw):
        kw.setdefault("unresolved_threads", 0)
        kw.setdefault("knowledge_delta_ok", True)
        return G.evaluate_gate(pr, POLICY, **kw)

    # 10. clean PR -> no blocks (a dry-run would proceed)
    check("10. clean PR passes the gate", gate(clean_pr()) == [], gate(clean_pr()))

    # 1. missing required context -> blocked
    b = gate(clean_pr(statusCheckRollup=clean_checks()[:-1]))
    check("1. missing required context blocks", any("missing" in x for x in b), b)

    # 2. failed required context -> blocked
    ch = clean_checks(); ch[0]["conclusion"] = "FAILURE"
    check("2. failed required context blocks", gate(clean_pr(statusCheckRollup=ch)) != [])

    # 3. pending required context -> blocked
    ch = clean_checks(); ch[0]["status"] = "IN_PROGRESS"; ch[0]["conclusion"] = None
    b = gate(clean_pr(statusCheckRollup=ch))
    check("3. pending required context blocks", any("not completed" in x for x in b), b)

    # 4. cancelled / skipped required context -> blocked
    for concl in ("CANCELLED", "SKIPPED"):
        ch = clean_checks(); ch[0]["conclusion"] = concl
        check(f"4. required context {concl} blocks", gate(clean_pr(statusCheckRollup=ch)) != [])

    # 5. moved head (evidence-freeze pin) -> blocked; matching head -> passes
    b = gate(clean_pr(headRefOid="b" * 40), expected_head="a" * 40)
    check("5. moved head (expected != live) blocks", any("expected head" in x for x in b), b)
    check("5. matching head passes", gate(clean_pr(headRefOid="a" * 40), expected_head="a" * 40) == [])

    # 6. wrong base branch -> blocked
    check("6. wrong base branch blocks", gate(clean_pr(baseRefName="release")) != [])

    # 7. draft PR -> blocked
    check("7. draft PR blocks", gate(clean_pr(isDraft=True)) != [])

    # 8. unresolved review thread -> blocked; zero -> passes
    check("8. unresolved review thread blocks", gate(clean_pr(), unresolved_threads=1) != [])
    check("8. zero unresolved threads passes", gate(clean_pr(), unresolved_threads=0) == [])

    # 9. missing/empty Knowledge Delta -> blocked
    check("9. missing Knowledge Delta blocks", gate(clean_pr(), knowledge_delta_ok=False) != [])

    # Extra defensive cases.
    check("x. CHANGES_REQUESTED blocks", gate(clean_pr(reviewDecision="CHANGES_REQUESTED")) != [])
    check("x. non-OPEN state blocks", gate(clean_pr(state="MERGED")) != [])
    check("x. no checks + not allow-missing blocks", gate(clean_pr(statusCheckRollup=[])) != [])
    check("x. no checks + allow-missing passes", gate(clean_pr(statusCheckRollup=[]), allow_missing_checks=True) == [])
    check("x. a non-required failed check also blocks",
          gate(clean_pr(statusCheckRollup=clean_checks() + [{"name": "flaky", "status": "COMPLETED", "conclusion": "FAILURE"}])) != [])

    # 11. required contexts come from the single policy source (not hardcoded here).
    check("11. policy provides exactly six required contexts", len(REQUIRED) == 6, str(len(REQUIRED)))
    # 12. platform enforcement honestly recorded as wrapper-only (branch protection unavailable).
    check("12. wrapper-only enforcement recorded (branch protection unavailable)",
          POLICY["platform_enforcement"]["branch_protection_available"] is False)

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_merge_gate: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
