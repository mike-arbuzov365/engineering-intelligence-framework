"""Optional MCP command; help and the base CLI never import the SDK."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="eifctl mcp", description="Optional instance-bound stdio reader (install the mcp extra).")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Serve nine read-only tools over stdio")
    serve.add_argument("--instance-path", help="Explicit EIF root; overrides EIF_INSTANCE_PATH")
    serve.add_argument("--packets-root", default="planning/packets", help="Packet directory relative to the instance")
    serve.add_argument("--self-test", action="store_true", help="Check a child server with a real SDK stdio client")
    args = parser.parse_args(argv)
    try:
        from ..eif_mcp.server import create_server, self_test
    except ImportError:
        print('eifctl mcp: install the optional dependency: pip install "engineering-intelligence-framework[mcp]"', file=sys.stderr)
        return 2
    from ..service import ServiceError
    raw_root = args.instance_path or os.environ.get("EIF_INSTANCE_PATH")
    if not raw_root:
        print("eifctl mcp: --instance-path or EIF_INSTANCE_PATH is required; no current-directory fallback", file=sys.stderr)
        return 3
    try:
        server = create_server(Path(raw_root), args.packets_root)
    except (ServiceError, OSError, ValueError):
        print("eifctl mcp: invalid instance; config and framework lock must pass their schemas", file=sys.stderr)
        return 3
    try:
        if args.self_test:
            print(json.dumps(asyncio.run(self_test(server.instance.root, args.packets_root)), separators=(",", ":")))
        else:
            server.run(transport="stdio")
    except KeyboardInterrupt:
        return 0
    except Exception:
        print("eifctl mcp: stdio operation failed; check the instance and optional dependency", file=sys.stderr)
        return 2
    finally:
        server.close()
    return 0
