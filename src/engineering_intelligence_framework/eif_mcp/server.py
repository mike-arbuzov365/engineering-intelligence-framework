"""Fixed reader catalog on the public MCPServer dispatch methods (SDK v2)."""
from __future__ import annotations

import asyncio
import concurrent.futures
import datetime as dt
import importlib.metadata
import json
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.server import MCPServer
from mcp.types import CallToolResult, TextContent, Tool

from ..service import Instance, ServiceError
from ..service import operations
from ..service.artifacts import artifact_get
from ..service.packets import packet_status

RESPONSE_BYTES = 24576
BRIEF_BYTES = 4096
READ_SECONDS = 15
CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def wire_bytes(result: CallToolResult) -> int:
    return len(result.model_dump_json(by_alias=True, exclude_none=True).encode("utf-8"))


def _result(payload: dict, error: bool = False) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=compact(payload))], structuredContent=payload, isError=error)


class ReaderServer(MCPServer):
    def __init__(self, instance: Instance, *, deadline: float = READ_SECONDS):
        super().__init__("eif-mcp", version=operations.package_version(), log_level="CRITICAL")
        self.instance = instance
        self.deadline = min(deadline, READ_SECONDS)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="eif-reader")
        self.catalog = {tool["name"]: tool for tool in CATALOG}

    async def list_tools(self) -> list[Tool]:
        return [Tool(**entry) for entry in CATALOG]

    def close(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)

    def _dispatch(self, name: str, arguments: dict[str, Any], elicitation: bool) -> dict:
        self.instance.refresh()
        if name == "eif_capabilities":
            result = operations.capabilities(self.instance, sdk_version=importlib.metadata.version("mcp"), elicitation=elicitation, catalog=[{"name": key, "effect": "read"} for key in self.catalog])
        elif name == "eif_brief":
            result = operations.brief(self.instance, **arguments)
        elif name == "eif_artifact_get":
            result = artifact_get(self.instance, **arguments)
        elif name == "eif_knowledge_search":
            arguments = dict(arguments)
            if "type" in arguments:
                arguments["type_filter"] = arguments.pop("type")
            result = operations.knowledge_search(self.instance, **arguments)
        elif name == "eif_packet_status":
            result = packet_status(self.instance, **arguments)
        elif name == "eif_doctor":
            result = operations.doctor_report(self.instance, **arguments)
        elif name == "eif_session_validate":
            result = operations.session_validate(self.instance, **arguments)
        elif name == "eif_session_resume_audit":
            result = operations.session_resume_audit(self.instance, **arguments)
        else:
            result = operations.delivery_check(self.instance, **arguments)
        state = operations.drift(self.instance)
        result["data"].setdefault("drift", state)
        if state != "match":
            if result["status"] in {"ok", "partial"}:
                result["status"] = "stale" if state == "mismatch" else ("unknown" if result["status"] == "ok" else "partial")
            result.setdefault("next_action", "Install the package version pinned by the instance or run eifctl upgrade --instance-path .")
        return result

    def _sanitize(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._sanitize(item) for item in value]
        if isinstance(value, str):
            root = str(self.instance.root)
            for spelling in (root.replace("\\", "\\\\"), root, self.instance.root.as_posix()):
                value = value.replace(spelling, ".")
            if re.match(r"^(?:[A-Za-z]:[\\/]|/|\\\\)", value):
                return "[outside-instance]"
        return value

    async def call_tool(self, name: str, arguments: dict[str, Any], context=None) -> CallToolResult:
        request_id, started = uuid.uuid4().hex, time.monotonic()
        known_name = name if name in self.catalog else "unknown"
        failed = False
        try:
            if known_name == "unknown":
                raise ServiceError("not_found", "The requested tool is not registered.")
            if not Draft202012Validator(self.catalog[name]["inputSchema"]).is_valid(arguments):
                raise ServiceError("validation_failed", "Arguments do not match the strict tool schema.")
            elicitation = False
            if context is not None:
                try:
                    caps = context.request_context.session.client_capabilities
                    elicitation = caps.elicitation is not None
                except (AttributeError, RuntimeError, ValueError):
                    pass
            # A single physical worker stays serialized after timeout/cancel.
            # Canceling an await cannot terminate a synchronous filesystem read.
            loop = asyncio.get_running_loop()
            future = loop.run_in_executor(self.executor, self._dispatch, name, dict(arguments), elicitation)
            payload = await asyncio.wait_for(future, timeout=self.deadline)
        except ServiceError as error:
            failed = True
            payload = {"status": error.status, "data": {}, "error": {"code": error.code, "message": str(error), "retryable": error.retryable}, "next_action": "Check the instance sources and declared tool arguments."}
        except asyncio.TimeoutError:
            failed = True
            payload = {"status": "unavailable", "data": {}, "error": {"code": "source_unavailable", "message": "The read deadline expired; its worker remains serialized until completion.", "retryable": True}}
        except asyncio.CancelledError:
            failed = True
            payload = {"status": "unavailable", "data": {}, "error": {"code": "cancelled", "message": "The read was cancelled.", "retryable": True}}
        except Exception:
            failed = True
            payload = {"status": "unavailable", "data": {}, "error": {"code": "source_unavailable", "message": "The bounded instance operation could not be completed.", "retryable": False}}
        payload["request_id"] = request_id
        payload = self._sanitize(payload)
        result = _result(payload, failed)
        limit = BRIEF_BYTES if name == "eif_brief" else RESPONSE_BYTES
        if wire_bytes(result) > limit - 128:
            payload = {"status": "truncated", "request_id": request_id, "data": {"reason": "The response exceeds its byte limit."}, "truncated": True, "error": {"code": "result_truncated", "message": "Request a smaller page or narrower result.", "retryable": False}, "next_action": "Use a named section, smaller max_chars or smaller top."}
            result = _result(payload)
        print(compact({"time": dt.datetime.now(dt.timezone.utc).isoformat(), "request_id": request_id, "tool": known_name, "status": payload["status"], "duration_ms": round((time.monotonic() - started) * 1000), "response_bytes": wire_bytes(result)}), file=sys.stderr)
        return result


def create_server(root: Path, packets_root: str = "planning/packets", *, deadline: float = READ_SECONDS) -> ReaderServer:
    return ReaderServer(Instance(root, packets_root), deadline=deadline)


async def self_test(root: Path, packets_root: str = "planning/packets") -> dict:
    parameters = StdioServerParameters(command=sys.executable, args=["-W", "ignore", "-m", "engineering_intelligence_framework.cli", "mcp", "serve", "--instance-path", str(root), "--packets-root", packets_root])
    async with Client(parameters, read_timeout_seconds=20) as client:
        tools = await client.list_tools()
        result = await client.call_tool("eif_capabilities", {})
        value = result.structured_content
        if len(tools.tools) != 9 or not value or value.get("data", {}).get("mode") != "reader":
            raise ServiceError("dependency_unavailable", "Stdio self-test did not return the reader identity.")
        return {"self_test": "pass", "transport": "stdio", "mode": "reader", "tools": 9, "status": value["status"]}
