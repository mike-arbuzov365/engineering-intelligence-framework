# MCP evaluation questions

**Model evaluation: NOT RUN.** The authorized model-turn budget is zero.
The ten independent [questions](questions.xml) have stable, exact-string answers
on a disposable synthetic fixture. They combine routing, explicit progress,
legacy status, malformed-search coverage, lifecycle filters, checkpoint audit,
bounded doctor coverage and section pagination.

```text
python scripts/tests/test_eif_mcp_eval.py
```

This script creates the fixture and verifies expected answers through the real
in-memory SDK client. It performs ordinary deterministic program operations,
with no model calls. It verifies answer grounding, not an agent's ability to
choose tools, handle ambiguity or complete a task. The actual model evaluation,
matched behavioral comparison and real-client canaries remain deferred. Each
question starts from the same fixed fixture and never requires a previous
question's state or a write through MCP.

Fixture definition: `scripts/tests/fixtures/eif_mcp/seed.py` plus the additional
packet/lifecycle cases in `scripts/tests/test_eif_mcp_eval.py`. Files with current
timestamps, real projects or private instances are not used as answer sources.
