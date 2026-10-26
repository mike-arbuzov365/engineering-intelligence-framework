#!/usr/bin/env python3
"""Inventory a clean, resolved optional-MCP runtime, excluding build tooling."""
from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import re
import sys
from pathlib import Path

from eif_check_licenses import BOOTSTRAP_EXCLUDE, check_package_licenses, license_identifiers, load_policy

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    distributions = [d for d in metadata.distributions() if d.metadata["Name"].lower() not in {*BOOTSTRAP_EXCLUDE, "engineering-intelligence-framework"}]
    if any(d.metadata["Name"].lower() in {"build", "hatchling", "pytest"} for d in distributions):
        print("FAIL: use a clean runtime environment without build/test tooling", file=sys.stderr)
        return 1
    denied, unknown, _ = check_package_licenses(load_policy(ROOT), distributions)
    if denied or unknown:
        print("FAIL: dependency license policy must pass before inventory generation", file=sys.stderr)
        return 1
    if metadata.version("mcp") != "2.1.1":
        print("FAIL: inventory requires the tested SDK pin mcp==2.1.1", file=sys.stderr)
        return 1
    components, pins = [], []
    for dist in sorted(distributions, key=lambda d: d.metadata["Name"].lower()):
        name = re.sub(r"[-_.]+", "-", dist.metadata["Name"].lower())
        licenses = license_identifiers(dist)
        components.append({"type": "library", "name": name, "version": dist.version, "bom-ref": f"pkg:pypi/{name}@{dist.version}", "purl": f"pkg:pypi/{name}@{dist.version}", "licenses": [{"license": {"name": value}} for value in licenses]})
        marker = '; sys_platform == "win32"' if name == "pywin32" else ""
        pins.append(f"{name}=={dist.version}{marker}")
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1, "metadata": {"properties": [{"name": "eif.scope", "value": "optional-mcp-runtime"}, {"name": "eif.python", "value": f"{sys.version_info.major}.{sys.version_info.minor}"}, {"name": "eif.platform", "value": sys.platform}]}, "components": components}
    outputs = {
        ROOT / "sbom-mcp.cdx.json": json.dumps(sbom, indent=2, ensure_ascii=False) + "\n",
        ROOT / "integrations/eif-mcp/constraints.txt": "# Resolved optional runtime; use with pip install -c, not as base requirements.\n" + "\n".join(pins) + "\n",
    }
    for path, content in outputs.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                print(f"FAIL: inventory drift in {path.name}")
                return 1
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    print(f"PASS: optional MCP inventory {len(components)} runtime components")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
