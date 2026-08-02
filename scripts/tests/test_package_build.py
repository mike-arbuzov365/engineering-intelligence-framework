#!/usr/bin/env python3
"""Release-only exhaustive packaging tests for the installable eifctl package - not
inspection of source files, but building an actual wheel, installing it
into a genuinely clean virtualenv (no framework checkout on PATH, a venv
path AND a project path each containing a space and a non-ASCII
character), and running every eifctl subcommand as a real subprocess
against it.

This suite is intentionally slower than the ordinary package smoke: it builds
wheel + sdist, creates two clean environments, reinstalls, corrupts package
state deliberately, and exercises every adapter/integration/package boundary.
It is deliberately excluded from run_all.py and runs once before a release.
For normal package-relevant work use test_package_smoke.py instead.

Usage:
    python scripts/tests/test_package_build.py
"""
from __future__ import annotations

import os
import json
import re
import shutil
import shlex
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path

import yaml

FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]


def check(name: str, condition: bool, detail: str = "") -> bool:
    print(f"{'PASS' if condition else 'FAIL'} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition


def run(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict | None = None,
    timeout_s: float | None = None,
) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **env} if env else None
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=full_env, timeout=timeout_s,
    )


def make_python_command_shim(root: Path, python_executable: Path, stem: str, source: str) -> Path:
    """Create a local test-only executable that forwards argv to Python."""
    provider = root / f"{stem}.py"
    provider.write_text(source, encoding="utf-8")
    if sys.platform == "win32":
        # The .cmd body must stay pure ASCII. cmd.exe parses a batch file in
        # the console OEM code page, never UTF-8, and this suite deliberately
        # runs from a temporary directory containing a space and a non-ASCII
        # character. Interpolating those paths into the file wrote bytes
        # cmd.exe then decoded into a path that does not exist, so the shim
        # exited without ever starting Python: every doctor version probe came
        # back empty, and three integration-status checks failed against the
        # installed wheel from 0.2.0 to 0.2.3 while the product was behaving
        # correctly. Environment variables carry the real paths as Unicode
        # through CreateProcess, with no code page in the way. eifctl inherits
        # this process's environment, so the shim it spawns sees them too.
        variable = "EIF_TEST_SHIM_" + re.sub(r"[^A-Z0-9]", "_", stem.upper())
        os.environ[f"{variable}_PYTHON"] = str(python_executable)
        os.environ[f"{variable}_TARGET"] = str(provider)
        shim = root / f"{stem}.cmd"
        shim.write_text(
            f'@echo off\r\n"%{variable}_PYTHON%" "%{variable}_TARGET%" %*\r\n',
            encoding="ascii",
        )
    else:
        shim = root / stem
        shim.write_text(
            f"#!/bin/sh\nexec {shlex.quote(str(python_executable))} {shlex.quote(str(provider))} \"$@\"\n",
            encoding="utf-8",
        )
        shim.chmod(0o755)
    return shim


def snapshot_paths(root: Path, paths: list[Path]) -> dict[str, bytes]:
    snapshot = {}
    for path in paths:
        if path.is_dir():
            files = sorted(item for item in path.rglob("*") if item.is_file() and "__pycache__" not in item.parts)
        else:
            files = [path] if path.is_file() else []
        for file_path in files:
            snapshot[file_path.relative_to(root).as_posix()] = file_path.read_bytes()
    return snapshot


