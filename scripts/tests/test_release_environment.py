#!/usr/bin/env python3
"""Перевіряє isolation ambient Python paths у local release gate."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import eif_release  # noqa: E402


def check(name: str, condition: bool, detail: str = "") -> tuple[bool, str]:
    return (
        condition,
        f"{'PASS' if condition else 'FAIL'} {name}"
        + (f": {detail}" if detail and not condition else ""),
    )


def main() -> int:
    captured: dict = {}
    real_run = eif_release.subprocess.run
    old_pythonpath = os.environ.get("PYTHONPATH")
    old_pythonhome = os.environ.get("PYTHONHOME")
    old_sentinel = os.environ.get("EIF_RELEASE_ENV_SENTINEL")

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    try:
        os.environ["PYTHONPATH"] = "ambient-site-packages"
        os.environ["PYTHONHOME"] = "ambient-python-home"
        os.environ["EIF_RELEASE_ENV_SENTINEL"] = "preserved"
        eif_release.subprocess.run = fake_run
        eif_release.run(["synthetic-command"])
    finally:
        eif_release.subprocess.run = real_run
        for name, value in (
            ("PYTHONPATH", old_pythonpath),
            ("PYTHONHOME", old_pythonhome),
            ("EIF_RELEASE_ENV_SENTINEL", old_sentinel),
        ):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    child_env = captured.get("env")
    results = [
        check(
            "release subprocess receives explicit environment",
            isinstance(child_env, dict),
            repr(captured),
        ),
        check(
            "ambient Python import paths are removed",
            isinstance(child_env, dict)
            and "PYTHONPATH" not in child_env
            and "PYTHONHOME" not in child_env,
            repr(child_env),
        ),
        check(
            "unrelated environment remains available",
            isinstance(child_env, dict)
            and child_env.get("EIF_RELEASE_ENV_SENTINEL") == "preserved",
            repr(child_env),
        ),
    ]

    for _passed, message in results:
        print(message)
    passed = sum(1 for condition, _message in results if condition)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
