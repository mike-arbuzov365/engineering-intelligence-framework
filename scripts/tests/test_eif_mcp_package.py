#!/usr/bin/env python3
"""Installed wheel: base isolation, optional extra, stdio self-test and licenses.

Packaging tooling is required in the invoking interpreter; intentionally kept
beside the existing release-only package suites, outside run_all's runtime list.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import venv
from pathlib import Path

from test_package_build import FRAMEWORK_ROOT, clean_checkout_export, run


def main() -> int:
    checks = []

    def check(name, value, detail=""):
        checks.append(bool(value))
        print(f"{'PASS' if value else 'FAIL'} {name}" + (": " + detail[-2000:] if not value else ""), flush=True)

    with tempfile.TemporaryDirectory(prefix="eif-mcp-package-") as tmp:
        root = Path(tmp).resolve()
        source = root / "source"
        clean_checkout_export(FRAMEWORK_ROOT, source)
        dist = root / "wheels"
        build = run([sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(source)], timeout_s=180)
        check("isolated wheel build", build.returncode == 0, build.stdout + build.stderr)
        if build.returncode:
            print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
            return 1
        wheel = next(dist.glob("*.whl"))
        environment = root / "venv space α"
        venv.create(environment, with_pip=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        eifctl = environment / ("Scripts/eifctl.exe" if os.name == "nt" else "bin/eifctl")
        installed = run([str(python), "-m", "pip", "install", str(wheel)], cwd=root, timeout_s=180)
        check("base install", installed.returncode == 0, installed.stdout + installed.stderr)
        # Deliberately supply a poisoned source path to the caller. The shared
        # runner must remove ambient PYTHONPATH from installed-package tests.
        previous = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = str(FRAMEWORK_ROOT / "src")
        try:
            origin = run([str(python), "-c", "import engineering_intelligence_framework as e; print(e.__file__)"], cwd=root)
        finally:
            if previous is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = previous
        check("imports installed wheel despite ambient source path", str(environment).lower() in origin.stdout.lower() and str(FRAMEWORK_ROOT).lower() not in origin.stdout.lower(), origin.stdout + origin.stderr)
        sdk = run([str(python), "-c", "import importlib.util; assert importlib.util.find_spec('mcp') is None"], cwd=root)
        check("base has no SDK", sdk.returncode == 0, sdk.stdout + sdk.stderr)
        help_result = run([str(eifctl), "mcp", "--help"], cwd=root)
        missing = run([str(eifctl), "mcp", "serve", "--instance-path", str(root)], cwd=root)
        check("help without SDK", help_result.returncode == 0)
        check("missing extra code 2 without traceback", missing.returncode == 2 and "[mcp]" in missing.stderr and "Traceback" not in missing.stderr, missing.stdout + missing.stderr)
        extra = run([str(python), "-m", "pip", "install", "-c", str(source / "integrations/eif-mcp/constraints.txt"), str(wheel) + "[mcp]"], cwd=root, timeout_s=240)
        check("extra install using resolved constraints", extra.returncode == 0, extra.stdout + extra.stderr)
        check("extra pip check", run([str(python), "-m", "pip", "check"], cwd=root).returncode == 0)
        project = root / "project space β"
        created = run([str(eifctl), "new", str(project), "--project-name", "synthetic-wheel", "--adapter", "codex"], cwd=root, timeout_s=60)
        check("installed instance creation", created.returncode == 0, created.stdout + created.stderr)
        check("installed runtime has canonical MCP guide", (project / ".eif/runtime/docs/reference/eif-mcp.md").is_file())
        probe = run([str(eifctl), "mcp", "serve", "--instance-path", str(project), "--self-test"], cwd=root, timeout_s=60)
        value = json.loads(probe.stdout) if probe.returncode == 0 else {}
        check("installed SDK stdio self-test with matching drift", probe.returncode == 0 and value.get("status") == "ok" and value.get("tools") == 9, probe.stdout + probe.stderr)
        license_result = run([str(python), str(source / "scripts/eif_check_licenses.py"), "--framework-root", str(source), "--environment"], cwd=root, timeout_s=30)
        check("clean extra environment licenses", license_result.returncode == 0, license_result.stdout + license_result.stderr)
        sdk_origin = run([str(python), "-c", "import mcp,engineering_intelligence_framework as e; print(mcp.__file__); print(e.__file__)"], cwd=root)
        check("both SDK and EIF resolve inside venv", sdk_origin.returncode == 0 and all(str(environment).lower() in line.lower() for line in sdk_origin.stdout.strip().splitlines()), sdk_origin.stdout + sdk_origin.stderr)
    print(f"EIF-RESULT: passed={sum(checks)} total={len(checks)}")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
