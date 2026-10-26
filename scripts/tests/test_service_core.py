#!/usr/bin/env python3
"""Real synthetic sources, boundary attacks, explicit progress and pagination."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts/tests")]
from engineering_intelligence_framework import cli
from engineering_intelligence_framework.service import Instance, ServiceError
from engineering_intelligence_framework.service.artifacts import artifact_get
from engineering_intelligence_framework.service.operations import brief, capabilities, delivery_check, doctor_report, knowledge_search, session_validate
from engineering_intelligence_framework.service.packets import packet_status
from test_service_golden import capture


def main() -> int:
    checks = []

    def check(name, value):
        checks.append(bool(value))
        print(f"{'PASS' if value else 'FAIL'} {name}")

    def error(name, callback, code=None):
        try:
            callback()
        except ServiceError as exc:
            check(name, code is None or exc.code == code)
        else:
            check(name, False)

    with tempfile.TemporaryDirectory(prefix="eif-service-") as tmp:
        base = Path(tmp).resolve()
        root = base / "project"
        check("real new instance", capture(["new", str(root), "--project-name", "synthetic-service", "--adapter", "claude-code"], base)["rc"] == 0)
        instance = Instance(root)
        check("identity", capabilities(instance)["data"]["instance"]["id"].startswith("synthetic-service-"))
        check("bounded doctor discloses omitted checks", doctor_report(instance)["status"] == "partial" and bool(doctor_report(instance)["data"]["skipped_checks"]))
        check("no applicable design guard", delivery_check(instance, "package", "demo")["status"] == "unavailable")
        kinds = json.loads((ROOT / "src/engineering_intelligence_framework/service/task_kinds.json").read_text(encoding="utf-8"))
        check("ten explicit task kinds", len(kinds) == 10)
        check("task routes exist in package", all(name is None or (ROOT / f"skills/{name}/SKILL.md").is_file() for name in kinds.values()))
        check("light has no skill", brief(instance, "light")["data"]["route"] is None)
        check("packet route uses manifest", brief(instance, "packet_run")["data"]["route"]["skill"] == "run-execution-packet")
        error("unknown kind", lambda: brief(instance, "invented"), "validation_failed")
        outline = artifact_get(instance, "playbook", "execution-packet-execution")
        slug = outline["data"]["sections"][0]["slug"]
        page = artifact_get(instance, "playbook", "execution-packet-execution", slug, 8)
        check("truncation explicit", page["status"] == "truncated" and len(page["data"]["text"]) == 8 and bool(page.get("next_cursor")))
        next_page = artifact_get(instance, "playbook", "execution-packet-execution", slug, 8, page["next_cursor"])
        check("cursor advances", page["data"]["text"] != next_page["data"]["text"])
        error("cursor bound to section", lambda: artifact_get(instance, "skill", "run-execution-packet", "different", 8, page["next_cursor"]))
        for saved in instance.cursors.values():
            saved["expires"] = 0
        error("cursor expiry", lambda: artifact_get(instance, "playbook", "execution-packet-execution", slug, 8, page["next_cursor"]), "validation_failed")
        for name in ("../secret", "C:/outside", "/outside", "..", "secrets"):
            error(f"name rejected {name}", lambda name=name: artifact_get(instance, "skill", name))
        error("section path rejected", lambda: artifact_get(instance, "skill", "run-execution-packet", "../outside"), "validation_failed")
        error("unknown artifact", lambda: artifact_get(instance, "skill", "unknown"), "not_found")
        target = root / ".eif/runtime/skills/run-execution-packet/SKILL.md"
        original = target.read_bytes()
        target.write_bytes(original + b"changed")
        error("tampered artifact stale", lambda: artifact_get(instance, "skill", "run-execution-packet"), "version_conflict")
        target.write_bytes(original)
        error("session id traversal", lambda: session_validate(instance, "../other"), "validation_failed")
        error("missing checkpoint", lambda: session_validate(instance, "absent"), "not_found")
        knowledge = root / "knowledge"
        knowledge.mkdir(exist_ok=True)
        (knowledge / "fact.md").write_text("---\ntype: fact\nstatus: validated\nscope: project\nevidence: OBSERVED\nsource: code\ncreated: 2026-07-15\n---\n# Synthetic result\nSynthetic.\n", encoding="utf-8")
        check("knowledge result", len(knowledge_search(instance, "synthetic")["data"]["results"]) == 1)
        check("known empty coverage", knowledge_search(instance, "nomatch")["data"]["coverage"]["indexed"] == 1)
        (knowledge / "malformed.md").write_text("---\n[broken: yaml\n---\n", encoding="utf-8")
        check("malformed coverage partial", knowledge_search(instance, "nomatch")["status"] == "partial")
        instance.config["knowledge"]["root"] = str(base)
        error("external knowledge root rejected", lambda: knowledge_search(instance, "query"))
        instance.refresh()
        packet = root / "planning/packets/demo"
        (packet / "sessions").mkdir(parents=True)
        (packet / "04-ROADMAP-demo.md").write_text("## Session 002\n## Session 001\n", encoding="utf-8")
        for number, status, dependencies in ((1, "prepared", []), (2, "prepared", ["SESSION-001"])):
            data = {"id": f"SESSION-{number:03d}", "status": status, "depends_on": dependencies}
            (packet / f"sessions/SESSION-{number:03d}-demo.md").write_text("---\n" + yaml.safe_dump(data) + "---\n", encoding="utf-8")
        check("next session respects dependencies", packet_status(instance, "demo")["data"]["next_session"] == "SESSION-001")
        first = packet / "sessions/SESSION-001-demo.md"
        first.write_text(first.read_text(encoding="utf-8").replace("prepared", "completed"), encoding="utf-8")
        check("next session follows roadmap", packet_status(instance, "demo")["data"]["next_session"] == "SESSION-002")
        first.write_text(first.read_text(encoding="utf-8").replace("completed", "prepared-awaiting-owner-approval"), encoding="utf-8")
        check("legacy never completion", packet_status(instance, "demo")["status"] == "partial" and packet_status(instance, "demo")["data"]["next_session"] is None)
        first.write_text("---\nid: SESSION-001\nstatus: prepared\ndepends_on: [SESSION-002]\n---\n", encoding="utf-8")
        check("cycle partial", packet_status(instance, "demo")["data"]["reason"] == "invalid_or_cyclic_dependencies")
        error("packet traversal", lambda: packet_status(instance, "../demo"), "validation_failed")
        outside = base / "outside.md"
        outside.write_text("external sentinel", encoding="utf-8")
        try:
            (knowledge / "link.md").symlink_to(outside)
        except OSError:
            import os
            import subprocess
            if os.name == "nt":
                external = base / "outside"
                external.mkdir()
                (external / "sentinel.md").write_text("outside", encoding="utf-8")
                junction = knowledge / "external"
                result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", f"New-Item -ItemType Junction -Path '{junction}' -Target '{external}' | Out-Null"], capture_output=True)
                check("junction fixture created", result.returncode == 0)
                if result.returncode == 0:
                    error("knowledge junction containment", lambda: knowledge_search(instance, "outside"), "source_unavailable")
                    os.rmdir(junction)
            else:
                check("symlink fixture required", False)
        else:
            error("knowledge symlink containment", lambda: knowledge_search(instance, "sentinel"), "source_unavailable")
            (knowledge / "link.md").unlink()
        runtime = root / ".eif/runtime"
        runtime.rename(root / ".eif/runtime-saved")
        error("missing runtime", lambda: artifact_get(instance, "skill", "run-execution-packet"), "source_unavailable")
        (root / ".eif/runtime-saved").rename(runtime)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            artifact_get(instance, "skill", "run-execution-packet")
        check("structured functions are silent", out.getvalue() == "")
    print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
