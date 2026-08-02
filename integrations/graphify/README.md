# integrations/graphify/

Structural code-graph navigation and impact analysis.

## Current status: behavioral adapter with portable lifecycle

EIF probes a compatible Graphify CLI, runs `query`, `path` and `explain`
against a synthetic structural fixture, and validates a project-local raw
artifact. Graph generation is deliberately separate: doctor and the lifecycle
tool never start Graphify extraction, a semantic provider or a paid/deep run.

The tested compatibility contract is in [`manifest.json`](manifest.json):
Graphify `>=0.9.12,<0.10.0`, with `0.9.12` behaviorally tested. The range is a
candidate compatibility range, not proof that every version behaves the same.
Install the `graphifyy` package separately from the
[upstream project](https://github.com/safishamsi/graphify). EIF does not install
it or mutate user configuration.

## Structural configuration

```yaml
integrations:
  structural_graph:
    enabled: true
    provider: graphify
    mode: structural
    artifact_path: graphify-out/graph.json
    metadata_path: graphify-out/eif-graph-metadata.json
    scope_manifest_path: .eif/graphify-scope.json
    baseline_commit: null
    processing: local
    data_boundary: local-only
    cost_cap_usd: 0
    failure_policy: degrade
```

Copy and review
[`scope-manifest.example.json`](scope-manifest.example.json) as
`.eif/graphify-scope.json`. Its `repo_id` is explicit and stable across
worktrees; EIF never derives repository identity from a directory name. The
manifest also declares source, semantic and excluded path prefixes.

### This framework repository

The framework checkout has a tracked `.graphifyignore`. It excludes the
website, demonstrations and the generated package mirrors under
`src/engineering_intelligence_framework/{_impl,resources}`. Those mirrors are
required wheel inputs, but indexing them beside their canonical sources would
duplicate nodes and distort navigation.

Build the local, zero-cost structural graph with:

```text
graphify extract . --code-only --no-cluster
graphify cluster-only . --no-label --no-viz
graphify export html
```

The result stays under ignored `graphify-out/`. Source files remain authority;
the graph is a local navigation index and can be rebuilt from the tracked scope.

## Artifact metadata

Every accepted graph has a sidecar with:

- `source_commit`;
- `graphify_version`;
- `manifest_hash`;
- `scope_hash`;
- `graph_sha256`;
- `generated_at`;
- the same explicit `repo_id` as the scope manifest.

After a separately authorized structural graph build, capture metadata without
starting another provider operation:

```text
python .eif/runtime/eif_graphify.py capture-metadata \
  --instance-root . --graphify-version 0.9.12
```

Check lifecycle status:

```text
python .eif/runtime/eif_graphify.py status --instance-root .
```

The output is content-safe. It reports state, hashes, commit identity and a
count of relevant changed files, never source paths or graph content.

## Freshness states

- `fresh` - metadata, graph digest, manifest and declared source scope match;
- `code-update-required` - structural source changed after graph capture;
- `semantic-update-required` - semantic paths or the declared scope changed;
- `full-rebuild-required` - the recorded source commit is not an ancestor of
  current history;
- `blocked` - required artifact, metadata, manifest, Git evidence or digest is
  missing or invalid;
- `suppressed` - the reviewed scope manifest explicitly disables graph use and
  records a reason.

Only `fresh` can map to integration health `healthy`. Update-required states
map to `stale`; full rebuild maps to `misconfigured`; blocked and suppressed
map to `degraded`. Every non-fresh state tells the agent to use source search
and manual navigation.

## Portable restore

Restore accepts only a graph JSON or gzip archive plus its validated metadata:

```text
python .eif/runtime/eif_graphify.py restore --instance-root . \
  --archive graph.json.gz --metadata-source eif-graph-metadata.json
```

The tool verifies explicit `repo_id`, scope and manifest hashes, graph digest
and JSON shape before staged same-volume replacement. It never guesses a repository from the
worktree folder, never regenerates a graph and never silently substitutes a
Markdown report.

## Semantic and deep safety gate

Structural mode must remain `local`/`local-only` with a zero cost cap.
`semantic` or `deep` requires all of:

- `processing: external`;
- `data_boundary: external-api`;
- a non-empty `semantic_provider`;
- a positive `cost_cap_usd`.

Missing any field fails closed as `misconfigured`. Even with a complete gate,
doctor only runs local structural canaries and reports `degraded` until a
separately approved semantic run supplies evidence. Doctor never initiates a
paid/provider scan.

## Authority and fallback

Graph output is navigation evidence, not source authority. Verify every
graph-derived claim against source files before editing or deciding. If
Graphify is disabled, unavailable, non-fresh or degraded, use source search
and manual navigation; core EIF remains functional.
