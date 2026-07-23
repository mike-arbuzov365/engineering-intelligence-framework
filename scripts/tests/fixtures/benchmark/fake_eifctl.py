#!/usr/bin/env python3
"""Minimal deterministic eifctl init double for benchmark contract tests.

It writes only the installed-package provenance lock consumed by
eif_benchmark.py. It is never release or behavioral evidence for eifctl itself;
the real wheel journey is covered by test_benchmark_mode_b.py and
test_package_build.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml


def main(argv: list[str]) -> int:
    if not argv or argv[0] != "init" or "--instance-path" not in argv:
        return 2
    instance = Path(argv[argv.index("--instance-path") + 1])
    runtime = instance / ".eif"
    runtime.mkdir(parents=True, exist_ok=True)
    lock = {
        "framework": {"source_type": "installed-package"},
        "package": {
            "distribution": "engineering-intelligence-framework",
            "version": "0.1.0-contract-test",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "resource_manifest_digest": "sha256:" + "1" * 64,
            "wheel_sha256": "2" * 64,
        },
    }
    (runtime / "framework.lock.yaml").write_text(
        yaml.safe_dump(lock, sort_keys=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
