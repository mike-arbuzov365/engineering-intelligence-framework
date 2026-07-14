# Contributing to Engineering Intelligence Framework

## Current status

This repository is being extracted from a private production instance
(see [`docs/architecture/HOW-EIF-WORKS.md`](docs/architecture/HOW-EIF-WORKS.md)
for the framework/instance split). Until the
[Definition of Public-Ready](docs/architecture/HOW-EIF-WORKS.md#definition-of-public-ready)
checklist is complete, this project is **not accepting external pull
requests**. Issues and discussion are welcome once the repository is public.

## When contributions open

- All contributions are licensed under [Apache-2.0](LICENSE) by submission
  (see the license grant in `LICENSE` section 5); no separate CLA is planned
  for v0.1.
- Every pull request must include a Knowledge Delta section (what changed in
  the methodology, and why) or an explicit `<!-- no-knowledge-delta:
  mechanical task -->` marker for purely mechanical changes.
- Documentation follows the locale declared for that directory - framework
  identifiers, schemas, code, and command examples stay in English
  regardless of prose locale (see `locales/README.md`).
- PRs must pass the CI gates described in `docs/guides/` before merge; a
  failed mandatory check must technically block the merge path, not just be
  documented as a rule.
- Scope discipline: one PR, one logical change. Do not mix refactors with
  new features.

## Code of conduct

By participating, you agree to abide by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security issues

Do not open a public issue for a security or privacy concern - see
[SECURITY.md](SECURITY.md).
