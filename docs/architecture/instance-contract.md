# Instance contract, provenance and upgrade model

<!-- Knowledge source: takeover architecture review 2026-07-15, round 2. The
first version of this document described a single merged config.yaml
carrying both user settings and framework provenance, a full-directory-
replace "runtime bundle" refresh, and no dirty-checking or hashing - a
second independent review found that design would lose user settings on
every upgrade and had no way to detect a corrupted or partial bundle. This
version reflects the actual, redesigned, tested implementation: config/lock
split, transactional staged-and-verified bundle swap, real dirty-checked
provenance with a hashed manifest, and a documented validation surface.
Status: experimental. Does not ratify D-08 (dependency/distribution model). -->

Status: **experimental**. Describes how a project instance records where it
came from and how it is upgraded. Deliberately small and reversible; does not
ratify the final distribution model (D-08 in
[`../../core/policies/decisions.md`](../../core/policies/decisions.md) remains
open).

## What a project instance is

A project instance is any repository initialized (or adopted) by
`scripts/eif_init.py`. It contains:

| Path | Owner | Committed? | Purpose |
|---|---|---|---|
| `.eif/config.yaml` | **you** (created once by eif_init, never overwritten without `--force`) | yes | Desired settings: project name, adapter choice, locale, governance, privacy, integrations |
| `.eif/framework.lock.yaml` | **EIF** (fully regenerated every init/upgrade) | yes | Exact provenance: framework commit, dirty flag, hashed bundle manifest, generated adapter entrypoint, timestamp |
| `.eif/runtime/` | **EIF** (fully regenerated every init/upgrade) | **no** (gitignored - see below) | Pinned *source* bundle of the scripts/schemas/ontology/locales/templates the instance's own commands run against. Still needs `pip install -r .eif/runtime/requirements.txt` - not a self-contained interpreter environment. |
| `CLAUDE.md` (EIF-managed block only) | split: EIF owns the marked block, you own everything else | yes | Agent entrypoint - the `EIF:BEGIN`/`EIF:END` block is regenerated on upgrade, content outside it is never touched |
| `knowledge/` | **you** | yes | The instance's own knowledge artifacts - never modified by init or upgrade |
| `.gitignore` (EIF-managed block only) | split, same pattern as CLAUDE.md | yes | Ignores `.eif/runtime/`, `.eif/runtime.next/`, `.eif/runtime.previous/`, `*.bak-*` so the regenerable bundle and backups are never committed by accident |

**Why config and lock are two files, not one.** An earlier version of this
design put framework provenance directly inside `.eif/config.yaml` and
regenerated the whole file on every upgrade (via `--force`), which meant an
upgrade could silently discard any user-owned setting added since init - a
real risk for a real project with real custom configuration. Splitting them
means a routine upgrade (`eif_init` re-run **without** `--force`) never
touches `.eif/config.yaml` at all - only the lock, the bundle, and the
managed `CLAUDE.md` block refresh.

The instance does **not** need the framework checked out to run its own
commands: `python .eif/runtime/eif_search_knowledge.py ...` works standalone,
with only a one-time `pip install` and no framework repo on the path.

## Provenance

`.eif/framework.lock.yaml` records exactly what produced this instance -
never a placeholder:

```yaml
lock_schema_version: 1
framework:
  ref: <full 40-char SHA>       # git rev-parse HEAD of --framework-root
  ref_short: <short SHA>
  dirty: false                  # true if --framework-root had uncommitted changes
instance:
  eif_instance_version: 0.1.0
  migration_status: greenfield  # or: adopted
adapter:
  name: claude-code
  entrypoint: CLAUDE.md
bundle:
  path: .eif/runtime
  manifest:                     # every bundled file, hashed
    - path: eif_search_knowledge.py
      sha256: <64-hex>
    - ...
  digest: sha256:<64-hex>       # combined hash over the whole manifest
generated_at: "2026-07-15T12:34:56+00:00"
```

`eif_init` refuses to materialize from a **dirty** framework checkout by
default - if `--framework-root` has uncommitted changes, the bundle would not
actually match the recorded `ref`, so the tool stops and asks for
`--allow-dirty` (which proceeds and records `dirty: true`) rather than
silently claiming a false provenance guarantee. Every bundled file is
sha256-hashed both from the source (building the manifest) and again after
staging (`verify_staged_bundle`), so a copy-time corruption is caught before
the bundle ever goes live.

## Transactional init/upgrade

The bundle is never replaced in place. `eif_init`:

1. resolves and validates provenance (dirty-check, mandatory-source check);
2. renders config and lock **in memory** and validates both against their
   schemas *before writing anything*;
