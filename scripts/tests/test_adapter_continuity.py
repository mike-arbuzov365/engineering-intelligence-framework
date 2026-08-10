#!/usr/bin/env python3
"""Перевіряє truthful capability map і model-free handoff для adapters."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from jsonschema import Draft202012Validator

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FRAMEWORK_ROOT / "scripts"))
sys.path.insert(0, str(FRAMEWORK_ROOT / "src"))

from eif_adapters import ADAPTERS  # noqa: E402
from engineering_intelligence_framework.commands import session  # noqa: E402
from engineering_intelligence_framework.workspace_contract import schema_data  # noqa: E402

MATRIX_PATH = FRAMEWORK_ROOT / "adapters" / "parity-matrix.json"
CAPABILITY_NAMES = (
    "same_chat",
    "resume",
    "create_new_chat",
    "open_new_chat",
    "auto_submit",
    "pre_compact",
    "post_compact",
)


def main() -> int:
    results: list[bool] = []

    def check(name: str, condition: bool, detail: object = "") -> None:
        ok = bool(condition)
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f": {detail}"))
        results.append(ok)

    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(
        schema_data("adapter-continuity-capabilities.schema.json")
    )
    errors = sorted(validator.iter_errors(matrix), key=lambda error: list(error.path))
    check(
        "continuity capability matrix matches schema",
        not errors,
        "; ".join(error.message for error in errors),
    )
    check(
        "continuity matrix covers the registered adapter set exactly",
        set(matrix["adapters"]) == set(ADAPTERS),
        sorted(matrix["adapters"]),
    )

    for adapter, entry in sorted(matrix["adapters"].items()):
        check(
            f"{adapter} declares every continuity capability",
            all(name in entry for name in CAPABILITY_NAMES),
        )
        for name in CAPABILITY_NAMES:
            capability = entry[name]
            if capability["auto_action"]:
                check(
                    f"{adapter}.{name} automatic action has observed adapter evidence",
                    capability["status"] == "verified"
                    and capability["enforcement"] == "adapter"
                    and capability["evidence_status"] == "observed",
                    capability,
                )
        check(
            f"{adapter} does not auto-submit prompts",
            entry["auto_submit"]["auto_action"] is False,
        )

    check(
        "no adapter advertises automatic handoff before a complete canary",
        not any(
            entry[name]["auto_action"]
            for entry in matrix["adapters"].values()
            for name in ("create_new_chat", "open_new_chat", "auto_submit")
        ),
    )
    check(
        "Codex open capability remains manual after the inconclusive canary",
        matrix["adapters"]["codex"]["open_new_chat"]["status"] == "manual"
        and matrix["adapters"]["codex"]["open_new_chat"]["evidence_status"]
        == "inconclusive",
    )
    check(
        "Hermes create capability does not claim Desktop control transfer",
        matrix["adapters"]["hermes"]["create_new_chat"]["auto_action"] is False
        and matrix["adapters"]["hermes"]["open_new_chat"]["evidence_status"]
        == "inconclusive",
    )
    check(
        "Cursor resume is documentation-only when local agent CLI is absent",
        matrix["adapters"]["cursor"]["resume"]["evidence_status"]
        == "documentation_only",
    )

    with tempfile.TemporaryDirectory(prefix="eif-continuity-url-") as temp_dir:
        project_root = Path(temp_dir).resolve()
        prompt = "Read checkpoint A & B? Then verify #1."
        link = session._codex_deep_link(project_root, prompt)
        parsed = urlsplit(link)
        decoded = parse_qs(parsed.query)
        check(
            "Codex deep link uses the canonical new-thread route",
            parsed.scheme == "codex" and parsed.netloc == "threads" and parsed.path == "/new",
            link,
        )
        check(
            "Codex deep link round-trips prompt and absolute path",
            decoded == {"prompt": [prompt], "path": [str(project_root)]},
            decoded,
        )
        check(
            "Codex deep link escapes reserved prompt characters",
            "%26" in link and "%3F" in link and "%23" in link and " " not in link,
            link,
        )

        original_audit = session._audit_checkpoint
        try:
            for adapter in sorted(ADAPTERS):
                checkpoint = project_root / ".session-context" / "SESSION-TEST.md"
                data = {
                    "project": {"id": "project-test", "adapter": adapter},
                    "logical_session": {
                        "id": "SESSION-TEST",
                        "continuation_mode": "auto",
                    },
                    "next_action": "Run the focused tests.",
                }
                session._audit_checkpoint = lambda path, root, data=data: (data, [])

                auto_args = argparse.Namespace(
                    checkpoint=str(checkpoint),
                    project_root=str(project_root),
                    mode="auto",
                    open=False,
                )
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    rc = session._handoff(auto_args)
                rendered = output.getvalue()
                check(
                    f"{adapter} auto mode degrades to an explicit manual handoff",
                    rc == 0
                    and "strategy=manual_new_chat" in rendered
                    and f"adapter={adapter}" in rendered
                    and "automation=none" in rendered,
                    rendered,
                )

                open_args = argparse.Namespace(
                    checkpoint=str(checkpoint),
                    project_root=str(project_root),
                    mode="auto",
                    open=True,
                )
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    rc = session._handoff(open_args)
                check(
                    f"{adapter} --open fails closed without verified capability",
                    rc == 1 and "FAIL automatic open is not verified" in output.getvalue(),
                    output.getvalue(),
                )
        finally:
            session._audit_checkpoint = original_audit

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_adapter_continuity: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
