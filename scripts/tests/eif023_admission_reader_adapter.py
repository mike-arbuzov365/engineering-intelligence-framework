#!/usr/bin/env python3
"""Exercise the locked acceptance expectations and the local and MCP readers."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests/fixtures/eif_mcp")]

from eif023_admission_contract import FIXTURE, run_contract  # noqa: E402
from engineering_intelligence_framework.service import Instance, ServiceError  # noqa: E402
from engineering_intelligence_framework.service.admission import contract_revision, store_review  # noqa: E402
from engineering_intelligence_framework.service.packets import packet_status  # noqa: E402
from seed import seed  # noqa: E402
from test_service_golden import capture  # noqa: E402


def revision(label):
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def synthetic_launch():
    return {"goal": "Prove the synthetic handoff", "scope": ["src"], "no_touch": ["tests"],
            "criteria": {"A5": "Use only a current accepted review"}}


def native_review(record, instance, data):
    return {
        **{key: value for key, value in record.items() if key != "evidence"},
        "instance": instance.project["id"] if record["instance"] == data["instance"] else record["instance"],
        "base_revision": revision(record["base_revision"]),
        "reviewed_revision": revision(record["reviewed_revision"]),
        "reviewed_contract": contract_revision(synthetic_launch()),
        "criteria": {
            criterion: {
                "result": "pass" if record["decision"] == "accepted" else "fail",
                "evidence": evidence,
            }
            for criterion, evidence in zip(record["criteria"], record["evidence"], strict=True)
        },
    }


def materialize(instance, data):
    folder = instance.root / instance.packets_root / data["packet"]
    sessions = folder / "sessions"
    sessions.mkdir(parents=True)
    order = "\n".join(f"## Session {row['id'].partition('-')[2]}" for row in data["sessions"])
    roadmap = f"---\norchestration_mode: {data['mode']}\n---\n{order}\n"
    (folder / "04-ROADMAP-synthetic.md").write_text(roadmap, encoding="utf-8")
    for row in data["sessions"]:
        entry = {key: row[key] for key in ("id", "status", "depends_on")}
        launch = synthetic_launch()
        if "attempt" in row:
            launch.update(attempt=row["attempt"], base_revision=revision("work-base"),
                          current_revision=revision(row["current_revision"]))
        entry["orchestration"] = launch
        (sessions / f"{row['id']}-synthetic.md").write_text(f"---\n{json.dumps(entry)}\n---\n", encoding="utf-8")
    reviews = folder / "reviews"
    reviews.mkdir()
    for index, record in enumerate(data["reviews"]):
        (reviews / f"fixture-{index}.json").write_text(json.dumps(native_review(record, instance, data)), encoding="utf-8")
    return folder


def adapter(root):
    @contextmanager
    def open_case(data):
        with tempfile.TemporaryDirectory(dir=root, prefix="case-") as packets:
            instance = Instance(root, Path(packets).name)
            materialize(instance, data)

            def read():
                result = packet_status(Instance(root, instance.packets_root), data["packet"])
                body = result["data"]
                return {
                    "legacy": {"status": result["status"], "next_session": body["next_session"],
                               "reason": body["reason"]},
                    "admission": {key: body["admission"][key] for key in (
                        "next_session", "blocker", "reason", "next_action",
                    )},
                }

            yield read
    return open_case


@contextmanager
def open_case(data):
    with tempfile.TemporaryDirectory(prefix="eif-admission-case-") as work:
        root = seed(Path(work) / "project")
        with adapter(root)(data) as read:
            yield read


def check_interfaces(root, fixture, check):
    data = fixture["input"]
    original_review = data["reviews"][0]
    packet = "synthetic-admission"
    session = "SESSION-001"
    instance = Instance(root)
    folder = materialize(instance, {**data, "reviews": []})
    record = native_review(original_review, instance, data)
    candidate = root / "review.json"

    def cli_review(body):
        candidate.write_text(json.dumps(body), encoding="utf-8")
        result = capture(["packet", "record-review", packet, "--record", candidate.name,
                          "--instance-path", str(root)], root)
        return result["rc"], json.loads(result["stdout"])

    def read_status():
        return packet_status(Instance(root), packet, session)["data"]

    incomplete = {**record, "criteria": {}}
    rc, rejected = cli_review(incomplete)
    check("every criterion needs passing evidence", rc == 2 and rejected["error"]["code"] == "validation_failed")
    returned = {**record, "decision": "changes_requested", "reason": "Retry from keyboard."}
    rc, saved = cli_review(returned)
    check("local CLI records a return", rc == 0 and saved["data"]["record"] == "recorded")
    check("a new reader reconstructs the returned revision", read_status()["admission"]["reason"] == "changes_requested")
    rc, replay = cli_review(returned)
    check("identical recording is idempotent", rc == 0 and replay["data"]["record"] == "already_recorded")
    rc, conflict = cli_review(record)
    check("conflicting recording preserves the return", rc == 2 and conflict["error"]["code"] == "review_conflict"
          and read_status()["handoff"]["review"] == returned)

    launch_path = folder / "sessions" / f"{session}-synthetic.md"
    launch = json.loads(launch_path.read_text(encoding="utf-8").splitlines()[1])
    launch["orchestration"].update(attempt=2, current_revision=revision("work-v2"))
    launch_path.write_text(f"---\n{json.dumps(launch)}\n---\n", encoding="utf-8")
    progress = read_status()
    check("a new attempt keeps earlier feedback", progress["admission"]["reason"] == "review_missing"
          and any(row["reason"] == returned["reason"] for row in progress["handoff"]["prior_feedback"]))
    rc, stale = cli_review(returned)
    check("a stale recording fails closed", rc == 2 and stale["error"]["code"] == "version_conflict")
    new_record = {**record, "attempt": 2, "reviewed_revision": revision("work-v2")}
    rejected_record = {**new_record, "decision": "changes_requested", "reason": "Conflicting concurrent decision."}

    def append(body):
        try:
            return store_review(Instance(root), packet, progress, body)
        except ServiceError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(append, (new_record, rejected_record)))
    check("competing local writes cannot overwrite each other", sorted(outcomes) == ["recorded", "review_conflict"]
          and len(list((folder / "reviews").glob("*.json"))) == 2)
    actual = read_status()
    winner = new_record if outcomes[0] == "recorded" else rejected_record
    check("readers see the winning decision", actual["handoff"]["review"] == winner)

    cli_status = capture(["packet", "status", packet, "--session", session, "--instance-path", str(root)], root)
    cli_data = json.loads(cli_status["stdout"])["data"]
    check("CLI status uses the same service data", cli_status["rc"] == 0 and cli_data == actual)
    if importlib.util.find_spec("mcp") is not None:
        from mcp import Client
        from engineering_intelligence_framework.eif_mcp.server import create_server

        async def verify_transport():
            server = create_server(root)
            try:
                async with Client(server) as client:
                    response = await client.call_tool("eif_packet_status", {"packet": packet, "session": session})
                    body = dict(response.structured_content["data"])
                    body.pop("drift")
                    check("MCP and CLI return identical admission and handoff", not response.is_error and body == cli_data)
                    unbound = await client.call_tool("eif_packet_status", {"session": session})
                    check("MCP named handoff requires a packet", unbound.is_error)
            finally:
                server.close()

        asyncio.run(verify_transport())

    (folder / "reviews/parallel.json").write_text(
        json.dumps(rejected_record if winner == new_record else new_record), encoding="utf-8",
    )
    divergent = read_status()
    check("incompatible review records block admission", divergent["admission"]["reason"] == "review_conflict"
          and divergent["handoff"]["review_conflict"] and divergent["handoff"]["review"] is None)


def main():
    results = []

    def check(name, success):
        print(f"{'PASS' if success else 'FAIL'} {name}")
        results.append(bool(success))

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="eif-admission-suite-") as work:
        root = seed(Path(work) / "project")
        check("versioned independent cases", run_contract(fixture, adapter(root)) == 0)
        check_interfaces(root, fixture, check)
        check_contract_changes(root, fixture, check)
    print(f"EIF-RESULT: passed={sum(results)} total={len(results)}")
    return 0 if all(results) else 1


def check_contract_changes(root, fixture, check):
    data = {**fixture["input"], "packet": "contract-edits", "reviews": []}
    instance = Instance(root)
    folder = materialize(instance, data)
    session_id = data["sessions"][0]["id"]

    def status():
        return packet_status(instance, data["packet"], session_id)["data"]

    original = status()
    record = native_review(fixture["input"]["reviews"][0], instance, data)
    record.update(packet=data["packet"], reviewed_contract=original["handoff"]["contract_revision"])
    candidate = root / "contract-review.json"
    candidate.write_text(json.dumps(record), encoding="utf-8")
    args = ["packet", "record-review", data["packet"], "--record", candidate.name, "--instance-path", str(root)]
    check("local CLI accepts the observed contract", capture(args, root)["rc"] == 0
          and status()["admission"]["reason"] == "ready")

    path = folder / "sessions" / f"{session_id}-synthetic.md"
    initial = path.read_text(encoding="utf-8")
    for field, replacement in (("criteria", {"A5": "Check an additional visible outcome"}),
                               ("no_touch", ["private-scope"])):
        launch = json.loads(initial.splitlines()[1])
        launch["orchestration"][field] = replacement
        path.write_text(f"---\n{json.dumps(launch)}\n---\n", encoding="utf-8")
        changed = status()
        check(f"changing {field} invalidates the prior acceptance", changed["admission"]["reason"] == "stale_contract"
              and changed["admission"]["next_session"] is None and changed["handoff"]["review"] is None)
        replay = capture(args, root)
        check(f"stale {field} review cannot be replayed", replay["rc"] == 2
              and json.loads(replay["stdout"])["error"]["code"] == "version_conflict")
    path.write_text(initial, encoding="utf-8")
    history = next((folder / "reviews").glob("*.json"))
    legacy = json.loads(history.read_text(encoding="utf-8"))
    del legacy["reviewed_contract"]
    history.write_text(json.dumps(legacy), encoding="utf-8")
    check("historical acceptance without the reviewed contract needs a new attempt",
          status()["admission"]["reason"] == "stale_contract")
    launch = json.loads(initial.splitlines()[1])
    launch["orchestration"]["attempt"] += 1
    launch["orchestration"]["criteria"]["A5"] = "Check the corrected behavior"
    path.write_text(f"---\n{json.dumps(launch)}\n---\n", encoding="utf-8")
    handoff = status()["handoff"]
    record.update(attempt=handoff["attempt"], reviewed_contract=handoff["contract_revision"])
    candidate.write_text(json.dumps(record), encoding="utf-8")
    check("a new review of the changed contract restores admission",
          capture(args, root)["rc"] == 0 and status()["admission"]["reason"] == "ready"
          and json.loads(history.read_text(encoding="utf-8")) == legacy)


if __name__ == "__main__":
    raise SystemExit(main())
