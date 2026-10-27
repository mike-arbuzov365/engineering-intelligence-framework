#!/usr/bin/env python3
"""Fail-closed license and pin coverage check for the separate MCP inventory."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

from eif_check_licenses import check_sbom_licenses, load_policy

ROOT = Path(__file__).resolve().parents[1]


def check_inventory(root: Path = ROOT) -> list[str]:
    try:
        sbom = json.loads((root / "sbom-mcp.cdx.json").read_text(encoding="utf-8"))
        lines = (root / "integrations/eif-mcp/constraints.txt").read_text(encoding="utf-8").splitlines()
        pins = {}
        for line in lines:
            if not line.strip() or line.startswith("#"):
                continue
            match = re.fullmatch(r'([a-z0-9-]+)==([A-Za-z0-9.!+_-]+)(?:; sys_platform == "win32")?', line)
            if not match or match.group(1) in pins:
                return ["constraints must contain unique exact pins and only the documented Windows marker"]
            pins[match.group(1)] = match.group(2)
        components = sbom["components"]
        versions = {item["name"]: item["version"] for item in components}
        if len(versions) != len(components) or versions != pins:
            return ["SBOM components and resolved constraints differ"]
        if pins.get("mcp") != "2.1.1" or pins.get("mcp-types") != "2.1.1":
            return ["SDK pin is missing or untested"]
        extra = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"]["mcp"]
        if extra != ["mcp>=2.1.1,<3"]:
            return ["optional extra differs from the tested lower-bound contract"]
        denied, unknown, _ = check_sbom_licenses(load_policy(root), components)
        return [*("denied: " + str(item) for item in denied), *("unknown: " + str(item) for item in unknown)]
    except (OSError, ValueError, KeyError, TypeError):
        return ["optional inventory is missing or malformed"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework-root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = check_inventory(args.framework_root)
    for error in errors:
        print("FAIL: " + error)
    print("PASS: optional MCP license inventory and exact constraints" if not errors else "FAIL: optional MCP license contour")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
