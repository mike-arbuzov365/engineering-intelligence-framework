# examples/

Synthetic, no-private-dependency examples that demonstrate the full
workflow end to end.

```text
examples/
  demo-workspace/       # not built yet - multi-repo demo workspace
  demo-product-repo/    # not built yet - single product repo using EIF
```

Planned demo scenario (see
[`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#end-to-end-example)):
a new task, experience retrieval, source authority, structural navigation
(or its fallback), controlled implementation, shell-output compression (or
its fallback), tests, Knowledge Delta, a promotion decision, and session
cleanup - all against synthetic code, no real project data.
