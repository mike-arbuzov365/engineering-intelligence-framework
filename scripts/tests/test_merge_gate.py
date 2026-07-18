#!/usr/bin/env python3
"""Proof matrix for the controlled merge gate (scripts/eif_merge_pr.py).

Two layers:

- Unit: `evaluate_gate` is a pure function, so most scenarios are driven with
  a synthetic PR dict - no `gh`, no live PRs (the Phase B proof matrix
  explicitly says NOT to use live product repositories for temporary proof
  PRs). The required check contexts come from the same
  core/policies/merge-policy.json the real gate reads, so this test also
  guards that single-source contract.
- Integration: a handful of scenarios drive `eif_merge_pr.main()` end-to-end
  with a programmable fake standing in for `run_gh`, to prove behaviour that
  only exists at the CLI/orchestration layer - repo auto-resolution and its
  fail-closed failure mode, thread pagination, and the second live-gate pass
  catching a change that isn't visible in the head SHA.

Usage:
    python scripts/tests/test_merge_gate.py
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eif_merge_pr as G  # noqa: E402

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
POLICY = G.load_policy(FRAMEWORK_ROOT / "core" / "policies" / "merge-policy.json")
REQUIRED = POLICY["required_check_contexts"]


# --------------------------------------------------------------- fake gh CLI
class FakeGh:
    """Programmable stand-in for eif_merge_pr.run_gh. Responses are queued
    per call category (repo_view / pr_view / graphql / pr_merge), so a
    scenario can make sequential calls to the same endpoint return different
    data - e.g. the two evaluate_live_gate() passes in one main() run, or
    successive GraphQL pages."""

    def __init__(self):
        self.queues: dict[str, list[tuple[int, str]]] = {}
        self.calls: list[list[str]] = []

    def queue(self, category: str, code: int, out: str) -> "FakeGh":
        self.queues.setdefault(category, []).append((code, out))
        return self

    @staticmethod
    def _category(args: list[str]) -> str:
        if args[:2] == ["repo", "view"]:
            return "repo_view"
        if args[:2] == ["pr", "view"]:
            return "pr_view"
        if args[:2] == ["api", "graphql"]:
            return "graphql"
        if args[:2] == ["pr", "merge"]:
            return "pr_merge"
        return "other:" + " ".join(args[:2])

    def __call__(self, args: list[str]) -> tuple[int, str]:
        self.calls.append(args)
        cat = self._category(args)
        q = self.queues.get(cat)
        if not q:
            raise AssertionError(f"FakeGh: no queued response for category {cat!r}, args={args}")
        return q.pop(0)


def run_main_with_fake_gh(fake: FakeGh, argv: list[str]) -> tuple[int, str]:
    original = G.run_gh
    G.run_gh = fake  # type: ignore[assignment]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = G.main(argv)
    finally:
        G.run_gh = original
    return code, buf.getvalue()


def clean_checks() -> list[dict]:
    return [{"name": n, "status": "COMPLETED", "conclusion": "SUCCESS"} for n in REQUIRED]


# A body with real content under Knowledge Delta, so integration scenarios
# that aren't about Knowledge Delta don't fail on it incidentally (the real
# classifier subprocess runs against this text, not a stub).
MEANINGFUL_BODY = "## Knowledge Delta\n\n### Added\n- something real\n"


def pr_json(**over) -> str:
    pr = {
        "state": "OPEN", "isDraft": False, "headRefOid": "a" * 40,
        "baseRefName": POLICY["base_branch"], "headRefName": "feature/x",
        "body": MEANINGFUL_BODY,
        "reviewDecision": "", "statusCheckRollup": clean_checks(), "url": "https://x",
    }
    pr.update(over)
    return json.dumps(pr)


def graphql_json(nodes: list[dict], *, has_next: bool = False, end_cursor: str | None = None) -> str:
    return json.dumps({
        "data": {"repository": {"pullRequest": {"reviewThreads": {
            "nodes": nodes,
            "pageInfo": {"hasNextPage": has_next, "endCursor": end_cursor},
        }}}}
    })


def main() -> int:
    results = []

    def check(name, cond, detail=""):
        ok = bool(cond)
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else ": " + str(detail)[:300]))
        results.append(ok)

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

    # ----------------------------------------------------------- unit: core
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
    # 9b. Knowledge Delta requirement is a policy property; the real EIF
    #     policy always requires it, and only a *different* policy file
    #     (never a runtime flag) could turn it off.
    check("9b. real EIF policy has knowledge_delta_required=True", POLICY["knowledge_delta_required"] is True)
    check("9c. a policy with knowledge_delta_required=False does not block on missing KD",
          G.evaluate_gate(clean_pr(), {**POLICY, "knowledge_delta_required": False},
                           unresolved_threads=0, knowledge_delta_ok=False) == [])

    # Extra defensive cases.
    check("x. CHANGES_REQUESTED blocks", gate(clean_pr(reviewDecision="CHANGES_REQUESTED")) != [])
    check("x. non-OPEN state blocks", gate(clean_pr(state="MERGED")) != [])
    check("x. no checks blocks under the real EIF policy (no bypass exists)",
          gate(clean_pr(statusCheckRollup=[])) != [])
    check("x. a non-required failed check also blocks",
          gate(clean_pr(statusCheckRollup=clean_checks() + [{"name": "flaky", "status": "COMPLETED", "conclusion": "FAILURE"}])) != [])

    # 11. required contexts come from the single policy source (not hardcoded here).
    check("11. policy provides exactly three consolidated required contexts", len(REQUIRED) == 3, str(len(REQUIRED)))
    # 12. platform enforcement honestly recorded as wrapper-only (branch protection unavailable).
    check("12. wrapper-only enforcement recorded (branch protection unavailable)",
          POLICY["platform_enforcement"]["branch_protection_available"] is False)

    # ------------------------------------------- unit: 1.2 no-bypass-flag proof
    # There is no `allow_missing_checks` parameter on evaluate_gate anymore -
    # a repo genuinely without CI can ONLY be expressed via a different
    # policy file, never via how this script is invoked.
    no_ci_policy = {**POLICY, "required_check_contexts": [], "allow_no_checks": True}
    check("13. a policy that explicitly declares no CI (empty required contexts + allow_no_checks=True) passes with zero checks",
          G.evaluate_gate(clean_pr(statusCheckRollup=[]), no_ci_policy, unresolved_threads=0, knowledge_delta_ok=True) == [])
    misdeclared_policy = {**POLICY, "required_check_contexts": []}  # allow_no_checks left at policy default (False)
    check("14. empty required_check_contexts WITHOUT allow_no_checks=True is refused, not silently allowed",
          G.evaluate_gate(clean_pr(statusCheckRollup=[]), misdeclared_policy, unresolved_threads=0, knowledge_delta_ok=True) != [])

    # ------------------------------------------- unit: 1.6 duplicate contexts
    dup_one_failed = clean_checks()
    dup_one_failed.append({"name": REQUIRED[0], "status": "COMPLETED", "conclusion": "FAILURE"})
    check("15. duplicate required context: one success + one failed occurrence still blocks",
          gate(clean_pr(statusCheckRollup=dup_one_failed)) != [])
    dup_both_ok = clean_checks()
    dup_both_ok.append({"name": REQUIRED[0], "status": "COMPLETED", "conclusion": "SUCCESS"})
    check("16. duplicate required context: both occurrences success still passes",
          gate(clean_pr(statusCheckRollup=dup_both_ok)) == [])
    dup_one_pending = clean_checks()
    dup_one_pending.append({"name": REQUIRED[0], "status": "IN_PROGRESS", "conclusion": None})
    check("17. duplicate required context: one success + one still-pending occurrence blocks",
          gate(clean_pr(statusCheckRollup=dup_one_pending)) != [])

    # --------------------------------------------------- integration: 1.1/1.4/1.5
    # A. no --repo given and gh repo view fails -> blocked (fail closed, never
    #    a warning + unresolved_threads=0).
    fake = FakeGh().queue("repo_view", 1, "error: not a git repository")
    code, out = run_main_with_fake_gh(fake, ["--pr", "4", "--dry-run"])
    check("A. unresolvable repo (no --repo, gh repo view fails) blocks the gate",
          code != 0 and "MERGE-GATE BLOCK" in out and "resolve" in out, (code, out))

    # B. no --repo given, but gh repo view succeeds -> the thread check still
    #    actually runs (proves auto-resolution is wired to the real check,
    #    not just made to not-crash).
    fake = (FakeGh()
            .queue("repo_view", 0, json.dumps({"nameWithOwner": "acme/widgets"}))
            .queue("pr_view", 0, pr_json())
            .queue("graphql", 0, graphql_json([{"isResolved": False}])))
    code, out = run_main_with_fake_gh(fake, ["--pr", "4", "--dry-run"])
    check("B. auto-resolved repo (no --repo) still runs the thread check and blocks on an unresolved thread",
          code != 0 and "unresolved review thread" in out, (code, out))

    # C. review-thread GraphQL call fails -> blocked, never treated as zero.
    fake = (FakeGh()
            .queue("repo_view", 0, json.dumps({"nameWithOwner": "acme/widgets"}))
            .queue("pr_view", 0, pr_json())
            .queue("graphql", 1, "error: GraphQL timeout"))
    code, out = run_main_with_fake_gh(fake, ["--pr", "4", "--repo", "acme/widgets", "--dry-run"])
    check("C. review-thread GraphQL failure blocks (never silently treated as zero unresolved)",
          code != 0 and "MERGE-GATE BLOCK" in out, (code, out))

    # D. review threads beyond the first page(100) are paginated and counted.
    fake = (FakeGh()
            .queue("repo_view", 0, json.dumps({"nameWithOwner": "acme/widgets"}))
            .queue("pr_view", 0, pr_json())
            .queue("graphql", 0, graphql_json([{"isResolved": True}] * 100, has_next=True, end_cursor="CURSOR1"))
            .queue("graphql", 0, graphql_json([{"isResolved": False}] * 5, has_next=False)))
    code, out = run_main_with_fake_gh(fake, ["--pr", "4", "--repo", "acme/widgets", "--dry-run"])
    check("D. review threads on a second page (beyond first:100) are fetched and counted (5 unresolved)",
          code != 0 and "5 unresolved review thread" in out, (code, out))
    graphql_calls = [c for c in fake.calls if c[:2] == ["api", "graphql"]]
    check("D. the second page request carries the endCursor from the first page",
          len(graphql_calls) == 2 and any(a == "c=CURSOR1" for a in graphql_calls[1]), graphql_calls)

    # E. the second live-gate pass (immediately before merge) catches a check
    #    flipping to failure even though the head SHA never moved.
    head = "a" * 40
    broken_checks = clean_checks(); broken_checks[0]["conclusion"] = "FAILURE"
    fake = (FakeGh()
            .queue("repo_view", 0, json.dumps({"nameWithOwner": "acme/widgets"}))
            .queue("pr_view", 0, pr_json(headRefOid=head))                                    # 1st pass: clean
            .queue("graphql", 0, graphql_json([]))                                             # 1st pass: 0 unresolved
            .queue("pr_view", 0, pr_json(headRefOid=head, statusCheckRollup=broken_checks))    # 2nd pass: now failing
            .queue("graphql", 0, graphql_json([])))                                            # 2nd pass: still 0 unresolved
    code, out = run_main_with_fake_gh(fake, ["--pr", "4", "--repo", "acme/widgets"])  # not dry-run
    check("E. second live evaluation catches a check flipping to failure even though head never moved",
          code != 0 and "final pre-merge check" in out and "required check" in out, (code, out))
    check("E. gh pr merge is never invoked when the final pre-merge check blocks",
          [c for c in fake.calls if c[:2] == ["pr", "merge"]] == [], fake.calls)

    # E2. the second pass also catches Knowledge Delta degrading (e.g. a late
    #     body edit) between the two live evaluations.
    empty_body_pr = json.loads(pr_json(headRefOid=head))
    empty_body_pr["body"] = "## Knowledge Delta\n\n### Added\n"  # template-only, no real content
    fake = (FakeGh()
            .queue("repo_view", 0, json.dumps({"nameWithOwner": "acme/widgets"}))
            .queue("pr_view", 0, pr_json(headRefOid=head))     # 1st pass: meaningful KD
            .queue("graphql", 0, graphql_json([]))
            .queue("pr_view", 0, json.dumps(empty_body_pr))    # 2nd pass: KD now empty/template-only
            .queue("graphql", 0, graphql_json([])))
    code, out = run_main_with_fake_gh(fake, ["--pr", "4", "--repo", "acme/widgets"])
    check("E2. second live evaluation catches Knowledge Delta degrading to empty even though head never moved",
          code != 0 and "final pre-merge check" in out and "Knowledge Delta" in out, (code, out))

    # E3. the second pass also catches a new unresolved review thread
    #     appearing between the two live evaluations.
    fake = (FakeGh()
            .queue("repo_view", 0, json.dumps({"nameWithOwner": "acme/widgets"}))
            .queue("pr_view", 0, pr_json(headRefOid=head))
            .queue("graphql", 0, graphql_json([]))                        # 1st pass: 0 unresolved
            .queue("pr_view", 0, pr_json(headRefOid=head))
            .queue("graphql", 0, graphql_json([{"isResolved": False}])))  # 2nd pass: 1 new unresolved
    code, out = run_main_with_fake_gh(fake, ["--pr", "4", "--repo", "acme/widgets"])
    check("E3. second live evaluation catches a new unresolved review thread even though head never moved",
          code != 0 and "final pre-merge check" in out and "unresolved review thread" in out, (code, out))

    # F. positive control: a genuinely clean two-pass run proceeds to merge.
    head2 = "b" * 40
    fake = (FakeGh()
            .queue("repo_view", 0, json.dumps({"nameWithOwner": "acme/widgets"}))
            .queue("pr_view", 0, pr_json(headRefOid=head2))
            .queue("graphql", 0, graphql_json([]))
            .queue("pr_view", 0, pr_json(headRefOid=head2))
            .queue("graphql", 0, graphql_json([]))
            .queue("pr_merge", 0, "")
            .queue("pr_view", 0, json.dumps({"state": "MERGED", "mergedAt": "2026-07-16T00:00:00Z", "mergeCommit": {"oid": "c" * 40}})))
    code, out = run_main_with_fake_gh(fake, ["--pr", "4", "--repo", "acme/widgets"])
    check("F. a genuinely clean two-pass run proceeds to gh pr merge and reports MERGED",
          code == 0 and "MERGED" in out, (code, out))
    merge_calls = [c for c in fake.calls if c[:2] == ["pr", "merge"]]
    check("F. gh pr merge was invoked exactly once, pinned with --match-head-commit to the confirmed head",
          len(merge_calls) == 1 and "--match-head-commit" in merge_calls[0] and head2 in merge_calls[0], merge_calls)

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_merge_gate: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
