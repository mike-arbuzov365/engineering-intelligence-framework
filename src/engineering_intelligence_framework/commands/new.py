"""`eifctl new` - create a local git repository and connect it to EIF.

The project is assembled in a temporary sibling directory, initialized as a
greenfield EIF instance, optionally `git init`-ed, then atomically renamed
to the requested path. An optional private project registry entry is written
only after the project exists successfully.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .._impl.eif_adapters import ADAPTERS
from . import init_cmd, projects


def run(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="eifctl new", description=__doc__)
    ap.add_argument("path", help="New project directory. It must not already exist.")
    ap.add_argument("--project-name", default=None, help="EIF project name. Default: directory name.")
    ap.add_argument("--adapter", choices=sorted(ADAPTERS), default="claude-code")
    ap.add_argument("--locale", choices=["en", "uk"], default="en")
    ap.add_argument("--knowledge-root", default="knowledge")
    ap.add_argument("--knowledge-index-path", default=None)
    ap.add_argument(
        "--no-manage-knowledge-index",
        action="store_true",
        help="Do not let EIF generate the knowledge index.",
    )
    ap.add_argument("--registry", default=None, help="Private projects.yaml registry to connect after creation.")
    ap.add_argument(
        "--profile",
        default="default",
        help="Workspace professional profile to assign. Requires --registry.",
    )
    ap.add_argument("--no-git", action="store_true", help="Create the EIF instance without `git init`.")
    args = ap.parse_args(argv)

    target = Path(args.path).resolve()
    if target.exists():
        print(f"eifctl new: target already exists: {target}", file=sys.stderr)
        return 1
    if not target.parent.exists():
        print(f"eifctl new: parent directory does not exist: {target.parent}", file=sys.stderr)
        return 1

    registry_path = Path(args.registry).resolve() if args.registry else None
    if registry_path is None and args.profile != "default":
        print("eifctl new: --profile requires --registry", file=sys.stderr)
        return 1
    if registry_path is not None:
        try:
            projects.load_registry(registry_path, allow_missing=True)
            projects.validate_profile_selection(registry_path, args.profile)
        except projects.RegistryError as exc:
            print(f"eifctl new: registry preflight failed: {exc}", file=sys.stderr)
            return 1

    stage: Path | None = Path(tempfile.mkdtemp(prefix=f".{target.name}.eif-new-", dir=target.parent))
    try:
        init_args = [
            "--instance-path", str(stage),
            "--project-name", args.project_name or target.name,
            "--adapter", args.adapter,
            "--locale", args.locale,
            "--knowledge-root", args.knowledge_root,
            "--adoption-mode", "greenfield",
        ]
        if args.knowledge_index_path:
            init_args += ["--knowledge-index-path", args.knowledge_index_path]
        if args.no_manage_knowledge_index:
            init_args.append("--no-manage-knowledge-index")

        rc = init_cmd.run(init_args)
        if rc != 0:
            return rc

        if not args.no_git:
            proc = subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=stage,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode != 0:
                print(f"eifctl new: git init failed: {proc.stderr.strip()}", file=sys.stderr)
                return proc.returncode

        stage.replace(target)
        stage = None  # target now owns the tree; never clean it in finally
    finally:
        if stage is not None and stage.exists():
            shutil.rmtree(stage)

    if registry_path is not None:
        try:
            name, action = projects.register_project(
                registry_path,
                target,
                profile=args.profile,
            )
            print(f"eifctl new: {action} {name} in {registry_path}")
        except projects.RegistryError as exc:
            print(
                f"eifctl new: project was created successfully at {target}, but registry update failed: {exc}",
                file=sys.stderr,
            )
            return 1

    print(f"eifctl new: SUCCESS created EIF project repository at {target}")
    print("eifctl new: next: add project-specific rules below the EIF:END marker, then commit the bootstrap.")
    return 0
