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

| Script | Does | Used by |
|---|---|---|
| [`eif_privacy_scan.py`](eif_privacy_scan.py) | Scans tracked files for absolute-path leaks, secret-shaped patterns, and instance-specific denylisted tokens (`.eif/local-denylist.txt`, gitignored). Redacts all matched values in output - reports file:line only. Fails closed if `git ls-files` fails. | CI, and manually before any commit that references a real project/path/person |
| [`eif_validate_frontmatter.py`](eif_validate_frontmatter.py) | Validates knowledge-artifact YAML frontmatter (default mode) or `.eif/config.yaml` (`--config PATH`) against the JSON Schemas in `core/schemas/`, using PyYAML + `jsonschema`'s `Draft202012Validator` with format checking. `--framework-root`/`--instance-root` let a project instance validate against this framework's schemas without vendoring the framework source. | CI |
| [`eif_check_links.py`](eif_check_links.py) | Checks relative Markdown links (and same-file/cross-file anchors) resolve | CI |
| [`eif_check_knowledge_delta.py`](eif_check_knowledge_delta.py) | Classifies a PR body's Knowledge Delta section as `meaningful` / `mechanical` / `empty` - a bare "does the heading exist" check always passes because the PR template always has the heading | CI |
| [`eif_merge_pr.py`](eif_merge_pr.py) | Controlled merge entrypoint - genericized port of the private instance's `merge-pr.ps1` pattern. Re-verifies all CI checks are green, Knowledge Delta is meaningful, and review state is clean, then merges pinned to the verified head SHA. Requires the `gh` CLI. | Manual (`python scripts/eif_merge_pr.py --pr N --dry-run` to check without merging); not wired into an agent-side hook guard yet since no adapters are ported (see [`adapters/README.md`](../adapters/README.md)) |

## Development / testing

```bash
python scripts/tests/test_validate.py           # frontmatter + config schema fixtures (positive + negative)
python scripts/tests/test_privacy_scan.py        # detection, false positives, fail-closed, redaction
python scripts/tests/test_knowledge_delta.py     # meaningful/mechanical/empty classification
```

All three are self-contained (use `tempfile`/subprocess, don't touch this
repository's own tracked files) and run in CI on every PR - see
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml). Positive
fixtures live in `scripts/tests/fixtures/{frontmatter,config}/` and must
pass; negative fixtures must fail. Run
`python scripts/eif_privacy_scan.py --repo .` before committing anything
that references a real project, path, or person.

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

Bootstrap (`eifctl init` equivalent), health checks (`eifctl doctor`
equivalent), knowledge-index generation, graph-freshness checks, and
merge-gate enforcement. The private instance has working, tested versions
of a graph-freshness checker and a controlled merge-gate script; porting
requires removing private repo names and machine-specific paths from both
the script and its default config. See
[`docs/guides/vertical-slice.md`](../docs/guides/vertical-slice.md) for
sequencing.