3. stages the new bundle into `.eif/runtime.next`;
4. re-hashes every staged file against the manifest computed from the
   source, catching corruption;
5. atomically swaps `.eif/runtime.next` into `.eif/runtime` (the previous
   runtime is renamed aside first and only deleted once the swap succeeds -
   if the swap itself fails, the previous runtime is restored, never left
   half-written or missing);
6. only then writes `.eif/framework.lock.yaml`;
7. updates the `CLAUDE.md` managed block and the `.gitignore` managed block.

`scripts/tests/test_journey.py` exercises this against a deliberately broken
framework copy (a mandatory bundle file removed mid-sequence) and confirms
the instance's prior, working runtime survives the failed upgrade untouched
and remains fully functional - not just "no crash," but "still works."

## Compatibility

Intentionally simple and conservative for v0.1:

- `schema_version` in `.eif/config.yaml` (config shape) and
  `lock_schema_version` in `.eif/framework.lock.yaml` (lock shape) are
  independent - a breaking change to either must bump its own number.
- Both are validated against the schemas shipped in the *same* bundle that
  produced them (`core/schemas/eif-config.schema.json`,
  `core/schemas/framework-lock.schema.json`), so an instance is always
  checked against the framework version it is actually pinned to.

No automatic cross-version config migration exists yet - the first breaking
config-shape change is where that becomes necessary, not before.

## Adoption (existing repositories)

`--migration-status adopted` marks an instance created on top of a
pre-existing repository (recorded provenance, in the lock). Non-destructive
defaults make bootstrapping onto one safe:

- an existing `.eif/config.yaml` is **kept, unchanged** by default - this is
  now the *routine* upgrade path, not a special case; only explicit `--force`
  replaces it (backed up first);
- an existing `CLAUDE.md` keeps all its content - the EIF block is appended,
  or on re-run replaced in place, never clobbering project rules;
- an existing `.gitignore` keeps all its content, with the EIF block appended
  if not already present;
- `--dry-run` reports exactly what would change (create/keep/overwrite,
  per file) before anything is written.

**Adoption preflight and coexistence (adoption-hardening round).** Being
non-destructive is not the same as being non-*competing*: a marker-safe
append is still the wrong outcome if the appended block declares itself
the project's authority into a `CLAUDE.md` that already has its own real
governance. `scripts/eif_preflight.py` runs before any write and detects
this case - substantial pre-existing entrypoint content, no EIF markers
yet. On `init`, if that's detected and no `--adoption-mode` was passed,
`eif_init.py` refuses to write anything at all (`--dry-run` shows the
identical STOP a real run enforces - the two cannot drift, they call the
same function). Resolving it is an explicit decision, not a default:

- `--adoption-mode coexist` generates a block that says explicitly it is
  **not** the project's sole or primary authority, that project-owned
  instructions outside the `EIF:BEGIN`/`EIF:END` markers stay canonical,
  and that only paths actually named in `.eif/config.yaml` are referenced
  (see below) - it fills gaps, it does not compete.
- `--adoption-mode greenfield` is an explicit, informed override if you
  want the framework-authority framing anyway.

`adoption.mode` lives in `.eif/config.yaml` (user-owned), deliberately not
in `framework.lock.yaml` - it is a project decision about how EIF should
present itself, not EIF-managed provenance, and a routine upgrade
preserves it exactly like locale or adapter.

**Configurable knowledge paths.** `knowledge.root` and
`knowledge.index_path` in `.eif/config.yaml` control where
`eif_generate_index.py`/`eif_search_knowledge.py` look and where the
generated block's own example commands point - the greenfield default is
`knowledge`/`knowledge/index.md`, but an adopted repository with existing
knowledge at, say, `docs/knowledge/` does not have to migrate it to match
the default. If the configured root does not exist, index generation
stays inert - it is never created silently, so adoption never produces a
second, parallel knowledge system next to whatever the project already
has.

This is the property the eventual migration of the private production
instance depends on: bringing a real, populated repository under EIF
without discarding, or silently out-authoring, its existing configuration,
governance, or knowledge. Tested against a realistic sanitized fixture,
not a real repository, in `scripts/tests/test_adoption.py` - see
[claims-evidence.md](../product/claims-evidence.md) for exactly what that
proves and does not prove.

## Uninstalling / rollback

Not yet a dedicated command - `eif_init.py` has no `--rollback`/`--undo`
flag (only within-transaction rollback if a single run fails partway, see
above). To remove an EIF instance by hand:

