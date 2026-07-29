"""`eifctl upgrade` - explicit, guarded project-instance upgrade.

The target is always the currently running, installed EIF package. The
command refuses a dirty project by default, verifies the pinned runtime
before changing it when that runtime is present, delegates the transactional
managed-state refresh to the same eif_init implementation as `eifctl init`,
and runs doctor afterward.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

from .. import __version__
from . import doctor, init_cmd


def _load_source_type(instance_path: Path) -> str | None:
    lock_path = instance_path / ".eif" / "framework.lock.yaml"
    if not lock_path.exists():
        return None
    try:
        data = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict):
        return None
    return (data.get("framework") or {}).get("source_type")


def _git_dirty(instance_path: Path) -> tuple[bool, str | None]:
    if not (instance_path / ".git").exists():
        return False, None
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=instance_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return True, proc.stderr.strip() or "git status failed"
    return bool(proc.stdout.strip()), None


def _verify_pinned_runtime(instance_path: Path) -> int:
    script = instance_path / ".eif" / "runtime" / "eif_verify_runtime.py"
    if not script.exists():
        print("eifctl upgrade: pinned runtime is absent; this run will rehydrate it from the installed package.")
        return 0
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [
            sys.executable,
            str(script),
            "--framework-root", str(instance_path / ".eif" / "runtime"),
            "--instance-path", str(instance_path),
        ],
        cwd=instance_path,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode


def run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="eifctl upgrade", description=__doc__)
    ap.add_argument("--instance-path", default=".", help="Existing EIF project instance. Default: current directory.")
    ap.add_argument("--dry-run", action="store_true", help="Plan and validate the upgrade without writing.")
    ap.add_argument(
        "--migrate-source",
        action="store_true",
        help="Explicitly migrate a git/source-bundle instance to installed-package provenance.",
    )
    ap.add_argument(
        "--allow-dirty-project",
        action="store_true",
        help="Proceed despite uncommitted project changes. Unsafe for routine use.",
    )
    ap.add_argument(
        "--defer-workspace-check",
        action="store_true",
        help=(
            "Leave the workspace axis to the caller. Set by "
            "`eifctl projects upgrade`, which materializes the workspace "
            "immediately after this framework-axis run."
        ),
    )
    args = ap.parse_args(argv)

    instance_path = Path(args.instance_path).resolve()
    config_path = instance_path / ".eif" / "config.yaml"
    lock_path = instance_path / ".eif" / "framework.lock.yaml"
    if not config_path.exists() or not lock_path.exists():
        print(
            f"eifctl upgrade: {instance_path} is not a complete EIF instance "
            "(.eif/config.yaml and .eif/framework.lock.yaml are required).",
            file=sys.stderr,
        )
        return 1

    dirty, dirty_error = _git_dirty(instance_path)
    if dirty and not args.allow_dirty_project:
        detail = f" ({dirty_error})" if dirty_error else ""
        print(
            f"eifctl upgrade: project working tree is dirty{detail}; commit or stash "
            "project changes first, or pass --allow-dirty-project explicitly.",
            file=sys.stderr,
        )
        return 1

    source_type = _load_source_type(instance_path)
    if source_type is None:
        print("eifctl upgrade: cannot read framework.source_type from the instance lock.", file=sys.stderr)
        return 1
    if source_type != "installed-package" and not args.migrate_source:
        print(
            f"eifctl upgrade: instance source_type is {source_type!r}, while this "
            f"command upgrades from installed package {__version__}. Re-run with "
            "--migrate-source to acknowledge the provenance change.",
            file=sys.stderr,
        )
        return 1

    if _verify_pinned_runtime(instance_path) != 0:
        print("eifctl upgrade: current pinned runtime failed doctor; refusing to update it.", file=sys.stderr)
        return 1

    print(f"eifctl upgrade: target EIF version {__version__}")
    init_args = ["--instance-path", str(instance_path)]
    if args.dry_run:
        init_args.append("--dry-run")
    if source_type != "installed-package":
        init_args.append("--allow-source-migration")

    rc = init_cmd.run(init_args)
    if rc != 0 or args.dry_run:
        return rc

    doctor_args = ["--instance-path", str(instance_path)]
    if args.defer_workspace_check:
        doctor_args.append(doctor.DEFER_WORKSPACE_FLAG)
    rc = doctor.run(doctor_args)
    if rc == 0:
        print(f"eifctl upgrade: SUCCESS {instance_path} -> {__version__}")
    else:
        print(
            "eifctl upgrade: managed-state refresh completed but post-upgrade doctor failed; "
            "do not commit the changes. Review git diff and restore the previous lock/runtime source.",
            file=sys.stderr,
        )
    return rc
