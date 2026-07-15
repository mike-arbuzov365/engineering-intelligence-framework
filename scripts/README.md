# scripts/

## Setup

```bash
pip install -r scripts/requirements.txt
```

Pinned exact versions (`PyYAML==6.0.2`, `jsonschema[format]==4.23.0`) - see
[`requirements.txt`](requirements.txt). The `[format]` extra pulls in
`rfc3339-validator`/`rfc3987` so `format: date`/`format: uri` in the JSON
Schemas are actually enforced, not silently skipped.

## Available

Bootstrap and instance lifecycle (experimental - see
[`docs/architecture/instance-contract.md`](../docs/architecture/instance-contract.md)):

| Script | Does | Used by |
|---|---|---|
| [`eif_init.py`](eif_init.py) | Initializes, upgrades, or (`--force`) reconfigures a project instance in any directory: real dirty-checked framework provenance, a hashed `.eif/runtime/` source bundle, a marker-safe generated entrypoint (e.g. `CLAUDE.md`), and (when `knowledge.managed: true`) a generated knowledge index - all as one ordered, rollback-on-failure transaction. Runs an adoption preflight (see `eif_preflight.py`) before writing anything. | Manual; `--dry-run` shows the same report a real run would enforce without writing |
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

## Development / testing

13 suites under `scripts/tests/`, all self-contained (use
`tempfile`/subprocess, don't touch this repository's own tracked files),
all run in CI on every PR - see
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) and
[`scripts/tests/run_all.py`](tests/run_all.py) (runs all of them locally,
one process each, and reports a single ok/FAIL summary line per suite):

```bash
python scripts/tests/run_all.py
```

`test_validate.py` (frontmatter + config/lock schema fixtures, positive +
negative), `test_privacy_scan.py`, `test_knowledge_delta.py`,
`test_paths.py`, `test_markers.py`, `test_init.py`, `test_verify_runtime.py`,
`test_generate_index.py`, `test_search_knowledge.py`, `test_locale.py`,
`test_render.py`, `test_journey.py` (a real subprocess journey against a
fresh seed instance), `test_adoption.py` (adoption/coexistence against a
realistic sanitized fixture). Positive frontmatter/config fixtures live in
`scripts/tests/fixtures/{frontmatter,config}/` and must pass; negative
fixtures must fail. Run `python scripts/eif_privacy_scan.py --repo .`
before committing anything that references a real project, path, or
person.

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

## Not populated yet

Graph-freshness checks (the private instance has a working, tested
checker; porting requires removing private repo names and machine-specific
paths from it and its default config) and a ratified, packaged CLI
(`eifctl` or equivalent - D-05/D-08 remain open; today's `eif_init.py` /
`eif_verify_runtime.py` are experimental scripts invoked directly, not a
stable installed command). See
[`docs/guides/vertical-slice.md`](../docs/guides/vertical-slice.md) for
sequencing.
