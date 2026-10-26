#!/usr/bin/env python3
"""SDK-free catalog/template contracts and fail-closed optional inventory tests."""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from eif_check_mcp_licenses import check_inventory
from eif_generate_mcp_guidance import outputs


def main() -> int:
    checks = []

    def check(name, value):
        checks.append(bool(value))
        print(f"{'PASS' if value else 'FAIL'} {name}")

    catalog = json.loads((ROOT / "src/engineering_intelligence_framework/eif_mcp/catalog.json").read_text(encoding="utf-8"))
    check("nine unique reader operations", len({x["name"] for x in catalog}) == len(catalog) == 9)
    for tool in catalog:
        schema = tool["inputSchema"]
        Draft202012Validator.check_schema(schema)
        check(tool["name"] + " declared safe input", schema["additionalProperties"] is False and not ({"path", "command", "sql", "approved", "confirm", "explicit_user_intent"} & schema["properties"].keys()) and len(tool["description"]) <= 280)
    guide = (ROOT / "docs/guides/eif-mcp.md").read_text(encoding="utf-8")
    check("guide catalog parity", all(tool["name"] in guide for tool in catalog))
    for path, expected in outputs().items():
        actual = path.read_text(encoding="utf-8")
        check(path.stem + " template drift", actual == expected)
        value = json.loads(actual)
        if path.stem == "hermes":
            check("Hermes observed YAML target", value["config_path"] == "~/.hermes/config.yaml" and value["config_format"] == "yaml" and value["config_key"] == "mcp_servers")
        check(path.stem + " not installed and writer deferred", value["installed"] is False and value["user_config_mutated_by_generator"] is False and value["modes"]["writer"]["server_entry"] is None)
        snippet = value["modes"]["reader"]["native_snippet"]
        parsed = tomllib.loads(snippet) if value["config_format"] == "toml" else yaml.safe_load(snippet)
        check(path.stem + " native config parses", parsed[value["config_key"]]["eif"]["args"][:2] == ["mcp", "serve"])
    check("optional inventory passes", not check_inventory())
    with tempfile.TemporaryDirectory(prefix="eif-mcp-inventory-") as tmp:
        root = Path(tmp)
        for relative in ("sbom-mcp.cdx.json", "pyproject.toml", "core/policies/license-policy.json", "integrations/eif-mcp/constraints.txt"):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        sbom_path = root / "sbom-mcp.cdx.json"
        original = json.loads(sbom_path.read_text(encoding="utf-8"))
        altered = copy.deepcopy(original)
        altered["components"].pop()
        sbom_path.write_text(json.dumps(altered), encoding="utf-8")
        check("missing dependency fails closed", bool(check_inventory(root)))
        altered = copy.deepcopy(original)
        altered["components"][0]["licenses"] = []
        sbom_path.write_text(json.dumps(altered), encoding="utf-8")
        check("unknown license fails closed", any("unknown" in x for x in check_inventory(root)))
        altered = copy.deepcopy(original)
        altered["components"][0]["licenses"] = [{"license": {"name": "GPL-3.0"}}]
        sbom_path.write_text(json.dumps(altered), encoding="utf-8")
        check("denied license fails closed", any("denied" in x for x in check_inventory(root)))
        altered = copy.deepcopy(original)
        altered["components"].append(altered["components"][0])
        sbom_path.write_text(json.dumps(altered), encoding="utf-8")
        check("duplicate component fails closed", bool(check_inventory(root)))
    print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
