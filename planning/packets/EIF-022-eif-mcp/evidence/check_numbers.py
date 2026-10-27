"""Check that the baseline table in 02-FACTS matches evidence/baseline-2026-10-26.json
and print the arithmetic behind the INFERRED footprint paragraph.

Usage: python planning/packets/EIF-022-eif-mcp/evidence/check_numbers.py planning/packets/EIF-022-eif-mcp
"""
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
facts = (root / "02-FACTS-022-eif-mcp.md").read_text(encoding="utf-8")
data = json.loads((root / "evidence" / "baseline-2026-10-26.json").read_text(encoding="utf-8"))

def fmt(n):
    return f"{n:,}".replace(",", " ")

rows = {}
for line in facts.splitlines():
    if line.startswith("| ") and line.split("|")[1].strip() in {"claude-code", "codex", "cursor", "hermes"}:
        rows[line.split("|")[1].strip()] = [c.strip() for c in line.strip("|").split("|")]

bad = []
for a in data["adapters"]:
    t = a["tier_a_always_loaded"]; b = a["tier_b_first_task"]; s = a["scenarios"]
    expect = [a["adapter"], fmt(t["entrypoint"]["bytes"]), fmt(t["skill_loaders"]["frontmatter_only"]["bytes"]),
              fmt(b["doctor_stdout"]["bytes"]), fmt(s["light"]["bytes"]), fmt(s["knowledge_search"]["bytes"]),
              fmt(s["packet_plan"]["bytes"]), fmt(s["packet_run"]["bytes"])]
    got = rows.get(a["adapter"])
    if got != expect:
        bad.append((a["adapter"], got, expect))

claude = data["adapters"][0]
for needle in (fmt(claude["tier_b_first_task"]["skill_walks_one_hop"]["run-execution-packet"]["total"]["bytes"]),
               fmt(claude["tier_b_first_task"]["skill_walks_one_hop"]["plan-execution-packet"]["total"]["bytes"]),
               fmt(claude["tier_b_first_task"]["skill_walks_one_hop"]["knowledge-search"]["total"]["bytes"]),
               fmt(claude["scenarios"]["light_if_host_loads_full_loaders"]["bytes"]),
               fmt(claude["runtime_bundle"]["bytes"]), str(claude["runtime_bundle"]["files"])):
    if needle not in facts:
        bad.append(("missing in facts", needle))

# arithmetic of the inferred paragraph
light_after = 2400 + 3735 + 6144 + 1536
run_after = light_after + 8000
print("light_after", light_after, round(100 * (light_after / claude["scenarios"]["light"]["bytes"] - 1), 1), "%")
print("run_after", run_after, round(100 * (run_after / claude["scenarios"]["packet_run"]["bytes"] - 1), 1), "%")
print("plan_after", run_after, round(100 * (run_after / claude["scenarios"]["packet_plan"]["bytes"] - 1), 1), "%")
print("tokens light/run", claude["scenarios"]["light"]["est_tokens"], claude["scenarios"]["packet_run"]["est_tokens"])
print("MISMATCHES:", bad or "none")
sys.exit(1 if bad else 0)