def clean_checkout_export(framework_root: Path, dest_dir: Path) -> None:
    """Exports exactly the currently TRACKED file state (including any
    staged/unstaged modifications to tracked files, but excluding untracked/
    ignored files - a stray local __pycache__/ or similar) into dest_dir, so
    building from it proves the package is never accidentally contaminated
    by local-only cruft a real CI checkout would never have (exactly the
    class of bug that broke the benchmark harness's fixture digests: local
    testing regenerates files git never tracked). `git stash create` makes
    a commit object capturing the current index+worktree diff vs HEAD
    without touching the working directory or requiring anything to
    already be committed; if the tree is already clean (nothing to stash),
    HEAD itself is used directly."""
    stash = subprocess.run(
        ["git", "-C", str(framework_root), "stash", "create"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    tree_ish = stash or "HEAD"
    dest_dir.mkdir(parents=True, exist_ok=True)
    tar_path = dest_dir.parent / "clean-checkout.tar"
    archive = subprocess.run(
        ["git", "-C", str(framework_root), "archive", "--format=tar", f"--output={tar_path}", tree_ish],
        capture_output=True, text=True,
    )
    if archive.returncode != 0:
        raise RuntimeError(f"git archive failed: {archive.stdout}{archive.stderr}")
    with tarfile.open(tar_path) as tf:
        tf.extractall(dest_dir)  # noqa: S202 - own git archive output, not untrusted input
    tar_path.unlink()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
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
            "package copies match their sources and contain no stale generated files",
            sync_check.returncode == 0,
            sync_check.stdout + sync_check.stderr,
        ))

        # --- 1. build sdist and wheel from a CLEAN CHECKOUT (git-tracked
        # files only), not the live working tree - a stray untracked file
        # (e.g. local __pycache__/ from manual testing) must never silently
        # leak into the package just because it happens to be sitting in
        # the dev machine's working directory right now. ---
        clean_src = tmp_root / "clean-src"
        clean_checkout_export(FRAMEWORK_ROOT, clean_src)
        dist_dir = tmp_root / "dist"
        build = run([sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(dist_dir), str(clean_src)])
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
        expected_impl = {
            path.name for path in (clean_src / "src" / "engineering_intelligence_framework" / "_impl").glob("eif_*.py")
        }
        actual_impl = {
            Path(name).name for name in names if "/_impl/eif_" in name and name.endswith(".py")
        }
        results.append(check(
            f"wheel contains the exact canonical set of {len(expected_impl)} _impl scripts",
            actual_impl == expected_impl,
            f"expected={sorted(expected_impl)} actual={sorted(actual_impl)}",
        ))
        canonical_schema_count = len(list((clean_src / "core" / "schemas").glob("*.schema.json")))
        results.append(check(
            f"wheel contains all {canonical_schema_count} canonical JSON schemas under resources/core/schemas",
            sum(1 for n in names if "/resources/core/schemas/" in n and n.endswith(".schema.json")) == canonical_schema_count,
            str([n for n in names if "/resources/core/schemas/" in n]),
        ))
        results.append(check(
            "wheel contains resources/scripts/ (eif_init.py's own BUNDLE_SCRIPTS, for project-instance bundling)",
            any(n.endswith("/resources/scripts/eif_locale.py") for n in names),
            "eif_init.py's collect_bundle_sources() reads these from <framework_root>/scripts/ - "
            "missing here means `eifctl init` fails with 'mandatory bundle source missing' at runtime "
            "(a real bug this exact assertion caught once while building this suite)",
        ))
        results.append(check(
            "wheel contains installable professional profile starters",
            any(
                n.endswith(
                    "/resources/professional-profiles/graphic-design/profile.yaml"
                )
                for n in names
            )
            and any(
                n.endswith(
                    "/resources/professional-profiles/software-development/profile.yaml"
                )
                for n in names
            ),
        ))
        results.append(check(
            "wheel contains the standalone benchmark C/D contract tool",
            any(n.endswith("/resources/scripts/eif_benchmark.py") for n in names),
            "the public benchmark schemas without their executable validator and harness are not a delivered contract",
        ))
        results.append(check(
            "benchmark tool remains a package resource, not a project runtime bundle or eifctl implementation",
            not any(n.endswith("/_impl/eif_benchmark.py") for n in names),
            "benchmark execution is an explicit verification workflow, not a runtime dependency of every initialized project",
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

        # --- 4a. v0.2 private-workspace lifecycle UX: create the local
        # workspace, connect a local git project, then plan and apply both
        # provenance axes from the installed wheel.
        control_dir = tmp_root / "private workspace"
        workspace_new = run([
            str(eifctl_exe), "workspace", "new", str(control_dir),
            "--workspace-name", "test-workspace",
            "--adapter", "codex",
            "--locale", "uk",
        ], cwd=tmp_root)
        results.append(check(
            "eifctl workspace new creates a local private workspace without a framework checkout",
            workspace_new.returncode == 0
            and (control_dir / ".git").exists()
            and (control_dir / ".eif" / "workspace.yaml").exists()
            and (control_dir / ".eif" / "projects.yaml").exists()
            and (control_dir / "workspace" / "profiles" / "default.yaml").exists()
            and (control_dir / "planning" / "migration-ledger.md").exists()
            and "no remote" in workspace_new.stdout,
            workspace_new.stdout + workspace_new.stderr,
        ))
        profile_list = run([
            str(eifctl_exe), "workspace", "profile", "list",
        ], cwd=tmp_root)
        profile_install = run([
            str(eifctl_exe), "workspace", "profile", "install", "graphic-design",
            "--workspace-path", str(control_dir),
        ], cwd=tmp_root)
        results.append(check(
            "wheel-installed professional profile catalog lists and installs graphic-design",
            profile_list.returncode == 0
            and "graphic-design" in profile_list.stdout
            and "software-development" in profile_list.stdout
            and profile_install.returncode == 0
            and (control_dir / "workspace" / "profiles" / "graphic-design.yaml").is_file()
            and (
                control_dir
                / "workspace"
                / "skills"
                / "run-graphic-design-project"
                / "SKILL.md"
            ).is_file(),
            profile_list.stdout + profile_list.stderr
            + profile_install.stdout + profile_install.stderr,
        ))
        workspace_doctor = run([
            str(eifctl_exe), "workspace", "doctor",
            "--workspace-path", str(control_dir),
        ], cwd=tmp_root)
        results.append(check(
            "wheel-installed workspace doctor accepts the clean bootstrap",
            workspace_doctor.returncode == 0 and "PASS" in workspace_doctor.stdout,
            workspace_doctor.stdout + workspace_doctor.stderr,
        ))
        registry_path = control_dir / ".eif" / "projects.yaml"
        new_project = tmp_root / "new project створено"
        new_proc = run([
            str(eifctl_exe), "new", str(new_project),
            "--project-name", "new-project",
            "--adapter", "codex",
            "--locale", "uk",
            "--profile", "graphic-design",
            "--registry", str(registry_path),
        ], cwd=tmp_root)
        results.append(check(
            "eifctl new creates a local git repo, EIF instance, and private registry entry",
            new_proc.returncode == 0
            and (new_project / ".git").exists()
            and (new_project / "AGENTS.md").exists()
            and registry_path.exists(),
            new_proc.stdout + new_proc.stderr,
        ))
        new_lock = yaml.safe_load((new_project / ".eif" / "framework.lock.yaml").read_text(encoding="utf-8"))
        new_config = yaml.safe_load((new_project / ".eif" / "config.yaml").read_text(encoding="utf-8"))
        installed_version = version_proc.stdout.strip().split()[1]
        results.append(check(
            "new project config and lock record the actual installed package version",
            (new_config.get("framework") or {}).get("version") == installed_version
            and (new_lock.get("instance") or {}).get("eif_instance_version") == installed_version
            and (new_lock.get("package") or {}).get("version") == installed_version,
            str({"config": new_config.get("framework"), "instance": new_lock.get("instance"), "package": new_lock.get("package")}),
        ))
        run(["git", "add", "-A"], cwd=control_dir)
        commit_workspace = run([
            "git", "-c", "user.name=EIF Test", "-c", "user.email=eif-test@example.invalid",
            "commit", "-m", "bootstrap workspace and registry",
        ], cwd=control_dir)
        results.append(check(
            "private workspace and logical registry can be committed without machine-local paths",
            commit_workspace.returncode == 0
            and str(new_project) not in (control_dir / ".eif" / "projects.yaml").read_text(encoding="utf-8"),
            commit_workspace.stdout + commit_workspace.stderr,
        ))
        run(["git", "add", "-A"], cwd=new_project)
        commit_new = run([
            "git", "-c", "user.name=EIF Test", "-c", "user.email=eif-test@example.invalid",
            "commit", "-m", "bootstrap",
        ], cwd=new_project)
        results.append(check("new project bootstrap can be committed cleanly", commit_new.returncode == 0, commit_new.stdout + commit_new.stderr))
        shutil.rmtree(new_project / ".eif" / "runtime")
        plan_new = run([
            str(eifctl_exe), "projects", "upgrade",
            "--registry", str(registry_path),
        ], cwd=control_dir)
        results.append(check(
            "projects upgrade is plan-only by default and does not recreate runtime",
            plan_new.returncode == 0
            and "no files were written" in plan_new.stdout
            and not (new_project / ".eif" / "runtime").exists(),
            plan_new.stdout + plan_new.stderr,
        ))
        apply_new = run([
            str(eifctl_exe), "projects", "upgrade",
            "--registry", str(registry_path),
            "--apply",
        ], cwd=control_dir)
        results.append(check(
            "projects upgrade applies and verifies both framework and workspace axes",
            apply_new.returncode == 0
            and (new_project / ".eif" / "runtime" / "eif_verify_runtime.py").exists()
            and (new_project / ".eif" / "workspace-runtime").exists()
            and (new_project / ".eif" / "workspace.lock.yaml").exists()
            and "SUCCESS updated 1 project(s)" in apply_new.stdout,
            apply_new.stdout + apply_new.stderr,
        ))
        run(["git", "add", "-A"], cwd=new_project)
        commit_update = run([
            "git", "-c", "user.name=EIF Test", "-c", "user.email=eif-test@example.invalid",
            "commit", "-m", "apply workspace",
        ], cwd=new_project)
        results.append(check(
            "two-axis project update can be committed cleanly",
            commit_update.returncode == 0,
            commit_update.stdout + commit_update.stderr,
        ))
        designer_doctor = run([
            str(eifctl_exe), "doctor", "--instance-path", str(new_project),
        ], cwd=tmp_root)
        results.append(check(
            "wheel-installed designer project reports its active agent context",
            designer_doctor.returncode == 0
            and "instruction: AGENTS.md (codex)" in designer_doctor.stdout
            and "profile: graphic-design" in designer_doctor.stdout
            and "review-graphic-design-delivery" in designer_doctor.stdout
            and "run-graphic-design-project" in designer_doctor.stdout
            and "project memory: managed at knowledge; index knowledge/index.md "
            "(not created yet)"
            in designer_doctor.stdout,
            designer_doctor.stdout + designer_doctor.stderr,
        ))
        detach_plan = run([
            str(eifctl_exe), "projects", "detach", "new-project",
            "--registry", str(registry_path),
        ], cwd=control_dir)
        results.append(check(
            "projects detach is plan-only by default",
            detach_plan.returncode == 0
            and "plan only" in detach_plan.stdout
            and (new_project / ".eif" / "workspace.lock.yaml").exists(),
            detach_plan.stdout + detach_plan.stderr,
        ))
        detach_apply = run([
            str(eifctl_exe), "projects", "detach", "new-project",
            "--registry", str(registry_path),
            "--apply",
        ], cwd=control_dir)
        detached_registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        results.append(check(
            "projects detach removes only workspace-managed state and keeps a detached logical entry",
            detach_apply.returncode == 0
            and not (new_project / ".eif" / "workspace-runtime").exists()
            and not (new_project / ".eif" / "workspace.lock.yaml").exists()
            and (new_project / ".eif" / "framework.lock.yaml").exists()
            and detached_registry["projects"][0]["status"] == "detached",
            detach_apply.stdout + detach_apply.stderr,
        ))
        detached_doctor = run([
            str(eifctl_exe), "workspace", "doctor",
            "--workspace-path", str(control_dir),
        ], cwd=tmp_root)
        results.append(check(
            "workspace doctor accepts an explicitly detached project",
            detached_doctor.returncode == 0 and "PASS" in detached_doctor.stdout,
            detached_doctor.stdout + detached_doctor.stderr,
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
        lock_data = yaml.safe_load(lock_text) if lock_text else {}
        runtime_manifest_paths = [
            item.get("path", "")
            for item in (lock_data.get("bundle", {}).get("manifest", []) if lock_data else [])
        ]
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
        results.append(check(
            "framework.lock.yaml records a real resource_manifest_digest (sha256:<64-hex>), not omitted",
            "resource_manifest_digest: sha256:" in lock_text,
            lock_text,
        ))
        results.append(check(
            "framework.lock.yaml records wheel_sha256 (installed from a local wheel path, direct_url.json has the hash)",
            "wheel_sha256:" in lock_text,
            lock_text,
        ))
        results.append(check(
            "installed-wheel runtime manifest excludes interpreter-generated bytecode",
            not any(
                "__pycache__" in path or path.endswith((".pyc", ".pyo"))
                for path in runtime_manifest_paths
            ),
            str(runtime_manifest_paths),
        ))

        doctor_proc = run([str(eifctl_exe), "doctor", "--instance-path", str(project_dir)], cwd=tmp_root)
        results.append(check(
            "eifctl doctor reports all checks passed on the just-initialized project",
            doctor_proc.returncode == 0 and "all checks passed" in doctor_proc.stdout,
            doctor_proc.stdout + doctor_proc.stderr,
        ))

        # --- Installed-wheel optional-integration status matrix. The local
        # shims below prove that packaged doctor transports provider argv,
        # resources and machine-readable results correctly. They are test
        # doubles, never evidence that the real providers are healthy. ---
        disabled_report_path = tmp_root / "integrations-disabled.json"
        disabled_doctor = run([
            str(eifctl_exe), "doctor", "--instance-path", str(project_dir),
            "--integration-report", str(disabled_report_path),
        ], cwd=tmp_root)
        disabled_report = json.loads(disabled_report_path.read_text(encoding="utf-8")) if disabled_report_path.exists() else {}
        disabled_results = disabled_report.get("results", [])
        results.append(check(
            "installed-wheel doctor reports every default optional integration as disabled",
            disabled_doctor.returncode == 0 and disabled_results and all(item["state"] == "disabled" for item in disabled_results),
            disabled_doctor.stdout + disabled_doctor.stderr,
        ))

        integration_project = tmp_root / "integration-status-pkgtest"
        integration_init = run([
            str(eifctl_exe), "init", "--project-name", "integration-status-pkgtest",
            "--adapter", "claude-code", "--instance-path", str(integration_project),
        ], cwd=tmp_root)
        results.append(check("installed wheel initializes the integration status fixture", integration_init.returncode == 0, integration_init.stdout + integration_init.stderr))
        run(["git", "init", "-q"], cwd=integration_project)
        run(["git", "config", "user.email", "eif-canary@example.invalid"], cwd=integration_project)
        run(["git", "config", "user.name", "EIF Canary"], cwd=integration_project)
        (integration_project / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
        run(["git", "add", "-A"], cwd=integration_project)
        run(["git", "commit", "-q", "-m", "baseline"], cwd=integration_project)
        baseline = run(["git", "rev-parse", "HEAD"], cwd=integration_project).stdout.strip()

        graph_dir = integration_project / "graphify-out"
        graph_dir.mkdir()
        graph_path = graph_dir / "graph.json"
        graph_data = {
            "directed": True,
            "multigraph": False,
            "nodes": [
                {"id": "source.py::Service", "label": "Service"},
                {"id": "source.py::Repository", "label": "Repository"},
            ],
            "links": [{"source": "source.py::Service", "target": "source.py::Repository", "relation": "CALLS"}],
            "hyperedges": [],
            "built_at_commit": baseline,
        }
        graph_path.write_text(json.dumps(graph_data), encoding="utf-8")

        graphify_shim = make_python_command_shim(
            tmp_root,
            venv_python,
            "fake-graphify-provider",
            """import sys
args = sys.argv[1:]
if args == ['--version']:
    print('graphify 0.9.12')
elif args and args[0] == 'query':
    print('PaymentService InvoiceRepository CALLS')
elif args and args[0] == 'path':
    print('CheckoutController -> PaymentService -> InvoiceRepository')
elif args and args[0] == 'explain':
    print('PaymentService CALLS InvoiceRepository')
else:
    raise SystemExit(2)
""",
        )
        rtk_shim = make_python_command_shim(
            tmp_root,
            venv_python,
            "fake-rtk-provider",
            """import json
import subprocess
import sys
args = sys.argv[1:]
if args == ['--version']:
    print('rtk 0.43.0')
elif args == ['--help']:
    print('  git x\\n  rg x\\n  read x\\n  summary x\\n  proxy x')
elif args and args[0] == 'proxy':
    raise SystemExit(2)
elif args and args[0] == 'rg':
    print('EIF_RTK_ALPHA\\nEIF_RTK_BETA')
elif len(args) >= 2 and args[:2] == ['git', 'diff']:
    print('sample.txt | 2 +-')
else:
    raise SystemExit(2)
""",
        )

        integration_config_path = integration_project / ".eif" / "config.yaml"
        integration_config = yaml.safe_load(integration_config_path.read_text(encoding="utf-8"))
        structural = integration_config["integrations"]["structural_graph"]
        structural.update({
            "enabled": True,
            "provider": "graphify",
            "mode": "structural",
            "artifact_path": "graphify-out/graph.json",
            "baseline_commit": None,
            "processing": "local",
            "data_boundary": "local-only",
            "cost_cap_usd": 0,
            "failure_policy": "degrade",
            "executable_path": str(tmp_root / "missing-graphify-provider"),
        })

        def write_integration_config() -> None:
            integration_config_path.write_text(yaml.safe_dump(integration_config, sort_keys=False), encoding="utf-8")

        def installed_doctor_report(stem: str) -> tuple[subprocess.CompletedProcess, dict]:
            report_path = tmp_root / f"{stem}.json"
            proc = run([
                str(eifctl_exe), "doctor", "--instance-path", str(integration_project),
                "--integration-report", str(report_path),
            ], cwd=tmp_root)
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
            return proc, {item["integration"]: item for item in report.get("results", [])}

        write_integration_config()
        unavailable_doctor, unavailable_by_name = installed_doctor_report("integration-unavailable")
        unavailable_graph = unavailable_by_name.get("structural_graph", {})
        results.append(check(
            "installed-wheel doctor reports a missing explicit provider executable as unavailable and actionable",
            unavailable_doctor.returncode == 0
            and unavailable_graph.get("state") == "unavailable"
            and bool(unavailable_graph.get("remediation")),
            unavailable_doctor.stdout + unavailable_doctor.stderr,
        ))

        structural["executable_path"] = str(graphify_shim)
        graph_data["built_at_commit"] = "0" * 40
        graph_path.write_text(json.dumps(graph_data), encoding="utf-8")
        write_integration_config()
        degraded_doctor, degraded_by_name = installed_doctor_report("integration-degraded")
        degraded_graph = degraded_by_name.get("structural_graph", {})
        results.append(check(
            "installed-wheel doctor reports missing Graphify lifecycle metadata as blocked and degraded, not healthy",
            degraded_doctor.returncode == 0
            and degraded_graph.get("state") == "degraded"
            and (degraded_graph.get("freshness") or {}).get("state") == "blocked",
            degraded_doctor.stdout + degraded_doctor.stderr,
        ))

        graph_data["built_at_commit"] = baseline
        graph_path.write_text(json.dumps(graph_data), encoding="utf-8")
        graph_scope_path = integration_project / ".eif" / "graphify-scope.json"
        graph_scope_path.write_text(
            json.dumps({
                "schema_version": 1,
                "repo_id": "integration-status-pkgtest",
                "source_paths": ["source.py"],
                "semantic_paths": [],
                "exclude_paths": [".eif", "graphify-out"],
                "suppressed": False,
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        capture_metadata = run([
            str(venv_python),
            str(integration_project / ".eif" / "runtime" / "eif_graphify.py"),
            "capture-metadata",
            "--instance-root", str(integration_project),
            "--graphify-version", "0.9.12",
            "--generated-at", "2026-07-23T00:00:00+00:00",
        ], cwd=tmp_root)
        results.append(check(
            "installed-wheel Graphify lifecycle captures deterministic D08 metadata",
            capture_metadata.returncode == 0,
            capture_metadata.stdout + capture_metadata.stderr,
        ))
        compression = integration_config["integrations"]["shell_output_compression"]
        compression.update({
            "enabled": True,
            "provider": "rtk",
            "processing": "local",
            "data_boundary": "local-only",
            "failure_policy": "degrade",
            "executable_path": str(rtk_shim),
        })
        write_integration_config()
        healthy_doctor, healthy_by_name = installed_doctor_report("integration-healthy")
        results.append(check(
            "installed-wheel doctor can report Graphify healthy only with fresh artifact and passing canaries",
            healthy_doctor.returncode == 0 and healthy_by_name.get("structural_graph", {}).get("state") == "healthy",
            healthy_doctor.stdout + healthy_doctor.stderr,
        ))
        installed_rtk = healthy_by_name.get("shell_output_compression", {})
        failed_rtk_capabilities = {
            item.get("id") for item in installed_rtk.get("capabilities", []) if item.get("status") == "fail"
        }
        results.append(check(
            "installed-wheel doctor reports RTK degraded when a required argv canary fails",
            healthy_doctor.returncode == 0
            and installed_rtk.get("state") == "degraded"
            and failed_rtk_capabilities == {"proxy-argv"},
            healthy_doctor.stdout + healthy_doctor.stderr,
        ))

        owner_sentinel = "\nOWNER_SENTINEL: preserve project content\n"
        entrypoint_path = integration_project / "CLAUDE.md"
        entrypoint_path.write_text(entrypoint_path.read_text(encoding="utf-8") + owner_sentinel, encoding="utf-8")
        config_before_upgrade = integration_config_path.read_bytes()
        integration_upgrade = run([
            str(eifctl_exe), "init", "--instance-path", str(integration_project),
        ], cwd=tmp_root)
        results.append(check(
            "installed-wheel routine upgrade preserves integration config and project-owned entrypoint content",
            integration_upgrade.returncode == 0
            and integration_config_path.read_bytes() == config_before_upgrade
            and owner_sentinel.strip() in entrypoint_path.read_text(encoding="utf-8"),
            integration_upgrade.stdout + integration_upgrade.stderr,
        ))

        managed_paths = [
            integration_project / ".eif" / "runtime",
            integration_project / ".eif" / "framework.lock.yaml",
            integration_config_path,
            entrypoint_path,
            integration_project / ".gitignore",
        ]
        before_failed_upgrade = snapshot_paths(integration_project, managed_paths)
        failed_upgrade = run(
            [str(eifctl_exe), "init", "--instance-path", str(integration_project)],
            cwd=tmp_root,
            env={"EIF_INIT_TEST_FAIL_AFTER": "runtime"},
        )
        after_failed_upgrade = snapshot_paths(integration_project, managed_paths)
        results.append(check(
            "installed-wheel injected upgrade failure rolls back managed state and preserves project content",
            failed_upgrade.returncode != 0
            and before_failed_upgrade == after_failed_upgrade
            and owner_sentinel.strip() in entrypoint_path.read_text(encoding="utf-8"),
            failed_upgrade.stdout + failed_upgrade.stderr,
        ))

        # --- doctor detects a modified/corrupted packaged resource bundle:
        # hand-corrupt a schema file INSIDE the venv's installed package
        # (as if the install were tampered with or partially corrupted),
        # then confirm doctor's package-provenance check (commands/doctor.py)
        # flags the resource_manifest_digest mismatch, not a silent pass. ---
        # PYTHONIOENCODING=utf-8: this tempdir's own prefix contains Cyrillic
        # characters (by design - see the outer TemporaryDirectory above), and
        # a child Python process's stdout defaults to the OS codepage (cp1252
        # on Windows) when piped rather than attached to a console, which
        # cannot encode them - a real UnicodeEncodeError this exact assertion
        # caught once while building this suite, not merely a hypothetical.
        find_resources = run(
            [str(venv_python), "-c",
             "import engineering_intelligence_framework.resources as r\n"
             "with r.framework_root() as root:\n"
             "    print(root)"],
            env={"PYTHONIOENCODING": "utf-8"},
        )
        resources_root = Path(find_resources.stdout.strip()) if find_resources.returncode == 0 else None
        if resources_root and resources_root.is_dir():
            digest_command = [
                str(venv_python), "-c",
                "import sys\n"
                "from pathlib import Path\n"
                "from engineering_intelligence_framework.commands.init_cmd import _resource_manifest_digest\n"
                "print(_resource_manifest_digest(Path(sys.argv[1])))",
                str(resources_root),
            ]
            digest_before_bytecode = run(digest_command, env={"PYTHONIOENCODING": "utf-8"})
            bytecode_dir = resources_root / "integrations" / "__pycache__"
            bytecode_dir.mkdir(parents=True, exist_ok=True)
            bytecode_file = bytecode_dir / "generated.cpython-311.pyc"
            bytecode_file.write_bytes(b"interpreter-generated test bytecode")
            try:
                digest_after_bytecode = run(digest_command, env={"PYTHONIOENCODING": "utf-8"})
                doctor_with_bytecode = run(
                    [str(eifctl_exe), "doctor", "--instance-path", str(project_dir)],
                    cwd=tmp_root,
                )
                results.append(check(
                    "installed-package resource digest ignores interpreter-generated bytecode",
                    digest_before_bytecode.returncode == 0
                    and digest_after_bytecode.returncode == 0
                    and digest_before_bytecode.stdout == digest_after_bytecode.stdout,
                    digest_before_bytecode.stdout + digest_before_bytecode.stderr
                    + digest_after_bytecode.stdout + digest_after_bytecode.stderr,
                ))
                results.append(check(
                    "eifctl doctor remains healthy when Python creates resource-tree bytecode",
                    doctor_with_bytecode.returncode == 0
                    and "all checks passed" in doctor_with_bytecode.stdout,
                    doctor_with_bytecode.stdout + doctor_with_bytecode.stderr,
                ))
            finally:
                bytecode_file.unlink(missing_ok=True)
                try:
                    bytecode_dir.rmdir()
                except OSError:
                    pass

            # A template file, not a *.schema.json: corrupting a JSON schema
            # file here would ALSO be parsed by check_schema() for the
            # config/lock validation checks that run first in
            # eif_verify_runtime.main(), crashing doctor with an uncaught
            # JSONDecodeError before this package-provenance check is ever
            # reached - a real but separate robustness gap (schema loading
            # isn't crash-safe against a malformed file), not what this
            # assertion is testing. A template's content isn't parsed/
            # validated by anything else doctor checks, so tampering with
            # it exercises the resource_manifest_digest mismatch in
            # isolation.
            victim = next((p for p in resources_root.rglob("*.md") if "templates" in p.parts and p.is_file()), None)
            if victim is not None:
                original = victim.read_bytes()
                victim.write_bytes(original + b"\n<!-- tampered for test -->\n")
                try:
                    doctor_after_tamper = run([str(eifctl_exe), "doctor", "--instance-path", str(project_dir)], cwd=tmp_root)
                    results.append(check(
                        "eifctl doctor detects a modified installed-package resource bundle (resource_manifest_digest mismatch)",
                        doctor_after_tamper.returncode != 0 and "resources/ tree does not match its own recorded digest" in (doctor_after_tamper.stdout + doctor_after_tamper.stderr),
                        doctor_after_tamper.stdout + doctor_after_tamper.stderr,
                    ))
                finally:
                    victim.write_bytes(original)
            else:
                results.append(check("eifctl doctor detects a modified installed-package resource bundle", False, "no template file found under resources/templates/ to tamper with"))
        else:
            results.append(check(
                "eifctl doctor detects a modified installed-package resource bundle", False,
                f"could not resolve the installed package's resources/ root - "
                f"find_resources: rc={find_resources.returncode} stdout={find_resources.stdout!r} stderr={find_resources.stderr!r}",
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

        # --- package-wheel-metadata: eifctl init --adapter codex also works
        # from the INSTALLED wheel, not only the dev checkout - the wheel's
        # bundled eif_adapters.py registry is what actually gets consulted,
        # so this proves the registered adapter (and the new AGENTS.md
        # marker-merge entrypoint template) round-trips through packaging. ---
        codex_project_dir = tmp_root / "codex-pkgtest"
        codex_init_proc = run(
            [str(eifctl_exe), "init", "--project-name", "codex-pkgtest", "--adapter", "codex", "--instance-path", str(codex_project_dir)],
            cwd=tmp_root,
        )
        results.append(check(
            "eifctl init --adapter codex succeeds from the installed wheel",
            codex_init_proc.returncode == 0,
            codex_init_proc.stdout + codex_init_proc.stderr,
        ))
        codex_entry_text = (codex_project_dir / "AGENTS.md").read_text(encoding="utf-8") if (codex_project_dir / "AGENTS.md").exists() else ""
        results.append(check(
            "wheel-installed eifctl generates a real AGENTS.md with the EIF-managed block",
            "<!-- EIF:BEGIN" in codex_entry_text and "<!-- EIF:END -->" in codex_entry_text,
            codex_entry_text,
        ))
        results.append(check(
            "wheel-installed eifctl's generated AGENTS.md correctly names itself (not a stale 'CLAUDE.md' reference)",
            "AGENTS.md/.gitignore marker integrity" in codex_entry_text,
            codex_entry_text,
        ))
        codex_cfg_text = (codex_project_dir / ".eif" / "config.yaml").read_text(encoding="utf-8") if (codex_project_dir / ".eif" / "config.yaml").exists() else ""
        results.append(check(
            "wheel-installed eifctl records adapter.name: codex",
            "codex" in codex_cfg_text,
            codex_cfg_text,
        ))

        # --- package-wheel-metadata: eifctl init --adapter hermes also
        # works from the INSTALLED wheel - proves the wheel's bundled
        # resolve_hermes_active_source()/simulate_hermes_context() (not
        # just the registry entry) round-trip through packaging, same as
        # Codex's own wheel proof above. ---
        hermes_project_dir = tmp_root / "hermes-pkgtest"
        hermes_init_proc = run(
            [str(eifctl_exe), "init", "--project-name", "hermes-pkgtest", "--adapter", "hermes", "--instance-path", str(hermes_project_dir)],
            cwd=tmp_root,
        )
        results.append(check(
            "eifctl init --adapter hermes succeeds from the installed wheel",
            hermes_init_proc.returncode == 0,
            hermes_init_proc.stdout + hermes_init_proc.stderr,
        ))
        hermes_entry_text = (hermes_project_dir / ".hermes.md").read_text(encoding="utf-8") if (hermes_project_dir / ".hermes.md").exists() else ""
        results.append(check(
            "wheel-installed eifctl generates a real .hermes.md with the EIF-managed block",
            "<!-- EIF:BEGIN" in hermes_entry_text and "<!-- EIF:END -->" in hermes_entry_text,
            hermes_entry_text,
        ))
        hermes_cfg_text = (hermes_project_dir / ".eif" / "config.yaml").read_text(encoding="utf-8") if (hermes_project_dir / ".eif" / "config.yaml").exists() else ""
        results.append(check(
            "wheel-installed eifctl records adapter.name: hermes",
            "hermes" in hermes_cfg_text,
            hermes_cfg_text,
        ))
        hermes_doctor_proc = run([str(eifctl_exe), "doctor", "--instance-path", str(hermes_project_dir)], cwd=tmp_root)
        results.append(check(
            "wheel-installed eifctl doctor passes on the generated hermes instance",
            hermes_doctor_proc.returncode == 0,
            hermes_doctor_proc.stdout + hermes_doctor_proc.stderr,
        ))

        # --- 4b. Full synthetic-task journey from the INSTALLED WHEEL, not
        # individual subcommands checked in isolation: a new task with
        # pre-existing project files (src/tests/task-scope.md, no
        # entrypoint yet) -> eifctl init bootstraps EIF onto it -> retrieval
        # surfaces the seeded fact/failure-pattern WITH the authority
        # metadata (status/evidence/confidence) an agent uses to resolve
        # which source to trust -> the pre-authored implementation passes
        # its real test -> Knowledge Delta and closeout (EIF's own
        # promotion-decision and cleanup steps) render to real files in the
        # instance's configured locale -> validation/privacy/doctor all
        # pass. Reuses the demo-workspace's own fixture content (not a
        # second, drifting copy of the same task) - same story as
        # examples/demo-workspace/README.md, proven via `eifctl`, not
        # `python scripts/eif_init.py`. ---
        journey_dir = tmp_root / "journey-pkgtest"
        demo_fixture = FRAMEWORK_ROOT / "examples" / "demo-workspace"
        shutil.copytree(demo_fixture / "src", journey_dir / "src")
        shutil.copytree(demo_fixture / "tests", journey_dir / "tests")
        shutil.copytree(demo_fixture / "knowledge", journey_dir / "knowledge", ignore=shutil.ignore_patterns("index.md"))
        shutil.copy2(demo_fixture / "task-scope.md", journey_dir / "task-scope.md")

        journey_init = run(
            [str(eifctl_exe), "init", "--project-name", "journey-pkgtest", "--adapter", "claude-code",
             "--locale", "uk", "--instance-path", str(journey_dir)],
            cwd=tmp_root,
        )
        results.append(check(
            "eifctl init bootstraps EIF onto a pre-existing synthetic task (retrieval content already seeded)",
            journey_init.returncode == 0,
            journey_init.stdout + journey_init.stderr,
        ))

        journey_search = run([str(eifctl_exe), "search", "leap year"], cwd=journey_dir)
        results.append(check(
            "eifctl search retrieves the seeded fact and failure pattern, with the authority metadata "
            "(status/evidence/confidence) a real retrieval-before-implementation step relies on",
            journey_search.returncode == 0
            and "FACT-0001" in journey_search.stdout
            and "PATTERN-0001" in journey_search.stdout
            and "status=validated" in journey_search.stdout
            and "evidence=OBSERVED" in journey_search.stdout,
            journey_search.stdout + journey_search.stderr,
        ))

        journey_test = run([str(venv_python), str(journey_dir / "tests" / "test_calendar_utils.py"), "-v"])
        results.append(check(
            "the pre-authored implementation passes its real test, run by the venv's own interpreter",
            journey_test.returncode == 0,
            journey_test.stdout + journey_test.stderr,
        ))

        journey_kd = run(
            [str(eifctl_exe), "render", "knowledge-delta", "--instance-root", str(journey_dir)], cwd=tmp_root,
        )
        kd_path = journey_dir / "knowledge-delta.md"
        results.append(check(
            "eifctl render knowledge-delta writes a real file from the installed wheel",
            journey_kd.returncode == 0 and kd_path.exists(),
            journey_kd.stdout + journey_kd.stderr,
        ))
        kd_text = kd_path.read_text(encoding="utf-8") if kd_path.exists() else ""
        results.append(check(
            "the rendered Knowledge Delta is in the instance's configured locale (Ukrainian), "
            "not a silent English fallback",
            any("а" <= c <= "я" for c in kd_text.lower()),
            kd_text,
        ))

        journey_closeout = run(
            [str(eifctl_exe), "render", "session-closeout", "--instance-root", str(journey_dir), "--draft",
             "--set", "task_name=implement is_leap_year", "--set", "branch_or_pr=wheel-journey-test"],
            cwd=tmp_root,
        )
        results.append(check(
            "eifctl render session-closeout (the journey's promotion-decision/cleanup step) "
            "writes a real file from the installed wheel",
            journey_closeout.returncode == 0 and (journey_dir / "session-closeout.md").exists(),
            journey_closeout.stdout + journey_closeout.stderr,
        ))

        run(["git", "init", "-q"], cwd=journey_dir)
        run(["git", "add", "-A"], cwd=journey_dir)
        journey_validate = run(
            [str(eifctl_exe), "validate", "--instance-root", str(journey_dir), "knowledge/**/*.md"], cwd=tmp_root,
        )
        results.append(check(
            "eifctl validate accepts the seeded knowledge artifacts from the installed wheel",
            journey_validate.returncode == 0,
            journey_validate.stdout + journey_validate.stderr,
        ))
        journey_privacy = run([str(eifctl_exe), "privacy-scan", "--repo", str(journey_dir)], cwd=tmp_root)
        results.append(check(
            "eifctl privacy-scan runs clean against the full journey instance",
            journey_privacy.returncode == 0,
            journey_privacy.stdout + journey_privacy.stderr,
        ))
        journey_doctor = run([str(eifctl_exe), "doctor", "--instance-path", str(journey_dir)], cwd=tmp_root)
        results.append(check(
            "eifctl doctor passes on the full journey instance",
            journey_doctor.returncode == 0 and "all checks passed" in journey_doctor.stdout,
            journey_doctor.stdout + journey_doctor.stderr,
        ))

        uninstall = run([str(venv_python), "-m", "pip", "uninstall", "-y", "-q", "engineering-intelligence-framework"])
        results.append(check("uninstall succeeds and removes the console-script entry point", uninstall.returncode == 0 and not eifctl_exe.exists()))

        reinstall = run([str(venv_python), "-m", "pip", "install", "-q", str(wheel_path)])
        results.append(check("reinstall from the same wheel succeeds", reinstall.returncode == 0 and eifctl_exe.exists(), reinstall.stdout + reinstall.stderr))

        # --- 5. No external scripts/ checkout, no decoy module accidentally
        # satisfies imports: a cwd containing its own scripts/eif_init.py
        # and a top-level eif_init.py, each rigged to raise loudly if ever
        # imported, must NOT affect eifctl at all - a console-script entry
        # point never puts cwd on sys.path the way `python script.py` does,
        # but this proves it, rather than assuming it. ---
        decoy_cwd = tmp_root / "decoy-cwd"
        (decoy_cwd / "scripts").mkdir(parents=True)
        decoy_text = "raise ImportError('decoy module was imported - sys.path isolation broken')\n"
        (decoy_cwd / "scripts" / "eif_init.py").write_text(decoy_text, encoding="utf-8")
        (decoy_cwd / "eif_init.py").write_text(decoy_text, encoding="utf-8")
        (decoy_cwd / "engineering_intelligence_framework.py").write_text(decoy_text, encoding="utf-8")
        decoy_version = run([str(eifctl_exe), "version"], cwd=decoy_cwd)
        results.append(check(
            "eifctl ignores a decoy scripts/eif_init.py + top-level eif_init.py/engineering_intelligence_framework.py in cwd",
            decoy_version.returncode == 0 and "eifctl" in decoy_version.stdout and "decoy" not in (decoy_version.stdout + decoy_version.stderr),
            decoy_version.stdout + decoy_version.stderr,
        ))
        decoy_project = decoy_cwd / "decoy-project"
        decoy_init = run(
            [str(eifctl_exe), "init", "--project-name", "decoy-test", "--adapter", "claude-code", "--instance-path", str(decoy_project)],
            cwd=decoy_cwd,
        )
        results.append(check(
            "eifctl init still works with a decoy scripts/ in cwd (never picks up the decoy code)",
            decoy_init.returncode == 0,
            decoy_init.stdout + decoy_init.stderr,
        ))

        # --- 6. sdist -> wheel rebuild in a SEPARATE clean venv - the sdist
        # must be a self-sufficient source distribution on its own, not
        # merely "whatever happened to already be next to the pre-built
        # wheel this run". ---
        sdist_path = sdists[0]
        sdist_extract = tmp_root / "sdist-extract"
        with tarfile.open(sdist_path) as tf:
            tf.extractall(sdist_extract)  # noqa: S202 - our own just-built sdist, not untrusted input
        sdist_src_dirs = [p for p in sdist_extract.iterdir() if p.is_dir()]
        results.append(check("sdist extracts to exactly one top-level directory", len(sdist_src_dirs) == 1, str(sdist_src_dirs)))
        if sdist_src_dirs:
            sdist_src = sdist_src_dirs[0]
            sdist_dist_dir = tmp_root / "sdist-dist"
            sdist_build = run([sys.executable, "-m", "build", "--wheel", "--outdir", str(sdist_dist_dir), str(sdist_src)])
            results.append(check("wheel rebuilds successfully from the extracted sdist alone", sdist_build.returncode == 0, sdist_build.stdout + sdist_build.stderr))
            sdist_wheels = list(sdist_dist_dir.glob("*.whl"))
            if sdist_wheels:
                sdist_venv_dir = tmp_root / "sdist-venv"
                venv.create(sdist_venv_dir, with_pip=True)
                sdist_venv_python = sdist_venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("python.exe" if sys.platform == "win32" else "python")
                sdist_eifctl_exe = sdist_venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / ("eifctl.exe" if sys.platform == "win32" else "eifctl")
                sdist_install = run([str(sdist_venv_python), "-m", "pip", "install", "-q", str(sdist_wheels[0])])
                results.append(check("the sdist-rebuilt wheel installs cleanly into its own fresh venv", sdist_install.returncode == 0, sdist_install.stdout + sdist_install.stderr))
                sdist_version = run([str(sdist_eifctl_exe), "version"])
                results.append(check("eifctl from the sdist-rebuilt wheel runs correctly", sdist_version.returncode == 0 and "eifctl" in sdist_version.stdout, sdist_version.stdout + sdist_version.stderr))

    passed = sum(results)
    print(f"EIF-RESULT: passed={passed} total={len(results)}")
    print(f"\ntest_package_build: {passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
