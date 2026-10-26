"""Disposable, synthetic EIF instance used by both SDK transport suites."""
from pathlib import Path


def seed(root: Path) -> Path:
    from test_service_golden import capture
    root = root.resolve()
    assert capture(["new", str(root), "--project-name", "synthetic-mcp", "--adapter", "claude-code"], root.parent)["rc"] == 0
    knowledge = root / "knowledge"
    knowledge.mkdir(exist_ok=True)
    (knowledge / "synthetic.md").write_text("---\ntype: fact\nstatus: validated\nscope: project\nevidence: OBSERVED\nsource: code\ncreated: 2026-07-15\n---\n# Synthetic MCP fact\nThe synthetic answer is cobalt.\n", encoding="utf-8")
    packet = root / "planning/packets/demo"
    (packet / "sessions").mkdir(parents=True)
    (packet / "04-ROADMAP-demo.md").write_text("# Roadmap\n\n## Session 001\n", encoding="utf-8")
    (packet / "sessions/SESSION-001-demo.md").write_text("---\nid: SESSION-001\nstatus: prepared\ndepends_on: []\n---\n# Synthetic session\n", encoding="utf-8")
    source = "planning/packets/demo/sessions/SESSION-001-demo.md"
    assert capture(["session", "checkpoint", "--project-root", str(root), "--source-artifact", source, "--session-id", "demo", "--goal", "Synthetic reader verification", "--in-scope", "planning", "--no-touch", "product", "--next-action", "Inspect the packet", "--approval-state", "not_required"], root)["rc"] == 0
    return root
