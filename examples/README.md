# examples/

Synthetic, no-private-dependency examples that demonstrate the full
workflow end to end.

```text
examples/
  demo-workspace/       # built - single product repo using EIF (see below)
```

[`demo-workspace/`](demo-workspace/) is a real, materialized EIF instance
(own `.eif/config.yaml`, `.eif/framework.lock.yaml`, pinned
`.eif/runtime/` bundle, generated `CLAUDE.md`) against a synthetic
leap-year calculator: initialize the instance, seed and search real
knowledge, scope and implement one real change informed by that
retrieval, verify it with a real failing-before/passing-after test, and
close out truthfully in Ukrainian. See
[`demo-workspace/README.md`](demo-workspace/README.md) for the exact
commands and captured output, and
[`docs/product/claims-evidence.md`](../docs/product/claims-evidence.md)
for what this demo does and does not prove (one scenario, one adapter,
single operator this session - not yet reproduced independently).

A separate multi-repo demo workspace is not built - this single-repo
scenario is the only one exercised so far, see
[`docs/guides/vertical-slice.md`](../docs/guides/vertical-slice.md) for
what was deliberately scoped out of v0.1.
