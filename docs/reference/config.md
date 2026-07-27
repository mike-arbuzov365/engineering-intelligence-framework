# Configuration reference

Two separate files, deliberately split - see
[`instance-contract.md`](../architecture/instance-contract.md) for why:

| File | Owner | Written by | Schema |
|---|---|---|---|
| `.eif/config.yaml` | **You** (the project) | `eif_init.py`, once, on first init - never overwritten by a routine upgrade | [`core/schemas/eif-config.schema.json`](../../core/schemas/eif-config.schema.json) |
| `.eif/framework.lock.yaml` | **EIF** (managed provenance) | `eif_init.py`, fully regenerated on every init/upgrade | [`core/schemas/framework-lock.schema.json`](../../core/schemas/framework-lock.schema.json) |

This page summarizes both for orientation. The schemas are the actual
source of truth (every field carries its own authoritative description,
enforced by [`scripts/eif_validate_frontmatter.py`](../../scripts/eif_validate_frontmatter.py));
[`.eif/config.yaml.example`](../../.eif/config.yaml.example) is the fully
commented, concrete example most people should copy from rather than
write against the schema directly.

## `.eif/config.yaml` - what you own

| Section | Required | Purpose |
|---|---|---|
| `schema_version` | yes | This file's own schema version. Bump only on a breaking shape change. |
| `project.name` | yes | Your project's display name. |
| `adapter.name` | yes | Which agent adapter the generated entrypoint targets - not an enum in the schema on purpose; [`scripts/eif_adapters.py`](../../scripts/eif_adapters.py)'s registry is the single source of truth for valid names, enforced by `eif_init.py`'s argparse choices. See [adapter compatibility](#adapter-compatibility) below. |
| `adapter.options.<name>` | no | Per-adapter settings that adapter's own registry entry declares. Omit for the adapter's documented default - most projects never need this. Currently defined for `codex` (`project_doc_fallback_filenames`, `project_doc_max_bytes`, `project_root_markers`) and `hermes` (`parent_context_action`, `context_file_max_chars`) - see each key's own schema description for the exact semantics, since both mirror a specific agent's real, primary-source-verified behavior rather than a generic guess. |
| `localization.documentation_locale` | yes | BCP-47 tag for generated project documentation (Knowledge Delta, closeout, status messages). |
| `localization.agent_response_locale` / `fallback_locale` / `preserve_technical_terms` / `code_comments_locale` / `commit_messages_locale` | no | Finer-grained locale controls - see [Language configuration](../architecture/HOW-EIF-WORKS.md#language-configuration). |
| `governance.knowledge_delta_required` / `evidence_labels_required` / `degraded_mode_allowed` | no | Governance toggles - `degraded_mode_allowed` is an explicit acknowledgment that any integration below may be absent or unreachable, not a per-integration behavior switch (see each integration's own `failure_policy`). |
| `knowledge.root` / `knowledge.index_path` / `knowledge.managed` | no | Where knowledge artifacts live, instance-relative. Greenfield default: `knowledge` / `knowledge/index.md` / `true`. An adopted repository can point these at wherever knowledge already lives instead of migrating content to EIF's default layout - both are validated against path escape (absolute, drive/UNC, `..` traversal, outside-instance) by [`scripts/eif_paths.py`](../../scripts/eif_paths.py), not just the schema. |
| `adoption.mode` | no | `greenfield` (default) or `coexist`. Required to be set explicitly via `--adoption-mode` when `eif_init`'s adoption preflight ([`scripts/eif_preflight.py`](../../scripts/eif_preflight.py)) detects pre-existing entrypoint content. See [Existing-repository adoption](../architecture/instance-contract.md#adoption-existing-repositories). |
| `privacy.deny_paths` / `local_denylist_file` / `suppressions` | no | Privacy-scan configuration. `suppressions` are finding-specific (rule + exact path + content fingerprint), never a whole rule+file - see [`scripts/eif_privacy_scan.py`](../../scripts/eif_privacy_scan.py) for the fingerprint algorithm. |
| `integrations.<name>.enabled` / `provider` / `processing` / `data_boundary` / `cost_cap_usd` / `failure_policy` | no | Optional-integration configuration - every integration defaults to disabled. See [`integrations/README.md`](../../integrations/README.md) for what each adds and its degraded mode when off, and [`SECURITY.md`](../../SECURITY.md#threat-model) for why `data_boundary` matters. |

### Adapter compatibility

`adapter.name` accepts one of the four supported adapters: `claude-code`,
`cursor`, `codex`, or `hermes`. D-16 retired the earlier two-tier status,
and adapter scope is frozen at these four - see
[`adapters/README.md`](../../adapters/README.md) for the full registry,
[`adapters/parity-matrix.json`](../../adapters/parity-matrix.json) for
per-adapter capabilities, and
[`adapters/switch-matrix.json`](../../adapters/switch-matrix.json) for
what's proven about switching a project from one to another
(`eif_init.py --force --adapter <name>`).

## `.eif/framework.lock.yaml` - what EIF manages

Never hand-edit this file - a routine upgrade regenerates it completely
and never touches your `config.yaml`. It records exactly which framework
source produced the current instance and lets `eifctl doctor`
(`scripts/eif_verify_runtime.py`) detect drift.

| Section | Purpose |
|---|---|
| `framework.source_type` | Discriminates which provenance shape applies: `git` (a real, git-verified or `--allow-dirty`/`--framework-ref`-asserted commit of a git checkout), `installed-package` (the `eifctl` console script, generated from an installed Python distribution - no git commit to report, never fabricated as one), or `source-bundle` (neither of the above; a caller-asserted identifier, kept structurally separate from a verified commit or real package metadata). |
| `instance.migration_status` | `greenfield` or `adopted` - derived from a dedicated, read-only repository-origin check (any project-owned file outside `.git/`/`.eif/`), independent of the governance/entrypoint preflight, so an existing repo with no `CLAUDE.md` is still correctly recorded `adopted`. |
| `adapter.name` / `adapter.entrypoint` / `adapter.effective_root_markers` | Which adapter and generated entrypoint file this instance actually has, plus (for an adapter with a configurable root-marker concept, e.g. Codex) the exact marker list used - `doctor` recomputes this and fails on drift. |
| `bundle.manifest` / `bundle.digest` | Every file copied from the framework source into this instance's pinned runtime bundle, individually hashed, plus one combined digest - `doctor` re-verifies every file's hash, not just the combined digest, so a single tampered or corrupted file is caught precisely. |
| `knowledge_index` | Present only when `eif_init.py` actually created or regenerated a knowledge index this run - lets `doctor` detect a hand-edited index (hash mismatch) or one that lost its ownership marker. |

## Validating your own config

```
python scripts/eif_validate_frontmatter.py --framework-root . --config .eif/config.yaml
python scripts/eif_validate_frontmatter.py --framework-root . --lock .eif/framework.lock.yaml
```

or, from an installed package: `eifctl validate`. Both run the real
`jsonschema` `Draft202012Validator` with format checking against the
schemas above - not a hand-rolled parser.
