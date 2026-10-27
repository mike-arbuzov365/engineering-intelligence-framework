"""Non-shipping, model-free cancellation/termination transport fixture."""
import json
import sys
import time
from pathlib import Path

from engineering_intelligence_framework.eif_mcp.server import create_server

server = create_server(Path(sys.argv[1]))
original = server._dispatch


def delayed(*args):
    print(json.dumps({"test": "call_started"}), file=sys.stderr, flush=True)
    time.sleep(1)
    return original(*args)


server._dispatch = delayed
try:
    server.run(transport="stdio")
finally:
    server.close()