1. Delete `.eif/` (config, lock, and the runtime bundle all live there).
2. Restore `CLAUDE.md` and `.gitignore` to their pre-EIF content. For a
   git-tracked file this was never committed with the EIF block, `git
   checkout -- CLAUDE.md .gitignore` is byte-exact by construction -
   prefer it over hand-editing, which is exact-whitespace-sensitive (a
   stray blank line at the removed block's former seam costs nothing
   functionally but does break a literal byte-for-byte claim). For an
   untracked file, or one where the EIF block was already committed,
   manually delete everything between and including the
   `<!-- EIF:BEGIN -->`/`<!-- EIF:END -->` (or `# EIF:BEGIN gitignore`/
   `# EIF:END gitignore`) markers, then verify with `git diff`/`git
   status`, not by eye.
3. **If a knowledge index was ever generated** (`eif_generate_index.py`,
   directly or via `eif_init.py`), delete the generated index file too -
   it lives at the configured `knowledge.index_path`, which may be
   outside `.eif/` (the common case for an adopted, not greenfield,
   repository) and is therefore NOT removed by step 1. A real gap this
   round's own adoption test caught: "delete `.eif/`, restore the two
   managed files" looked complete and was not - the generated index was
   left behind until the test's own byte-for-byte comparison against the
   pre-install snapshot caught it.
4. Verify: `git status`/`git diff` should show the tree back to its
   pre-EIF state exactly, not "looks about right."

## Validation surface

<!-- Added in the takeover review's round 2: the first version of this
document claimed "validate the whole instance" while the bundle only shipped
a subset of the framework's own validation scripts. This section is now
explicit about what runs from the instance and what doesn't. -->

What a project instance can run **from its own bundle**, with no framework
checkout:

| Check | Script (in `.eif/runtime/`) | What it validates |
|---|---|---|
| Knowledge frontmatter + schema-aware indexing | `eif_generate_index.py`, `eif_search_knowledge.py` | Distinguishes valid / schema-invalid / unparseable-YAML artifacts - see their own docstrings |
| Config schema | `eif_validate_frontmatter.py --config` | `.eif/config.yaml` against `eif-config.schema.json` |
| Lock schema | `eif_validate_frontmatter.py --lock` | `.eif/framework.lock.yaml` against `framework-lock.schema.json` |
| Privacy scan | `eif_privacy_scan.py` | Absolute-path leaks, secret-shaped strings, denylisted tokens across the instance's own git-tracked files - including finding-specific suppression validation |
| Relative link check | `eif_check_links.py` | Markdown relative links resolve within the instance |
| Localized rendering | `eif_render.py` | Not a validator, but writes real files - included here because "validate the instance" implies these files actually got generated, not just described |
| Self-verification ("doctor") | `eif_verify_runtime.py` | Config/lock schema validity, manifest digest self-consistency, per-file bundle hash verification, missing/unexpected-file detection, config/adapter/lock/entrypoint consistency, provenance notes, marker integrity, and drift between `.eif/config.yaml` and the generated entrypoint block or knowledge index |

What is **deliberately framework-maintainer-only**, not shipped in the
bundle:

| Not bundled | Why |
|---|---|
| `eif_init.py` | You always run the *framework's* copy to init/upgrade an instance - an instance never re-inits itself from inside |
| `eif_preflight.py` | `eif_init.py`'s own adoption-preflight helper - exclusively framework-side, same reasoning as `eif_init.py` itself |
| `eif_paths.py` | `eif_init.py`'s own path-policy helper (validates `knowledge.root`/`knowledge.index_path` at init/upgrade time) - exclusively framework-side, same reasoning |
| `eif_check_knowledge_delta.py` | Validates a *PR body* against this framework repository's own PR template - not applicable to a generic project instance's PR process |
| `eif_merge_pr.py` | This framework repository's own merge-gate script, not a generic tool |

An instance's own bundle validation surface is therefore: frontmatter/config/
lock schema validation, privacy scanning, link checking, localized
rendering, and self-verification. It is not a claim that the bundle
re-implements this framework repository's entire CI - PR-workflow-specific
tooling stays in the framework.

## What this is not

- Not a package manager or a ratified distribution model (D-08 open).
- Not a guarantee of forward/backward compatibility across arbitrary
  framework versions - only the conservative `schema_version`/
  `lock_schema_version` rule above.
- Not an automatic migrator - upgrade refreshes the bundle, lock, and managed
  blocks; anything more (config-shape migration, knowledge-schema migration,
  private-vocabulary remapping) is future work, named where it does not exist
  rather than implied.
- Not literally self-contained - the bundle is a pinned *source* copy; Python
  dependencies still need `pip install` once.
