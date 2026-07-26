# docs/

- [`architecture/HOW-EIF-WORKS.md`](architecture/HOW-EIF-WORKS.md) - the
  canonical, single source-of-truth explanation of how EIF works end to
  end. Everything else (README, website copy, articles, FAQ) is meant to
  derive from this document, not diverge from it.
- `concepts/` - focused explanations of individual concepts (not populated
  yet; content currently lives inside HOW-EIF-WORKS.md until it grows large
  enough to split).
- `guides/` - task-oriented how-tos:
  [`vertical-slice.md`](guides/vertical-slice.md) - the target minimum
  functional workflow and its sequencing; [`quickstart.md`](guides/quickstart.md) -
  a real, timed walkthrough from a clean clone to one closed-out change.
  CI/adapter-setup guides are not written yet.
- `product/` - what is claimed publicly and what backs it:
  [`claims-evidence.md`](product/claims-evidence.md) - every public claim
  with its evidence and its bound;
  [`pre-release.md`](product/pre-release.md) - where the release actually
  stands, what no claim is made about, and the release-day checklist. The
  website carries the claims; this directory carries the accounting behind
  them.
- `reference/` - [`config.md`](reference/config.md) - `.eif/config.yaml` and
  `.eif/framework.lock.yaml` field-by-field summary, pointing to the
  authoritative JSON Schemas rather than duplicating them.
- `benchmarks/` - quality-per-token benchmark methodology and results, see
  [`benchmarks/README.md`](benchmarks/README.md).
