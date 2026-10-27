#!/usr/bin/env python3
"""Opt-in compact routing: real upgrades, fallback, drift and exact rollback."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests")]
from engineering_intelligence_framework._impl.eif_init import _managed_block
from engineering_intelligence_framework.resources import framework_root
from test_service_golden import capture

ADAPTERS = {"claude-code": "CLAUDE.md", "codex": "AGENTS.md", "cursor": ".cursor/rules/eif/governance.mdc", "hermes": ".hermes.md"}


def main() -> int:
    checks = []

    def check(name, value, detail=""):
        checks.append(bool(value))
        print(f"{'PASS' if value else 'FAIL'} {name}" + (": " + detail[-1000:] if not value else ""), flush=True)

    expected = json.loads((ROOT / "scripts/tests/fixtures/eif_mcp/legacy-blocks.json").read_text(encoding="utf-8"))
    with framework_root() as resources:
        for adapter, entry in ADAPTERS.items():
            for mode in ("greenfield", "coexist"):
                check(f"{adapter} {mode} legacy bytes unchanged", _managed_block(resources, "knowledge", "knowledge/index.md", mode, entry, True) == expected[adapter][mode] and _managed_block(resources, "knowledge", "knowledge/index.md", mode, entry, True, eif_mcp=False) == expected[adapter][mode])
                compact = _managed_block(resources, "knowledge", "knowledge/index.md", mode, entry, True, eif_mcp=True)
                check(f"{adapter} {mode} compact block budget", len(compact.encode("utf-8")) <= 2400)
    with tempfile.TemporaryDirectory(prefix="eif-mcp-compact-") as tmp:
        base = Path(tmp).resolve()
        for adapter, entry in ADAPTERS.items():
            for locale in ("en", "uk"):
                label = f"{adapter}/{locale}"
                project = base / f"{adapter}-{locale}"
                created = capture(["new", str(project), "--project-name", "synthetic-compact", "--adapter", adapter, "--locale", locale], base)
                check(label + " instance created", created["rc"] == 0, created["stdout"] + created["stderr"])
                path = project / entry
                legacy = path.read_bytes()
                config_path = project / ".eif/config.yaml"
                config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

                def configure(enabled):
                    config.setdefault("integrations", {})["eif_mcp"] = {"enabled": enabled}
                    config_path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n")

                upgrade = ["upgrade", "--instance-path", str(project), "--allow-dirty-project"]
                configure(False)
                disabled = capture(upgrade, base)
                check(label + " explicit disabled preserves bytes", disabled["rc"] == 0 and path.read_bytes() == legacy, disabled["stdout"] + disabled["stderr"])
                configure(True)
                chosen_config = config_path.read_bytes()
                enabled = capture(upgrade, base)
                compact = path.read_text(encoding="utf-8")
                check(label + " real opt-in upgrade", enabled["rc"] == 0 and "<!-- EIF:MCP reader -->" in compact, enabled["stdout"] + enabled["stderr"])
                check(label + " config preserved by upgrade", config_path.read_bytes() == chosen_config)
                check(label + " fallback and markers", compact.count("<!-- EIF:BEGIN") == compact.count("<!-- EIF:END -->") == 1 and all(token in compact for token in ("eif_brief(task_kind)", "eifctl doctor --instance-path .", 'eifctl search "<query>" --knowledge-root "knowledge"', "operating-protocol.md")))
                health = capture(["doctor", "--instance-path", str(project)], base)
                check(label + " configured never healthy", health["rc"] == 0 and "integration eif_mcp" in health["stdout"] and "state=configured" in health["stdout"], health["stdout"] + health["stderr"])
                path.write_text(compact.replace("eif_brief(task_kind)", "missing-route"), encoding="utf-8", newline="\n")
                drift = capture(["doctor", "--instance-path", str(project)], base)
                check(label + " missing route detected", drift["rc"] == 1 and "compact MCP block" in drift["stdout"])
                path.write_text(compact, encoding="utf-8", newline="\n")
                configure(False)
                rolled_back = capture(upgrade, base)
                check(label + " rollback restores exact legacy bytes", rolled_back["rc"] == 0 and path.read_bytes() == legacy, rolled_back["stdout"] + rolled_back["stderr"])
        # The lightweight path must also respect an unmanaged/coexisting
        # project's retrieval ownership and canonical authority markers.
        with framework_root() as resources:
            text = _managed_block(resources, "external-notes", "external-notes/index.md", "coexist", "AGENTS.md", False, eif_mcp=True)
        check("unmanaged/coexist authority preserved", "knowledge is not managed by EIF" in text and "EIF is NOT this project's sole or" in text)
    schema = json.loads((ROOT / "core/schemas/integration-health-result.schema.json").read_text(encoding="utf-8"))
    fixture = json.loads((ROOT / "scripts/tests/fixtures/integrations/health-disabled.valid.json").read_text(encoding="utf-8"))
    fixture.update(integration="eif_mcp", provider="eif-mcp", state="configured")
    check("configured reader health schema", Draft202012Validator(schema).is_valid(fixture))
    fixture["integration"] = "other-provider"
    check("configured cannot certify another integration", not Draft202012Validator(schema).is_valid(fixture))
    print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
