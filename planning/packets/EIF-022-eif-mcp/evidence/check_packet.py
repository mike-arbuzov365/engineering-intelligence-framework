"""Mechanical consistency check of this packet (the repository has no packet validator).

Checks: every packet-local decision reference resolves, every Definition-of-Done
item appears in the roadmap cross-check, roadmap sessions match launch files and
README links, launch files carry the template sections and a status from the
D-008 vocabulary. Lists verification scripts that sessions are expected to create.

Usage: python planning/packets/EIF-022-eif-mcp/evidence/check_packet.py planning/packets/EIF-022-eif-mcp
"""
import re, sys
from pathlib import Path

root = Path(sys.argv[1])
text = {p.name: p.read_text(encoding="utf-8") for p in root.rglob("*.md")}
problems = []

decisions = text["03-DECISIONS-022-eif-mcp.md"]
defined = set(re.findall(r"^## (D-\d{3}):", decisions, re.M))
print("decisions defined:", sorted(defined))

# packet-local decision references (three digits) must resolve
for name, body in text.items():
    for ref in set(re.findall(r"\bD-(\d{3})\b", body)):
        if f"D-{ref}" not in defined:
            problems.append(f"{name}: references undefined decision D-{ref}")

# every DD in the charter must appear in the roadmap cross-check and be listed once
charter = text["01-CHARTER-022-eif-mcp.md"]
roadmap = text["04-ROADMAP-022-eif-mcp.md"]
dds = re.findall(r"`(DD-\d{2})`", charter)
cross = roadmap.split("## Definition-of-done cross-check", 1)[1]
for dd in dds:
    if dd not in cross:
        problems.append(f"{dd} missing in roadmap cross-check")
print("DD items:", len(dds))

# sessions: roadmap blocks, launch files, README rows
blocks = re.findall(r"^## Session (\d{3}) - ", roadmap, re.M)
launch = sorted(n for n in text if n.startswith("SESSION-"))
print("roadmap sessions:", blocks, "launch files:", len(launch))
if len(blocks) != len(launch):
    problems.append("session count mismatch between roadmap and launch files")
readme = text["00-README.md"]
for n in launch:
    if n.split(".")[0] not in readme:
        problems.append(f"{n} not linked in 00-README")

# every launch file has the template sections and a boolean exit list
required = ["## Goal", "## Required reading order", "## Experience retrieval preflight", "## Scope",
            "## Out of scope / do not touch", "## Verification", "## Bounded loop contract",
            "## Exit criteria", "## Closeout / Knowledge Delta"]
for n in launch:
    for sec in required:
        if sec not in text[n]:
            problems.append(f"{n}: missing section {sec}")
    if "- [ ]" not in text[n]:
        problems.append(f"{n}: no checkbox exit criteria")
    fm = text[n].split("---", 2)[1]
    for key in ("id:", "logical_session:", "type: session-launch", "status:", "source_artifact:", "session_context:", "depends_on:"):
        if key not in fm:
            problems.append(f"{n}: frontmatter lacks {key}")
    if not re.search(r"^status: (prepared|in_progress|completed|blocked|deferred)$", fm, re.M):
        problems.append(f"{n}: status outside the D-008 vocabulary")

# verification commands that reference existing repo scripts
repo = root.parents[2]
missing = set()
for n in launch:
    for cmd in re.findall(r"python (scripts/[\w./-]+\.py)", text[n]):
        if not (repo / cmd).exists():
            missing.add((cmd, n))
print("verification scripts not yet in repo (expected: created by sessions):")
for cmd, n in sorted(missing):
    print("  ", cmd, "<-", n)

print("PROBLEMS:", problems or "none")
sys.exit(1 if problems else 0)
