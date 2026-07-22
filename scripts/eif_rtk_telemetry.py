#!/usr/bin/env python3
"""Record and summarize content-free local RTK route counters.

The event schema deliberately has no command, argv, cwd, path or output field.
Raw proxy, parse failure and unsupported routes always record zero savings.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import uuid
from collections import defaultdict
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


def _framework_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _store_path(instance_root: Path) -> Path:
    return instance_root.resolve() / ".eif" / "local-state" / "rtk-telemetry.jsonl"


def _schema(framework_root: Path) -> dict:
    return json.loads(
        (framework_root / "core" / "schemas" / "rtk-telemetry-event.schema.json").read_text(encoding="utf-8")
    )


def _registry_version(framework_root: Path) -> str:
    registry = json.loads(
        (framework_root / "integrations" / "rtk" / "command-registry.json").read_text(encoding="utf-8")
    )
    return registry["registry_version"]


def _token_estimate(byte_count: int) -> int:
    return (byte_count + 3) // 4


def build_event(args: argparse.Namespace, framework_root: Path) -> dict:
    savings_eligible = args.route in {"native-filtered", "native-guarded", "summary-filtered"}
    raw_tokens = _token_estimate(args.raw_bytes)
    emitted_tokens = _token_estimate(args.emitted_bytes)
    saved_tokens = max(0, raw_tokens - emitted_tokens) if savings_eligible else 0
    return {
        "schema_version": 1,
        "event_id": uuid.uuid4().hex,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "integration": "rtk",
        "registry_version": _registry_version(framework_root),
        "command_class": args.command_class,
        "route": args.route,
        "outcome": args.outcome,
        "raw_bytes": args.raw_bytes,
        "emitted_bytes": args.emitted_bytes,
        "estimated_raw_tokens": raw_tokens,
        "estimated_emitted_tokens": emitted_tokens,
        "estimated_saved_tokens": saved_tokens,
        "savings_eligible": savings_eligible,
    }


def validate_event(event: dict, framework_root: Path) -> list[str]:
    validator = Draft202012Validator(_schema(framework_root), format_checker=FormatChecker())
    return [error.message for error in validator.iter_errors(event)]


def cmd_record(args: argparse.Namespace) -> int:
    framework_root = Path(args.framework_root).resolve() if args.framework_root else _framework_root()
    event = build_event(args, framework_root)
    errors = validate_event(event, framework_root)
    if errors:
        print("eif-rtk-telemetry: event rejected")
        for error in errors:
            print(f"  - {error}")
        return 1
    store = _store_path(Path(args.instance_root))
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    print(
        "eif-rtk-telemetry: recorded "
        f"class={event['command_class']} route={event['route']} outcome={event['outcome']} "
        f"estimated_saved_tokens={event['estimated_saved_tokens']}"
    )
    return 0


def _load_events(store: Path, framework_root: Path) -> tuple[list[dict], list[str]]:
    if not store.exists():
        return [], []
    events, errors = [], []
    for line_number, line in enumerate(store.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"line {line_number}: invalid JSON")
            continue
        event_errors = validate_event(event, framework_root)
        if event_errors:
            errors.append(f"line {line_number}: schema invalid")
            continue
        events.append(event)
    return events, errors


def cmd_summary(args: argparse.Namespace) -> int:
    framework_root = Path(args.framework_root).resolve() if args.framework_root else _framework_root()
    store = _store_path(Path(args.instance_root))
    events, errors = _load_events(store, framework_root)
    if errors:
        print("eif-rtk-telemetry: invalid local store")
        for error in errors:
            print(f"  - {error}")
        return 1
    grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"events": 0, "raw_bytes": 0, "emitted_bytes": 0, "estimated_saved_tokens": 0}
    )
    for event in events:
        bucket = grouped[(event["command_class"], event["route"])]
        bucket["events"] += 1
        bucket["raw_bytes"] += event["raw_bytes"]
        bucket["emitted_bytes"] += event["emitted_bytes"]
        bucket["estimated_saved_tokens"] += event["estimated_saved_tokens"]
    summary = {
        "schema_version": 1,
        "events": len(events),
        "groups": [
            {"command_class": key[0], "route": key[1], **values}
            for key, values in sorted(grouped.items())
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--instance-root", default=".")
    record.add_argument("--framework-root")
    record.add_argument("--command-class", required=True)
    record.add_argument(
        "--route",
        required=True,
        choices=["native-filtered", "native-guarded", "summary-filtered", "raw-proxy", "parse-failure", "unsupported"],
    )
    record.add_argument("--outcome", required=True, choices=["success", "failure", "degraded"])
    record.add_argument("--raw-bytes", required=True, type=int)
    record.add_argument("--emitted-bytes", required=True, type=int)
    record.set_defaults(func=cmd_record)

    summary = sub.add_parser("summary")
    summary.add_argument("--instance-root", default=".")
    summary.add_argument("--framework-root")
    summary.set_defaults(func=cmd_summary)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if getattr(args, "raw_bytes", 0) < 0 or getattr(args, "emitted_bytes", 0) < 0:
        print("eif-rtk-telemetry: byte counts must be non-negative")
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
