"""Fail-closed preflight for the reader's fixed Git commands."""
from __future__ import annotations

import os
from pathlib import Path
import stat

from ..commands import session
from .instance import ServiceError

_FALLBACK = "Run eifctl session resume-audit directly for this repository."
_REDIRECTS = {"commondir", "gitdir", "config.worktree", "objects/info/alternates", "objects/info/http-alternates"}
_UNSUPPORTED_CONFIG = (
    r"^include(if\..*)?\.path$"
    r"|^filter\..*\.(clean|smudge|process)$"
    r"|^extensions\.(worktreeconfig|partialclone)$"
    r"|^remote\..*\.promisor$"
    r"|^core\.(worktree|attributesfile|excludesfile|alternaterefscommand)$"
)


def _unavailable() -> ServiceError:
    return ServiceError("source_unavailable", "A self-contained Git repository without redirects or executable filters is required. " + _FALLBACK)


def _plain(info: os.stat_result) -> bool:
    # lstat must precede traversal. In
    # particular, Windows junctions are reparse points but not symlinks.
    linked = stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    return not linked and (stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode) and info.st_nlink <= 1))


def preflight(root: Path) -> None:
    """Inspect path metadata before the first Git subprocess, never targets.

    Reject all Git links, worktree/common directories and alternate object
    stores, including contained variants. A bounded metadata walk also guards
    linked refs, HEAD, config, index and object/pack files. No Git config is
    read until the complete walk succeeds.
    """
    git_dir = root / ".git"
    try:
        info = git_dir.lstat()
        if not _plain(info) or not stat.S_ISDIR(info.st_mode):
            raise _unavailable()
        pending = [git_dir]
        count = 0
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    count += 1
                    path = Path(entry.path)
                    if count > 20_000 or path.relative_to(git_dir).as_posix().casefold() in _REDIRECTS:
                        raise _unavailable()
                    # DirEntry.stat reports st_nlink=0 on Windows. lstat
                    # obtains the actual link count without following links.
                    info = path.lstat()
                    if not _plain(info):
                        raise _unavailable()
                    if stat.S_ISDIR(info.st_mode):
                        pending.append(path)
    except OSError:
        raise _unavailable() from None

    # This query cannot expand includes or invoke a filter. Read names only;
    # configured commands/values must never enter diagnostics or responses.
    configured = session._run_git(root, ["config", "--no-includes", "--local", "--name-only", "--get-regexp", _UNSUPPORTED_CONFIG], bounded=True)
    if configured.returncode != 1:
        raise _unavailable()
