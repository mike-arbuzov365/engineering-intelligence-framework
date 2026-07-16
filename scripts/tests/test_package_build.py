#!/usr/bin/env python3
"""Real, executed packaging tests for the installable eifctl package - not
inspection of source files, but building an actual wheel, installing it
into a genuinely clean virtualenv (no framework checkout on PATH, a venv
path AND a project path each containing a space and a non-ASCII
character), and running every eifctl subcommand as a real subprocess
against it.

This suite is intentionally slower than the others (building a wheel and
creating venvs takes real seconds) - see run_all.py, which runs it like
every other suite, just slower.

Usage:
    python scripts/tests/test_package_build.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def main() -> int:
    results: list[bool] = []

    # A tempdir whose own name has a space and a non-ASCII character -
    # every venv/project path built under it inherits that, satisfying
    # "venv path containing spaces" and "project path containing spaces
    # and Unicode" without needing separate, redundant scaffolding.
    with tempfile.TemporaryDirectory(prefix="eifctl pkg test тест ") as tmp:
        tmp_root = Path(tmp)

        # --- 0. sync must be up to date - a stale copy would make
        # everything below test the wrong code without saying so.
        sync_check = run([sys.executable, str(FRAMEWORK_ROOT / "scripts" / "sync_package_sources.py"), "--check"])
        results.append(check(
            "package _impl/resources copies are byte-for-byte in sync with their scripts/ sources",
            sync_check.returncode == 0,
            sync_check.stdout + sync_check.stderr,
        ))

        # --- 1. build sdist and wheel ---
        dist_dir = tmp_root / "dist"
        build = run([sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(dist_dir), str(FRAMEWORK_ROOT)])
        results.append(check("python -m build produces a wheel and sdist with no error", build.returncode == 0, build.stdout + build.stderr))
        if build.returncode != 0:
            print(f"EIF-RESULT: passed={sum(results)} total={len(results)}")
            print(f"\ntest_package_build: {sum(results)}/{len(results)} passed")
            return 1  # nothing downstream is meaningful without a wheel

        wheels = list(dist_dir.glob("*.whl"))
        sdists = list(dist_dir.glob("*.tar.gz"))
        results.append(check("exactly one wheel produced", len(wheels) == 1, str(wheels)))
        results.append(check("exactly one sdist produced", len(sdists) == 1, str(sdists)))
        wheel_path = wheels[0]

        # --- 2. inspect wheel contents - real assertions, not a wildcard ---
        with zipfile.ZipFile(wheel_path) as z:
            names = z.namelist()
        results.append(check(
            "wheel contains cli.py",
            any(n.endswith("engineering_intelligence_framework/cli.py") for n in names),
        ))
        results.append(check(
            "wheel contains all 12 _impl scripts",
            sum(1 for n in names if "/_impl/eif_" in n and n.endswith(".py")) == 12,
            str([n for n in names if "/_impl/" in n]),
        ))
        results.append(check(
            "wheel contains the 3 canonical JSON schemas under resources/core/schemas",
            sum(1 for n in names if "/resources/core/schemas/" in n and n.endswith(".schema.json")) == 3,
        ))
        results.append(check(
            "wheel contains resources/scripts/ (eif_init.py's own BUNDLE_SCRIPTS, for project-instance bundling)",
            any(n.endswith("/resources/scripts/eif_locale.py") for n in names),
            "eif_init.py's collect_bundle_sources() reads these from <framework_root>/scripts/ - "
            "missing here means `eifctl init` fails with 'mandatory bundle source missing' at runtime "
            "(a real bug this exact assertion caught once while building this suite)",
        ))
        results.append(check(
            "wheel does NOT contain the framework's own test suite or git metadata",
            not any("/tests/" in n or n.startswith(".git") for n in names),
            str([n for n in names if "/tests/" in n or n.startswith(".git")]),
        ))

        # --- 3. install into a clean venv (space + Unicode in both the venv
        # path and the project path, from this tempdir's own prefix) ---
        venv_dir = tmp_root / "venv"
        venv.create(venv_dir, with_pip=True)
        venv_python = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
        eifctl_exe = venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("eifctl.exe" if sys.platform == "win32" else "eifctl")

        install = run([str(venv_python), "-m", "pip", "install", "-q", str(wheel_path)])
        results.append(check("wheel installs cleanly into a fresh venv", install.returncode == 0, install.stdout + install.stderr))
        results.append(check("eifctl console-script entry point exists after install", eifctl_exe.exists()))

        # --- 4. no framework checkout needed: run everything from a cwd
        # that isn't FRAMEWORK_ROOT and isn't the project either.
        project_dir = tmp_root / "project"
        project_dir.mkdir()

        version_proc = run([str(eifctl_exe), "version"], cwd=tmp_root)
        results.append(check(
            "eifctl version runs offline, without cwd being the framework checkout or the project",
            version_proc.returncode == 0 and "eifctl" in version_proc.stdout,
            version_proc.stdout + version_proc.stderr,
        ))

        init_proc = run(
            [str(eifctl_exe), "init", "--project-name", "pkgtest", "--adapter", "claude-code", "--instance-path", str(project_dir)],
            cwd=tmp_root,
        )
        results.append(check(
            "eifctl init succeeds against a project path with a space and Unicode, from an unrelated cwd",
            init_proc.returncode == 0,
            init_proc.stdout + init_proc.stderr,
        ))

        lock_path = project_dir / ".eif" / "framework.lock.yaml"
        lock_text = lock_path.read_text(encoding="utf-8") if lock_path.exists() else ""
        results.append(check(
            "framework.lock.yaml records package provenance (source_type: installed-package)",
            "source_type: installed-package" in lock_text and "distribution: engineering-intelligence-framework" in lock_text,
            lock_text,
        ))
        results.append(check(
            "framework.lock.yaml has no path from this machine's build environment (no C:\\ or /home/ substring)",
            "C:\\" not in lock_text and "/home/" not in lock_text and str(FRAMEWORK_ROOT) not in lock_text,
            lock_text,
        ))

        doctor_proc = run([str(eifctl_exe), "doctor", "--instance-path", str(project_dir)], cwd=tmp_root)
        results.append(check(
            "eifctl doctor reports all checks passed on the just-initialized project",
            doctor_proc.returncode == 0 and "all checks passed" in doctor_proc.stdout,
            doctor_proc.stdout + doctor_proc.stderr,
        ))

        validate_proc = run(
            [str(eifctl_exe), "validate", "--config", str(project_dir / ".eif" / "config.yaml")], cwd=tmp_root,
        )
        results.append(check("eifctl validate accepts the generated config.yaml", validate_proc.returncode == 0, validate_proc.stdout + validate_proc.stderr))

        render_proc = run([str(eifctl_exe), "render", "session-closeout", "--stdout", "--draft"], cwd=tmp_root)
        results.append(check("eifctl render produces the session-closeout template", render_proc.returncode == 0 and "Knowledge Delta" in render_proc.stdout, render_proc.stdout + render_proc.stderr))

        render_uk_proc = run([str(eifctl_exe), "render", "session-closeout", "--locale", "uk", "--stdout", "--draft"], cwd=tmp_root)
        results.append(check(
            "eifctl render --locale uk produces Ukrainian output (packaged locales/ resources load correctly)",
            render_uk_proc.returncode == 0 and any("а" <= c <= "я" for c in render_uk_proc.stdout.lower()),
            render_uk_proc.stdout + render_uk_proc.stderr,
        ))

        # privacy-scan needs a real git repo (fail-closed by design) -
        # give it one rather than asserting on the fail-closed path here
        # (that path is already covered by scripts/tests/test_privacy_scan.py).
        run(["git", "init", "-q"], cwd=project_dir)
        run(["git", "add", "-A"], cwd=project_dir)
        privacy_proc = run([str(eifctl_exe), "privacy-scan", "--repo", str(project_dir)], cwd=tmp_root)
        results.append(check("eifctl privacy-scan runs clean against the generated project", privacy_proc.returncode == 0, privacy_proc.stdout + privacy_proc.stderr))

        reconfigure_proc = run(
            [str(eifctl_exe), "init", "--instance-path", str(project_dir), "--force", "--locale", "uk"], cwd=tmp_root,
        )
        config_text = (project_dir / ".eif" / "config.yaml").read_text(encoding="utf-8")
        results.append(check(
            "eifctl init --force reconfigures an existing instance (locale switch takes effect)",
            reconfigure_proc.returncode == 0 and "documentation_locale: uk" in config_text,
            reconfigure_proc.stdout + reconfigure_proc.stderr,
        ))

        uninstall = run([str(venv_python), "-m", "pip", "uninstall", "-y", "-q", "engineering-intelligence-framework"])
        results.append(check("uninstall succeeds and removes the console-script entry point", uninstall.returncode == 0 and not eifctl_exe.exists()))

        reinstall = run([str(venv_python), "-m", "pip", "install", "-q", str(wheel_path)])
        results.append(check("reinstall from the same wheel succeeds", reinstall.returncode == 0 and eifctl_exe.exists(), reinstall.stdout + reinstall.stderr))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_package_build: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
