# integrations/rtk/

Shell-output compression with tracked, per-command token savings. Not
ported yet - see [`integrations/README.md`](../README.md) for the
degraded-mode fallback (commands run unfiltered) and data-boundary notes.

Planned content: hook templates for each supported agent adapter, the
command-registry pattern (canonical filtered form per command class), and
the correctness-first discipline described in
[`docs/architecture/HOW-EIF-WORKS.md#shell-output-compression-integration`](../../docs/architecture/HOW-EIF-WORKS.md#shell-output-compression-integration) -
a filter that silently returns wrong output is worse than no filter.
