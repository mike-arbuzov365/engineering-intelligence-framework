"""Local packet progress and immutable review recording."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..service import Instance, ServiceError
from ..service.admission import read_review, store_review
from ..service.instance import identifier
from ..service.packets import packet_status


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="eifctl packet")
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="Read packet progress and optional orchestration admission")
    status.add_argument("packet", nargs="?")
    status.add_argument("--session", help="Read the named session's handoff and review")
    review = sub.add_parser("record-review", help="Append a local orchestrator review")
    review.add_argument("packet")
    review.add_argument("--record", required=True, help="Project-relative path to the review JSON")
    for command in (status, review):
        command.add_argument("--instance-path", required=True)
        command.add_argument("--packets-root", default="planning/packets")
    args = parser.parse_args(argv)
    try:
        instance = Instance(Path(args.instance_path), args.packets_root)
        if args.command == "status":
            outcome = packet_status(instance, args.packet, args.session)
        else:
            packet = identifier(args.packet)
            record = read_review(instance, args.record)
            progress = packet_status(instance, packet, record["session"])["data"]
            state = store_review(instance, packet, progress, record)
            outcome = {"status": "ok", "data": {"record": state, "session": record["session"]}}
    except ServiceError as exc:
        outcome = {"status": exc.status, "error": {"code": exc.code, "message": str(exc)}}
    except (OSError, UnicodeError, ValueError):
        outcome = {"status": "unavailable", "error": {"code": "source_unavailable", "message": "The packet sources could not be read."}}
    print(json.dumps(outcome, ensure_ascii=True, sort_keys=True))
    return 2 if "error" in outcome else 0
