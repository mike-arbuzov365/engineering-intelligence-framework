#!/usr/bin/env python3
"""Build the distribution artifacts for the `engineering-intelligence-framework`
package, prove they are valid for a package index, and prove the built wheel
installs and runs in a clean environment.

This script never uploads anything. Publication is an owner action with owner
credentials: the last thing this prints is the exact command to run, and it
stops there. That boundary is deliberate and matches the rest of the
framework - EIF generates what a person then chooses to execute.

Usage:
    python scripts/eif_release.py                      # build + validate
    python scripts/eif_release.py --require-final-version
    python scripts/eif_release.py --skip-index-check   # offline: no twine

Exit code 1 if the build, the index metadata check or the clean install fails.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)
NAME_RE = re.compile(r'^name\s*=\s*"([^"]+)"', re.M)

results: list[tuple[str, bool, str]] = []


def record(step: str, ok: bool, detail: str = "") -> bool:
    results.append((step, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'} :: {step}{f' :: {detail}' if detail else ''}")
    return ok


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    child_env = os.environ.copy()
    for key in list(child_env):
        if key.upper() in {"PYTHONPATH", "PYTHONHOME"}:
            child_env.pop(key)
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=child_env,
    )


def venv_bin(env_dir: Path, stem: str) -> Path:
    if sys.platform == "win32":
        return env_dir / "Scripts" / f"{stem}.exe"
    return env_dir / "bin" / stem


def project_metadata() -> tuple[str, str]:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    name = NAME_RE.search(text)
    version = VERSION_RE.search(text)
    if not name or not version:
        raise SystemExit("[eif-release] could not read name/version from pyproject.toml")
    return name.group(1), version.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-final-version",
        action="store_true",
        help="refuse a .dev/.rc version; use this for an actual release build",
    )
    parser.add_argument(
        "--skip-index-check",
        action="store_true",
        help="skip the twine metadata check (it needs network to install twine)",
    )
    args = parser.parse_args()

    name, version = project_metadata()
    print(f"[eif-release] {name} {version}")

    is_final = not re.search(r"(dev|a|b|rc)\d*$", version)
    if args.require_final_version and not is_final:
        record("version is a final release version", False, version)
        print("[eif-release] FAIL")
        return 1
    record("version read from pyproject.toml", True, version)

    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    build = run([sys.executable, "-m", "build"], cwd=REPO_ROOT)
    if not record("sdist and wheel build", build.returncode == 0, build.stderr.strip()[-300:]):
        print("[eif-release] FAIL")
        return 1

    wheels = sorted(DIST_DIR.glob("*.whl"))
    sdists = sorted(DIST_DIR.glob("*.tar.gz"))
    record("wheel produced", len(wheels) == 1, wheels[0].name if wheels else "none")
    record("sdist produced", len(sdists) == 1, sdists[0].name if sdists else "none")
    if not wheels or not sdists:
        print("[eif-release] FAIL")
        return 1

    with tempfile.TemporaryDirectory(prefix="eif-release-") as tmp:
        env_dir = Path(tmp) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
        pip = venv_bin(env_dir, "pip")

        # Index metadata check. twine is the only tool that validates a
        # distribution the way PyPI itself will, so it is installed into the
        # throwaway environment rather than required on the host.
        if args.skip_index_check:
            record("package-index metadata check", True, "skipped by flag")
        else:
            install_twine = run([str(pip), "install", "--quiet", "twine"])
            if install_twine.returncode != 0:
                record(
                    "package-index metadata check",
                    False,
                    "twine could not be installed; rerun with --skip-index-check offline",
                )
            else:
                twine = venv_bin(env_dir, "twine")
                check = run(
                    [str(twine), "check", "--strict", *[str(p) for p in DIST_DIR.glob("*")]]
                )
                record(
                    "package-index metadata check",
                    check.returncode == 0,
                    check.stdout.strip().splitlines()[-1] if check.stdout.strip() else "",
                )

        # The claim the site makes is that `pip install` works, so this proves
        # it against the artifact that would be uploaded, in an environment
        # that has never seen this repository.
        install = run([str(pip), "install", "--quiet", str(wheels[0])])
        if not record("clean-environment install", install.returncode == 0, install.stderr.strip()[-300:]):
            print("[eif-release] FAIL")
            return 1

        eifctl = venv_bin(env_dir, "eifctl")
        record("console script installed", eifctl.exists(), str(eifctl.name))
        if eifctl.exists():
            reported = run([str(eifctl), "version"])
            record(
                "installed eifctl reports its version",
                reported.returncode == 0 and version.split(".dev")[0] in reported.stdout,
                reported.stdout.strip().splitlines()[0] if reported.stdout.strip() else "",
            )

    failed = [step for step, ok, _ in results if not ok]
    print()
    if failed:
        print(f"[eif-release] FAIL ({len(failed)} step(s))")
        return 1

    print("[eif-release] PASS - artifacts in dist/ are installable and index-valid")
    print()
    print("  Publication is not automated and is not performed by this script.")
    print("  To attach the validated artifacts to the matching GitHub Release,")
    print("  an owner with credentials creates the tag and release:")
    print()
    print(f"    git tag -a v{version} -m \"Engineering Intelligence Framework v{version}\"")
    print(f"    git push origin v{version}")
    print(
        f"    gh release create v{version} "
        f"dist/{wheels[0].name} dist/{sdists[0].name} "
        "--verify-tag --generate-notes"
    )
    print()
    print("  PyPI publication is a separate owner decision and is not part of")
    print(f"  this release. After the GitHub Release exists, install its wheel;")
    print("  installing from a clone with `pip install .` also remains supported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
