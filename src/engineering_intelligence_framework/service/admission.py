"""Read version-bound reviews and append decisions through the local CLI."""
from __future__ import annotations

import json
import os
import tempfile
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from ..resources import framework_root
from .instance import Instance, ServiceError, digest

MODE = "orchestrated_sequential"
REVIEW_DIR = "reviews"
MAX_REVIEW_BYTES = 32_768
MAX_REVIEW_ENTRIES = 512


@lru_cache(maxsize=2)
def _validator(kind: str) -> Draft202012Validator:
    with framework_root() as root:
        schema = json.loads((root / "core/schemas/packet-orchestration.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator({"$defs": schema["$defs"], "$ref": f"#/$defs/{kind}"})


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("Duplicate review key")
    return value


def read_review(instance: Instance, relative: str) -> dict:
    raw = instance.read(relative, limit=MAX_REVIEW_BYTES)
    try:
        body = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_keys)
    except (ValueError, RecursionError):
        raise ServiceError("validation_failed", "A packet review is not a valid JSON record.") from None
    if not _validator("review").is_valid(body):
        raise ServiceError("validation_failed", "A packet review does not satisfy the review schema.")
    return body


def _scope_matches(instance: Instance, packet: str, record: dict) -> bool:
    return record["instance"] == instance.project["id"] and record["packet"] == packet


def _review_directory(instance: Instance, packet: str) -> Path:
    folder = instance.safe(f"{instance.packets_root}/{packet}")
    directory = instance.safe((folder / REVIEW_DIR).relative_to(instance.root))
    if directory.resolve().parent != folder.resolve():
        raise ServiceError("source_unavailable", "The review directory must belong to the selected packet.")
    return directory


def _review_groups(instance: Instance, packet: str) -> dict[str, list[dict]]:
    folder = _review_directory(instance, packet)
    reviews: dict[str, list[dict]] = defaultdict(list)
    if not folder.exists():
        return reviews
    with os.scandir(folder) as entries:
        for number, entry in enumerate(entries, 1):
            if number > MAX_REVIEW_ENTRIES:
                raise ServiceError("source_unavailable", "Packet review sources exceed reader limits.")
            if entry.name.endswith(".json"):
                path = Path(entry.path)
                if path.resolve().parent != folder.resolve():
                    raise ServiceError("source_unavailable", "A review source leaves the review directory.")
                record = read_review(instance, path.relative_to(instance.root).as_posix())
                if _scope_matches(instance, packet, record):
                    reviews[record["session"]].append(record)
    return reviews


def _same_submission(launch: dict, review: dict) -> bool:
    return review["attempt"] == launch.get("attempt") and review["reviewed_revision"] == launch.get("current_revision")


def _matches_revision(launch: dict, review: dict) -> bool:
    return _same_submission(launch, review) and review["base_revision"] == launch.get("base_revision")


def contract_revision(launch: dict) -> str:
    """Identify the scope and expectations the reviewer actually inspected."""
    contract = {key: launch[key] for key in ("goal", "scope", "no_touch", "criteria")}
    canonical = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + digest(canonical.encode("utf-8"))


def _covers_criteria(launch: dict, review: dict) -> bool:
    return (
        set(review["criteria"]) == set(launch["criteria"])
        and all(item["result"] == "pass" for item in review["criteria"].values())
    )


def _decision(reason: str, action: str, *, blocker: str | None = None, ready: str | None = None) -> dict:
    return {
        "mode": MODE,
        "next_session": ready,
        "blocker": blocker,
        "reason": reason,
        "next_action": action,
        "enforcement": "machine",
        "review_authority": "instruction_only",
    }


def invalid_mode() -> dict:
    return _decision("invalid_orchestration_mode", "inspect_roadmap")


def _evaluate(rows: list[dict], launches: dict[str, dict], reviews: dict[str, list[dict]], progress_reason: str | None) -> dict:
    if progress_reason in {"missing_or_ambiguous_session_order", "invalid_or_cyclic_dependencies"}:
        return _decision(progress_reason, "inspect_roadmap")
    legacy = next((row["id"] for row in rows if row["status"] == "legacy"), None)
    if legacy:
        return _decision("unsupported_status", "inspect_source_status", blocker=legacy)

    accepted: set[str] = set()
    active = {row["id"] for row in rows if row["status"] == "in_progress"}
    for row in rows:
        session_id = row["id"]
        status = row["status"]
        if status == "blocked":
            return _decision("session_blocked", "resolve_blocker", blocker=session_id)
        if status == "deferred":
            return _decision("session_deferred", "resolve_roadmap", blocker=session_id)
        launch = launches[session_id]["orchestration"]
        if not _validator("launch").is_valid(launch):
            return _decision("invalid_handoff", "inspect_launch", blocker=session_id)
        if not all(dep in accepted for dep in row["depends_on"]):
            return _decision("dependency_not_accepted", "inspect_roadmap", blocker=session_id)
        if status in {"prepared", "in_progress"}:
            if active - {session_id}:
                return _decision("parallel_sessions", "reconcile_active_sessions", blocker=session_id)
            if status == "in_progress":
                return _decision("session_in_progress", "resume_session", blocker=session_id)
            return _decision("ready", "start_next_session", ready=session_id)

        attempt = launch.get("attempt")
        submitted = [record for record in reviews.get(session_id, []) if record["attempt"] == attempt]
        if not submitted or not launch.get("current_revision"):
            return _decision("review_missing", "review_current_attempt", blocker=session_id)
        matching = [record for record in submitted if _same_submission(launch, record)]
        if not matching:
            return _decision("stale_revision", "review_current_revision", blocker=session_id)
        record = matching[0]
        if any(other != record for other in matching[1:]):
            return _decision("review_conflict", "reconcile_review_records", blocker=session_id)
        if not _matches_revision(launch, record):
            return _decision("stale_revision", "review_current_revision", blocker=session_id)
        if record["decision"] == "changes_requested":
            return _decision("changes_requested", "revise_and_resubmit", blocker=session_id)
        if record.get("reviewed_contract") != contract_revision(launch):
            return _decision("stale_contract", "submit_new_attempt", blocker=session_id)
        if not _covers_criteria(launch, record):
            return _decision("criteria_unverified", "review_current_attempt", blocker=session_id)
        accepted.add(session_id)
    return _decision("packet_complete", "close_packet")


def read_admission(
    instance: Instance, packet: str, rows: list[dict], launches: dict[str, dict],
    progress_reason: str | None, session: str | None,
) -> tuple[dict, dict | None]:
    try:
        reviews = _review_groups(instance, packet)
    except (ServiceError, OSError, RuntimeError):
        return _decision("review_source_invalid", "inspect_reviews"), None
    decision = _evaluate(rows, launches, reviews, progress_reason)
    if session is None:
        return decision, None
    entry = launches.get(session)
    if entry is None:
        raise ServiceError("not_found", "The session identifier is not present in this packet.")
    launch = entry["orchestration"]
    if not _validator("launch").is_valid(launch):
        return decision, {"session": session, "launch_path": entry["path"], "reason": "invalid_handoff"}
    related = sorted(reviews.get(session, []), key=lambda row: (row["attempt"], row["reviewed_revision"], row["decision"]))
    current = [record for record in related if _same_submission(launch, record)]
    prior = [record for record in related if record["decision"] == "changes_requested" and record not in current]
    conflict = bool(current and any(row != current[0] for row in current))
    contract = contract_revision(launch)
    review = current[0] if current and not conflict and _matches_revision(launch, current[0]) else None
    if review and review["decision"] == "accepted" and review.get("reviewed_contract") != contract:
        review = None
    return decision, {
        "session": session, "launch_path": entry["path"], **launch,
        "contract_revision": contract, "review": review,
        "review_conflict": conflict,
        "prior_feedback": [
            {field: row[field] for field in ("attempt", "reviewed_revision", "reason")}
            for row in prior[-2:]
        ],
    }


def store_review(instance: Instance, packet: str, progress: dict, record: dict) -> str:
    handoff = progress.get("handoff") or {}
    admission = progress.get("admission") or {}
    if admission.get("mode") != MODE or admission.get("reason") == "invalid_orchestration_mode":
        raise ServiceError("validation_failed", "The packet must select sequential orchestration.")
    if not _scope_matches(instance, packet, record) or record["session"] != handoff.get("session"):
        raise ServiceError("validation_failed", "The review must target the current instance, packet and session.")
    if not _matches_revision(handoff, record):
        raise ServiceError("version_conflict", "The submitted attempt or revision changed.", status="stale")
    if not record.get("reviewed_contract") or record["reviewed_contract"] != handoff.get("contract_revision"):
        raise ServiceError("version_conflict", "Read the current handoff and review its contract before recording.", status="stale")
    if handoff["review_conflict"]:
        raise ServiceError("review_conflict", "Reconcile the conflicting review records before appending.")
    if handoff["review"] == record:
        return "already_recorded"
    if handoff["review"] is not None:
        raise ServiceError("review_conflict", "A different decision exists for this attempt and revision.")
    if admission["blocker"] != record["session"] or admission["reason"] not in {"review_missing", "stale_revision"}:
        raise ServiceError("validation_failed", "The packet is not waiting for this session's review.")
    if record["decision"] == "accepted" and not _covers_criteria(handoff, record):
        raise ServiceError("validation_failed", "Acceptance requires passing evidence for every declared criterion.")

    directory = _review_directory(instance, packet)
    directory.mkdir(exist_ok=True)
    revision = digest(record["reviewed_revision"].encode("ascii"))
    name = f"{record['session']}-{record['attempt']}-{revision}.json"
    target = instance.safe((directory / name).relative_to(instance.root))
    content = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(content) > MAX_REVIEW_BYTES:
        raise ServiceError("validation_failed", "The serialized review exceeds reader limits.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".review-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link publishes the complete file atomically and cannot replace
        # another writer's decision. The temporary name never matches *.json.
        os.link(temporary, target)
    except FileExistsError:
        if read_review(instance, target.relative_to(instance.root).as_posix()) == record:
            return "already_recorded"
        raise ServiceError("review_conflict", "A concurrent writer recorded a different decision.") from None
    except OSError:
        raise ServiceError("source_unavailable", "Could not append an immutable review on this filesystem.") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return "recorded"
