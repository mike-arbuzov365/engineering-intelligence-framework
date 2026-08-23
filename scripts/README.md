# scripts/

## Setup

```bash
pip install -r scripts/requirements.txt
```

Pinned exact versions (`PyYAML==6.0.2`, `jsonschema[format-nongpl]==4.23.0`) -
see [`requirements.txt`](requirements.txt). The `[format-nongpl]` extra pulls
in `rfc3339-validator`/`rfc3986-validator` (both MIT) so `format: date`/
`format: date-time`/`format: uri` in the JSON Schemas are actually enforced,
not silently skipped - without the GPL-3.0-or-later `rfc3987` that the plain
`[format]` extra would pull in for the same formats. See
[`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) and
`scripts/tests/test_format_dependencies.py`, which enumerates the exact set
of formats EIF's schemas declare and proves the installed dependency set
covers all of them.

## Available

Bootstrap and instance lifecycle (experimental - see
[`docs/architecture/instance-contract.md`](../docs/architecture/instance-contract.md)):

| Script | Does | Used by |
|---|---|---|
| [`eif_init.py`](eif_init.py) | Initializes, upgrades, or (`--force`) reconfigures a project instance in any directory: real dirty-checked framework provenance, a hashed `.eif/runtime/` source bundle, a marker-safe generated entrypoint (e.g. `CLAUDE.md`), and (when `knowledge.managed: true`) a generated knowledge index - all as one ordered, rollback-on-failure transaction (a mid-copy partial `.next` is cleaned up too). Runs an adoption preflight (see `eif_preflight.py`) before writing anything, and derives the historical `migration_status` from a separate read-only repository-origin check (project files outside `.git/`/`.eif/`), so an existing repo with no `CLAUDE.md` is recorded `adopted`, not `greenfield`. | Manual; `--dry-run` shows the same report a real run would enforce without writing |
| [`eif_preflight.py`](eif_preflight.py) | Detects pre-existing project state (an entrypoint file with real content and no EIF markers, a knowledge-index path collision) before `eif_init.py` writes anything, and classifies each observation OK / WARN / STOP | Called by `eif_init.py`; not a standalone CLI entrypoint |
| [`eif_paths.py`](eif_paths.py) | Shared path-policy helper: rejects absolute paths, Windows drive/UNC paths, `..` traversal, any `knowledge.root`/`knowledge.index_path` value that resolves outside the instance directory, and shell metacharacters (a strict allowlist of alnum + `/ \ . _ -` + space) so the configured path is always safe to quote into the generated commands. A JSON Schema `pattern` alone cannot catch all of these. | Called by `eif_init.py`; not a standalone CLI entrypoint |
| [`eif_markers.py`](eif_markers.py) | Shared BEGIN/END managed-block logic (exactly one well-formed pair, atomic merge/replace) used for both `CLAUDE.md` and `.gitignore` | Called by `eif_init.py`/`eif_verify_runtime.py`; not a standalone CLI entrypoint |
| [`eif_adapters.py`](eif_adapters.py) | The adapter registry (which agent an entrypoint can be generated for) and the entrypoint filename for each. One entry today: `claude-code` -> `CLAUDE.md`. | Called by `eif_init.py`/`eif_verify_runtime.py`; not a standalone CLI entrypoint |
| [`eif_verify_runtime.py`](eif_verify_runtime.py) | Bundled "doctor" command: config/lock schema validity, manifest digest self-consistency, per-file bundle hash verification, missing/unexpected-file detection, config/adapter/lock/entrypoint consistency, migration-provenance consistency (`adoption.mode` vs `migration_status`), provenance notes, marker integrity, and drift between `.eif/config.yaml` and the generated entrypoint block or knowledge index (catches a hand-edit with no regeneration) - all from the instance's own bundle, no framework checkout needed | Manual (`.eif/runtime/eif_verify_runtime.py --framework-root .eif/runtime`); CI (`vertical-slice` job) |
| [`eif_generate_index.py`](eif_generate_index.py) | Builds `knowledge.index_path` from every artifact under `knowledge.root`: valid, malformed-YAML, and schema-invalid rows reported as three distinct, honest categories | Called by `eif_init.py`; also runnable standalone to regenerate the index after adding knowledge |
| [`eif_search_knowledge.py`](eif_search_knowledge.py) | Offline, Unicode-aware, lifecycle- and schema-aware keyword search over an instance's knowledge index - excludes `rejected`/`superseded` by default, reports unparseable-YAML vs. schema-invalid vs. not-found as separate outcomes | Manual, and by the generated entrypoint's retrieval instruction |
| [`eif_locale.py`](eif_locale.py) / [`eif_render.py`](eif_render.py) | Config-driven localized rendering (status messages, Knowledge Delta, session closeout) - reads `documentation_locale` from `.eif/config.yaml`, writes real files atomically, fails loudly on a broken config, requires `--draft` to allow an unresolved-placeholder partial render | Called by `eif_init.py`'s status messages; `eif_render.py` runnable standalone for Knowledge Delta/closeout |

Validation and CI-gate scripts:

| Script | Does | Used by |
|---|---|---|
| [`eif_privacy_scan.py`](eif_privacy_scan.py) | Scans tracked files for absolute-path leaks, secret-shaped patterns, and instance-specific denylisted tokens (`.eif/local-denylist.txt`, gitignored). Redacts all matched values in output - reports file:line only. Fails closed if `git ls-files` fails, and fails loudly (not a silent empty-suppressions pass) if an EXISTING `.eif/config.yaml` is unreadable - invalid YAML, not a mapping, or PyYAML unavailable. Supports a narrow, finding-specific suppression mechanism (`privacy.suppressions` in config: rule + exact path + content fingerprint + rationale + reviewed date; an expired or no-longer-matching suppression is itself reported as a finding). | CI, and manually before any commit that references a real project/path/person |
| [`eif_validate_frontmatter.py`](eif_validate_frontmatter.py) | Validates knowledge-artifact YAML frontmatter (default mode) or `.eif/config.yaml`/`.eif/framework.lock.yaml` (`--config`/`--lock PATH`) against the JSON Schemas in `core/schemas/`, using PyYAML + `jsonschema`'s `Draft202012Validator` with format checking. `--framework-root`/`--instance-root` let a project instance validate against this framework's schemas without vendoring the framework source. | CI |
| [`eif_check_links.py`](eif_check_links.py) | Checks relative Markdown links (and same-file/cross-file anchors) resolve | CI |
| [`eif_check_knowledge_delta.py`](eif_check_knowledge_delta.py) | Classifies a PR body's Knowledge Delta section as `meaningful` / `mechanical` / `empty` - a bare "does the heading exist" check always passes because the PR template always has the heading | CI |
| [`eif_merge_pr.py`](eif_merge_pr.py) | Controlled merge entrypoint - genericized port of the private instance's `merge-pr.ps1` pattern. Re-verifies all CI checks are green, Knowledge Delta is meaningful, and review state is clean, then merges pinned to the verified head SHA. Requires the `gh` CLI. | Manual (`python scripts/eif_merge_pr.py --pr N --dry-run` to check without merging); not wired into an agent-side hook guard yet - the one adapter that exists (Claude Code) ships no hook scripts, see [`adapters/README.md`](../adapters/README.md) |
| [`eif_check_licenses.py`](eif_check_licenses.py) | Checks the SBOM-declared dependency closure's (`sbom.cdx.json`, default) or the live interpreter's (`--environment`, opt-in) licenses against [`core/policies/license-policy.json`](../core/policies/license-policy.json) - blocks GPL/AGPL-family and undeclared licenses, checks `requirements.txt` is fully pinned, and (default mode only) fails if the SBOM's pinned-package versions disagree with `requirements.txt` | CI (Windows + Ubuntu, default mode) |
| [`sync_package_sources.py`](sync_package_sources.py) | Syncs the canonical `scripts/eif_*.py` implementation + framework resource trees into `src/engineering_intelligence_framework/` byte-for-byte, so the installable package's bundled copies never silently fork from their source of truth. `--check` verifies without writing. | Manual after any change to a synced file; package smoke and release package gate |
| [`eif_release.py`](eif_release.py) | Builds the sdist and wheel, validates both against what a package index requires (`twine check --strict`, installed into a throwaway environment rather than required on the host), installs the built wheel into a clean virtualenv and runs `eifctl version` from it. Prints the publish commands and stops: it never uploads, because publication takes owner credentials and is an owner decision. `--require-final-version` refuses a `.dev`/`rc` version; `--skip-index-check` for an offline run. | Manual before a technical preview or release |

## Development / testing

The canonical inventory contains 38 self-contained suites in
[`scripts/tests/run_all.py`](tests/run_all.py). They use
`tempfile`/subprocess, do not touch this repository's tracked files, and need
only `scripts/requirements.txt`:

```bash
python scripts/tests/run_all.py
```

The canonical inventory is the `SUITES` list in
[`tests/run_all.py`](tests/run_all.py), including the RTK, Graphify and shared
integration-contract suites. Positive frontmatter/config fixtures live in
`scripts/tests/fixtures/{frontmatter,config}/` and must pass; negative
fixtures must fail. Run `python scripts/eif_privacy_scan.py --repo .`
before committing anything that references a real project, path, or
person.

Package checks are deliberately **not** in `run_all.py` and need their own
extra tooling (`pip install build hatchling`). Putting `build`/`hatchling` in
`scripts/requirements.txt` would misrepresent them as a runtime dependency
of EIF itself.

Use the smallest gate that answers the current question:

| When | Command | Scope |
|---|---|---|
| Routine change | `python scripts/tests/smoke.py` | Source critical path; this is the only automatic GitHub PR test suite. Measured 15.6s. |
| You changed specific files | `python scripts/tests/route_changed.py` | Smoke plus the suites your changed paths map to. Measured 24.9s on a seven-suite selection. An unclassified path escalates to the full inventory. |
| Package-relevant change | `python scripts/tests/test_package_smoke.py` | One wheel, one clean environment, one Codex `graphic-design` project, one `doctor`; prints each stage and enforces bounded command timeouts. |
| Release only | `python scripts/tests/test_package_build.py` | Exhaustive wheel + sdist, two clean environments, reinstall, all adapters/integrations, corruption and installed-package journeys. |
| Release inventory | `python scripts/tests/run_all.py` | Every suite. Measured about 17 minutes for 1822 checks. Not a routine gate. |

`smoke.py` covers the critical flow and touches no skill, contract, or
template. A governance-text change therefore passes it and can still be
broken, which is what happened on 2026-08-19: an edit under
`skills/run-execution-packet/` passed `eifctl skills check` and four
hand-picked suites, then failed `test_skill_contracts.py` in the release
inventory seventeen minutes later. `route_changed.py` exists to close that
gap; it selects by changed path rather than by memory, and it selected the
missing suite on the same input.

Prefer `route_changed.py` over re-running the full inventory. Running
every suite to prove one file is the expensive habit this table is meant
to prevent.

Install the build tools once, then use the short package smoke during ordinary
work:

```bash
pip install build hatchling
python scripts/tests/test_package_smoke.py
```

Run the exhaustive package suite once, locally, at the release gate:

```bash
python scripts/tests/test_package_build.py
```

Do not run both the full `run_all.py` inventory and the exhaustive package
suite for an ordinary small change. Select focused suites plus package smoke;
reserve both exhaustive gates for a release. The manual GitHub release workflow
remains an owner-triggered fallback, but local execution spends no Actions
minutes.

## Dependency update ownership

`scripts/requirements.txt` is pinned deliberately, not floating on
`latest`. Bumping a version is a normal PR (not a special process) but
must:

1. Change the pin in `requirements.txt` explicitly (`pip install
   package==X.Y.Z`, then copy the resolved version in - don't hand-guess
   a version number).
2. Re-run all three test scripts above locally with the new version
   installed.
3. State the version bump and why in the PR's Knowledge Delta.

The same applies to the pinned GitHub Actions revisions in
`.github/workflows/ci.yml` (pinned to commit SHA, not a mutable tag) -
bump by looking up the new tag's commit SHA (e.g. via `gh api
repos/<owner>/<repo>/git/refs/tags/<tag>`), not by trusting a floating
`@v4`-style reference.

## Installable package (`eifctl`)

`pyproject.toml` at the repo root builds a real, installable package
(`pip install .`, not yet published to PyPI) with a console command
`eifctl` - see the root [`README.md`](../README.md#current-capability)'s
package row for the full picture. The package's own source lives under
`src/engineering_intelligence_framework/` and is kept in sync with the
scripts above by [`sync_package_sources.py`](sync_package_sources.py) -
run it (and `--check` in CI) after changing any script or resource tree
the package bundles. D-05/D-08 are now Ratified - the CI package-build
matrix (Windows + Ubuntu, Python 3.11/3.12) confirmed green on all 4
combinations, twice, across two separate commits.

## Not populated yet

Graph-freshness checks (the private instance has a working, tested
checker; porting requires removing private repo names and machine-specific
paths from it and its default config). See
[`docs/guides/vertical-slice.md`](../docs/guides/vertical-slice.md) for
sequencing.
