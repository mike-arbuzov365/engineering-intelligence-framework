"""eifctl - installable console entry point for the Engineering
Intelligence Framework. Dispatches to a thin per-subcommand wrapper in
commands/, each of which calls straight into the existing, tested
scripts/eif_*.py logic (synced byte-for-byte into _impl/ - see
scripts/sync_package_sources.py). This file only dispatches. Lifecycle
coordination for `new`, `upgrade`, and `projects` lives in their command
modules; framework primitives remain in the synced implementations.

Compatibility note: the standalone `python scripts/eif_init.py ...` form
(and its siblings) keeps working unchanged - eifctl is an additional,
packaged way to run the same underlying code, not a replacement for it.

Usage:
    eifctl init [--project-name NAME] [--instance-path PATH] ...
    eifctl new PATH [--project-name NAME] [--registry PATH] ...
    eifctl upgrade [--instance-path PATH] [--dry-run]
    eifctl projects {add,remove,status,upgrade} ...
    eifctl workspace {new,doctor} ...
    eifctl doctor [--instance-path PATH]
    eifctl search QUERY [--knowledge-root PATH] ...
    eifctl render {knowledge-delta,session-closeout,message} ...
    eifctl privacy-scan [--repo PATH] ...
    eifctl validate [PATTERNS ...]
    eifctl version
"""
from __future__ import annotations

import sys

from .commands import doctor, init_cmd, new, privacy_scan, projects, render, search, upgrade, validate, version, workspace

COMMANDS = {
    "init": init_cmd.run,
    "new": new.run,
    "upgrade": upgrade.run,
    "projects": projects.run,
    "workspace": workspace.run,
    "doctor": doctor.run,
    "search": search.run,
    "render": render.run,
    "privacy-scan": privacy_scan.run,
    "validate": validate.run,
    "version": version.run,
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv and argv[0] in ("-h", "--help") else 2

    command, rest = argv[0], argv[1:]
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"eifctl: unknown command {command!r} - one of: {', '.join(sorted(COMMANDS))}", file=sys.stderr)
        return 2

    return handler(rest)


if __name__ == "__main__":
    raise SystemExit(main())
