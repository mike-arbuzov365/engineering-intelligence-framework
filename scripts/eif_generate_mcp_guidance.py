#!/usr/bin/env python3
"""Generate reviewable templates without touching any client's configuration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "integrations/eif-mcp"
TARGETS = {
    "claude-code": ("~/.claude.json", "json", "mcpServers"),
    "codex": ("~/.codex/config.toml", "toml", "mcp_servers"),
    "cursor": ("~/.cursor/mcp.json", "json", "mcpServers"),
    "hermes": ("~/.hermes/config.yaml", "yaml", "mcp_servers"),
}


def outputs() -> dict[Path, str]:
    manifest = json.loads((DEST / "manifest.json").read_text(encoding="utf-8"))
    result = {}
    for adapter, (path, fmt, key) in TARGETS.items():
        entry = {"command": "eifctl", "args": ["mcp", "serve", "--instance-path", "<explicit-instance-root>"]}
        fragment = {key: {"eif": entry}}
        if fmt == "toml":
            snippet = '[mcp_servers.eif]\ncommand = "eifctl"\nargs = ' + json.dumps(entry["args"]) + "\n"
        elif fmt == "yaml":
            snippet = yaml.safe_dump(fragment, sort_keys=False)
        else:
            snippet = json.dumps(fragment, indent=2) + "\n"
        template = {"schema_version": 1, "integration": "eif-mcp", "adapter": adapter, "config_path": path, "config_format": fmt, "config_key": key, "installed": False, "user_config_mutated_by_generator": False, "template_only": True, "data_boundary": "local-only", "modes": {"reader": {"available": True, "server_entry": entry, "native_snippet": snippet}, "writer": {"available": False, "status": "deferred-to-EIF-022b", "server_entry": None}}, "review_before_install": ["Back up your client configuration and review the explicit instance root.", "Use the eifctl from the environment containing the pinned package and mcp extra.", "Never auto-allow eif_commit or automatically accept host elicitation when writers become available.", "Remove this server entry to roll back; EIF does not install or edit client configuration."], "client_canary": "configured-not-verified", "format_evidence": manifest["format_evidence"][adapter]}
        result[DEST / f"generated/{adapter}.json"] = json.dumps(template, indent=2, ensure_ascii=False) + "\n"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, content in outputs().items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                print(f"FAIL: template drift {path.name}")
                return 1
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    print("PASS: four MCP templates; no client configuration was modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
