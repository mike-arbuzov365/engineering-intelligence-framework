# Static context footprint

This is a model-free byte measurement, not a token-cost or quality benchmark.
The script creates disposable `synthetic-demo` instances for all four adapters.
It counts the entrypoint, loader frontmatter, one doctor response and a one-hop
walk of relative Markdown links from each scenario's skill. It never reads a
private instance. Doctor output replaces the temporary instance root with `.`;
UTF-8 is forced and timing is omitted. These normalizations make repeated runs
comparable. Token estimates are `ceil(bytes / 4)`, not tokenizer counts.

```text
python scripts/eif_context_footprint.py --no-latency --out measurement.json
python scripts/eif_context_footprint.py --no-latency --check docs/benchmarks/context-footprint/baseline.json
python scripts/tests/test_context_footprint.py
```

[baseline.json](baseline.json) records the source SHA and measured components.
`--check` compares all measured components and ignores provenance notes. B0 is
the pre-implementation source; later intentional policy changes require a new
measurement, never silently replacing B0. Temporary-path normalization means
doctor byte counts differ from the unnormalized planning measurement.

Scenarios: `light` adds only doctor; `knowledge_search`, `packet_plan` and
`packet_run` add their respective skill walk. A separate scenario counts full
loader files in case the host loads more than frontmatter. Runtime bundle size
is reported separately and is not automatically loaded context.

Budgets: reader `tools/list` 6,144 bytes; response 24,576 bytes; brief target
1,536 and hard limit 4,096 bytes; default artifact page 4,000 characters.
A compact entrypoint may ship only after the packet scenario comparison passes
the 15% threshold using actual protocol response sizes. Host schema loading,
deeper policy reads and behavioral quality remain unmeasured. No savings claim
follows from this static measurement.
