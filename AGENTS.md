# AGENTS.md - engineering-intelligence-framework

Instructions for AI agents working in this repository. Kept compact
deliberately, per this framework's own design principle of not duplicating
detailed reference material into a persistent, always-loaded file - the
detailed reference lives in [`core/`](core/) and [`docs/`](docs/).

## What this repo is

The framework itself (see [`docs/architecture/HOW-EIF-WORKS.md`](docs/architecture/HOW-EIF-WORKS.md#framework-vs-project-instance)).
No project-specific code, no private data, no product logic.

## Before making a change

1. Read [`core/policies/decisions.md`](core/policies/decisions.md) - do not
   contradict a `ratified` decision without proposing an explicit
   supersession; `provisional`/`open` items can be revised more freely.
2. Check whether the claim you're about to make is Available, Draft,
   Experimental, Planned, or Not built (see the capability matrix in
   [`README.md`](README.md)). Do not describe target design as current
   behavior.
3. Run `python scripts/eif_privacy_scan.py` before committing anything
   that references a real project, path, or person - this repo must never
   contain private repository names, machine-specific paths, or
   owner-identifying detail. See [`SECURITY.md`](SECURITY.md).

## Making a change

- One PR, one logical change - see [`CONTRIBUTING.md`](CONTRIBUTING.md).
- Every methodology-affecting PR includes a Knowledge Delta section (the
  PR template prompts for it); purely mechanical PRs use
  `<!-- no-knowledge-delta: mechanical task -->` instead.
- If you edit `core/ontology/*.md`, check whether
  `core/schemas/knowledge-frontmatter.schema.json` needs a matching update
  - the schema is the enforced source, the Markdown is the explained one.
  Run `python scripts/eif_validate_frontmatter.py` to check.
- If you add or change a relative Markdown link, run
  `python scripts/eif_check_links.py` before committing.
- Do not add empty directory stubs beyond what's needed to explain
  structure - prefer a working, if small, vertical slice over a large
  skeleton of "not built yet" placeholders. See
  [`docs/guides/vertical-slice.md`](docs/guides/vertical-slice.md) for the
  current target slice.

## Do not

- Do not change repository visibility, or suggest doing so as part of a
  routine change - see [`core/policies/decisions.md`](core/policies/decisions.md)
  and [`GOVERNANCE.md`](GOVERNANCE.md).
- Do not claim a token-savings or quality number without a reproducible
  benchmark - see [`docs/benchmarks/README.md`](docs/benchmarks/README.md).
- Do not assume a hook enforces anything until verified end-to-end for the
  specific agent/version - see
  [`adapters/README.md`](adapters/README.md).
