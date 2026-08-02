# Contributing to Engineering Intelligence Framework

## Current status

EIF 0.2.x is public and maintained by one owner. Focused bug fixes,
documentation corrections, reproducible evidence reports, and small
well-scoped improvements are welcome. For a new capability or a change to
the methodology, start a
[discussion](https://github.com/mike-arbuzov365/engineering-intelligence-framework/discussions)
before writing a large patch; the adapter scope is frozen at
Claude Code, Cursor, Codex, and Hermes.

## Contribution requirements

- All contributions are licensed under [Apache-2.0](LICENSE) by submission
  (see the license grant in `LICENSE` section 5); no separate CLA is planned
  for v0.1.
- Every pull request must include a Knowledge Delta section (what changed in
  the methodology, and why) or an explicit `<!-- no-knowledge-delta:
  mechanical task -->` marker for purely mechanical changes.
- Documentation follows the locale declared for that directory - framework
  identifiers, schemas, code, and command examples stay in English
  regardless of prose locale (see `locales/README.md`).
- PRs must pass the CI checks in
  [`.github/workflows/ci.yml`](.github/workflows/ci.yml) - privacy scan,
  frontmatter/config schema validation, link check, YAML/JSON Schema
  syntax, Knowledge Delta completeness, and the critical-path smoke suite.
  GitHub branch protection requires the consolidated
  `PR smoke checks (required by policy)` context before `main` advances;
  [`scripts/eif_merge_pr.py`](scripts/eif_merge_pr.py) performs the
  repository-specific second gate for maintainer merges.
- Scope discipline: one PR, one logical change. Do not mix refactors with
  new features.

## Local checks

Install the pinned validation dependencies and run the same critical path as
routine pull requests:

```bash
python -m pip install -r scripts/requirements.txt
python scripts/tests/smoke.py
python scripts/eif_privacy_scan.py --repo .
python scripts/eif_check_links.py --repo .
```

If the change affects packaged commands or bundled resources, add the bounded
installed-wheel path:

```bash
python scripts/tests/test_package_smoke.py
```

Before a release, maintainers run the exhaustive package suite once, plus the
full inventory and site gate when those surfaces changed, as documented in
[`.github/workflows/release-check.yml`](.github/workflows/release-check.yml)
and [`site/README.md`](site/README.md).

## Code of conduct

By participating, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security issues

Do not open a public issue for a security or privacy concern - see
[SECURITY.md](SECURITY.md).
