#!/usr/bin/env python3
"""Model-free baseline of the context an agent receives in a synthetic EIF instance.

Creates one disposable instance per adapter with `eifctl new` in a temporary
directory, then measures bytes (and an approximate token count) of what a host
loads or an agent is told to read. No model, network or private data is used.

Usage:
    python measure_baseline.py [--eifctl "eifctl"] [--runs 5] [--out baseline.json]

`--eifctl` is the command that starts eifctl. Default: `eifctl`. From a source
checkout: --eifctl "python -W ignore -m engineering_intelligence_framework.cli"
with PYTHONPATH pointing at src/.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shlex
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ADAPTERS = {
    "claude-code": {"entrypoint": "CLAUDE.md", "skills": ".claude/skills"},
    "codex": {"entrypoint": "AGENTS.md", "skills": ".agents/skills"},
    "cursor": {"entrypoint": ".cursor/rules/eif/governance.mdc", "skills": ".cursor/skills"},
    "hermes": {"entrypoint": ".hermes.md", "skills": ".hermes/skills"},
}
WALK_SKILLS = ("run-execution-packet", "plan-execution-packet", "knowledge-search")
LINK_RE = re.compile(r"\]\(([^)#\s]+\.md)(?:#[^)]*)?\)")
FRONTMATTER_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)


def size(path: Path) -> dict:
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "lines": data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1),
        "est_tokens": math.ceil(len(data) / 4),
    }


def total(items: list[dict]) -> dict:
    byte_sum = sum(item["bytes"] for item in items)
    return {"bytes": byte_sum, "est_tokens": math.ceil(byte_sum / 4)}


def frontmatter_bytes(path: Path) -> int:
    text = path.read_bytes().decode("utf-8")
    match = FRONTMATTER_RE.match(text)
    return len(match.group(0).encode("utf-8")) if match else 0


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, bytes, float]:
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, check=False)
    elapsed = time.perf_counter() - started
    return proc.returncode, proc.stdout + proc.stderr, elapsed


def one_hop_reads(runtime: Path, skill: str) -> list[Path]:
    source = runtime / "skills" / skill / "SKILL.md"
    reads = [source]
    for target in LINK_RE.findall(source.read_text(encoding="utf-8")):
        if "://" in target:
            continue
        resolved = (source.parent / target).resolve()
        if resolved.is_file() and runtime.resolve() in resolved.parents and resolved not in reads:
            reads.append(resolved)
    return reads


def measure_instance(eifctl: list[str], root: Path, adapter: str, runs: int) -> dict:
    spec = ADAPTERS[adapter]
    project = root.resolve() / f"inst-{adapter}"
    rc, out, _ = run([*eifctl, "new", str(project), "--project-name", "synthetic-demo", "--adapter", adapter])
    if rc != 0:
        raise SystemExit(f"eifctl new failed for {adapter}: {out.decode('utf-8', 'replace')[-400:]}")

    runtime = project / ".eif" / "runtime"
    entry = size(project / spec["entrypoint"])

    loaders = sorted((project / spec["skills"]).glob("*/SKILL.md"))
    loader_full = [size(path) for path in loaders]
    loader_meta = [frontmatter_bytes(path) for path in loaders]

    rc, doctor_out, _ = run([*eifctl, "doctor", "--instance-path", str(project)])
    timings = [run([*eifctl, "doctor", "--instance-path", str(project)])[2] for _ in range(runs)]
    version_timings = [run([*eifctl, "version"])[2] for _ in range(runs)]
    import_timings = [
        run([sys.executable, "-W", "ignore", "-c", "import engineering_intelligence_framework.cli"])[2]
        for _ in range(runs)
    ]

    walks = {}
    for skill in WALK_SKILLS:
        reads = one_hop_reads(runtime, skill)
        sizes = [size(path) for path in reads]
        walks[skill] = {
            "files": [path.relative_to(runtime).as_posix() for path in reads],
            "total": total(sizes),
        }

    fm_bytes = sum(loader_meta)
    full_loader_bytes = sum(item["bytes"] for item in loader_full)
    base_bytes = entry["bytes"] + fm_bytes + len(doctor_out)

    def scenario(count: int) -> dict:
        return {"bytes": count, "est_tokens": math.ceil(count / 4)}

    scenarios = {
        "light": scenario(base_bytes),
        "knowledge_search": scenario(base_bytes + walks["knowledge-search"]["total"]["bytes"]),
        "packet_plan": scenario(base_bytes + walks["plan-execution-packet"]["total"]["bytes"]),
        "packet_run": scenario(base_bytes + walks["run-execution-packet"]["total"]["bytes"]),
        "light_if_host_loads_full_loaders": scenario(base_bytes - fm_bytes + full_loader_bytes),
    }

    return {
        "adapter": adapter,
        "scenarios": scenarios,
        "tier_a_always_loaded": {
            "entrypoint": {"path": spec["entrypoint"], **entry},
            "skill_loaders": {
                "count": len(loaders),
                "frontmatter_only": {
                    "bytes": sum(loader_meta),
                    "est_tokens": math.ceil(sum(loader_meta) / 4),
                },
                "full_files": total(loader_full),
            },
        },
        "tier_b_first_task": {
            "doctor_stdout": {"exit_code": rc, "bytes": len(doctor_out), "est_tokens": math.ceil(len(doctor_out) / 4)},
            "skill_walks_one_hop": walks,
        },
        "runtime_bundle": {
            "files": sum(1 for p in runtime.rglob("*") if p.is_file()),
            "bytes": sum(p.stat().st_size for p in runtime.rglob("*") if p.is_file()),
        },
        "latency_seconds": {
            "note": "machine-dependent; cold subprocess; median of runs",
            "runs": runs,
            "doctor_median": round(statistics.median(timings), 3),
            "version_median": round(statistics.median(version_timings), 3),
            "import_cli_median": round(statistics.median(import_timings), 3),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--eifctl", default="eifctl")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--out")
    parser.add_argument("--source-ref", default="unspecified", help="Free-text note: where this eifctl came from.")
    args = parser.parse_args()
    eifctl = shlex.split(args.eifctl)

    rc, version, _ = run([*eifctl, "version"])
    with tempfile.TemporaryDirectory(prefix="eif-baseline-") as tmp:
        result = {
            "method": {
                "token_estimate": "ceil(bytes / 4); an approximation, not a tokenizer count",
                "eifctl_version": version.decode("utf-8", "replace").strip().splitlines()[-1],
                "python": sys.version.split()[0],
                "source_ref": args.source_ref,
                "instances": "synthetic, created by `eifctl new`, project name synthetic-demo",
                "scenarios": "light = entrypoint + skill frontmatter + one doctor run; the others add the one-hop skill walk; assumes the host loads only skill frontmatter at start",
                "tier_a": "loaded by the host without an agent decision",
                "tier_b": "the entrypoint tells the agent to read or run these on the first task",
                "walk_limits": "one hop of relative .md links from the runtime skill source; deeper reads not counted",
            },
            "adapters": [measure_instance(eifctl, Path(tmp), adapter, args.runs) for adapter in ADAPTERS],
        }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
