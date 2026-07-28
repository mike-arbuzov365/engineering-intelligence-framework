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
Status: experimental. The package distribution model is ratified by
D-05/D-08; the instance lifecycle and compatibility boundary remain
experimental. -->

Status: **experimental**. Describes how a project instance records where it
came from and how it is upgraded. The installable-package distribution model
is ratified in D-05/D-08. D-17 defines the user-owned private project
registry and update workflow. D-18 defines the optional private workspace
scope inside L2.

## What a project instance is

A project instance is any repository initialized (or adopted) by
`scripts/eif_init.py`. It contains:

| Path | Owner | Committed? | Purpose |
|---|---|---|---|
| `.eif/config.yaml` | **you** (created once by eif_init, never overwritten without `--force`) | yes | Desired settings: project name, adapter choice, locale, governance, privacy, integrations |
| `.eif/framework.lock.yaml` | **EIF** (fully regenerated every init/upgrade) | yes | Exact provenance: framework commit, dirty flag, hashed bundle manifest, generated adapter entrypoint, timestamp |
| `.eif/runtime/` | **EIF** (fully regenerated every init/upgrade) | **no** (gitignored - see below) | Pinned *source* bundle of the scripts/schemas/ontology/locales/templates the instance's own commands run against. Still needs `pip install -r .eif/runtime/requirements.txt` - not a self-contained interpreter environment. |
| `.eif/workspace.lock.yaml` | **EIF workspace materializer** | yes, when connected | Separate private-workspace provenance: opaque workspace identity, revision, selected profile, overrides, exceptions, and artifact hashes. Contains no path or credential. |
| `.eif/workspace-runtime/` | **EIF workspace materializer** | **no** (gitignored) | Pinned, selected workspace artifacts. Agents consume this copy, never the live workspace checkout. Absent when no workspace is connected or after detach. |
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
  source_type: git               # git | installed-package | source-bundle - discriminates which of
                                  # the sibling git/package/source_bundle blocks below is populated;
                                  # never a fake stand-in for another kind (e.g. no synthetic git SHA
                                  # for an installed-package source)
git:                              # present only when source_type: git
  commit_sha: <full 40-char SHA>  # git rev-parse HEAD of --framework-root
  dirty: false                    # true if --framework-root had uncommitted changes
# package: {...}                  # present only when source_type: installed-package - see
                                  # core/schemas/framework-lock.schema.json
# source_bundle: {...}            # present only when source_type: source-bundle (an asserted,
                                  # non-git-verified --framework-ref) - same schema
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
default (git and source-bundle sources only - an installed package has no
working tree to be dirty) - if `--framework-root` has uncommitted changes,
the bundle would not actually match the recorded commit, so the tool stops
and asks for `--allow-dirty` (which proceeds and records `dirty: true`)
rather than silently claiming a false provenance guarantee. A routine
upgrade must also resolve to the same `framework.source_type` this instance
was already generated from. `eifctl upgrade --migrate-source` explicitly
permits the supported provenance migration from a git or source-bundle
instance to the installed package while preserving the user-owned config.
`--force` remains an intentional reconfiguration command, not the migration
path. Every bundled file is
sha256-hashed both from the source (building the manifest) and again after
staging (`verify_staged_bundle`), so a copy-time corruption is caught before
the bundle ever goes live.

## Private workspace, registry and fleet updates

The optional private workspace is an EIF project instance with additional
user-owned workspace configuration and content. It is durable scope inside
L2. It is not a second framework distribution and is deliberately excluded
from its own registry.

The workspace separates committed logical state from machine-local state:

| Path | Owner | Committed? | Purpose |
|---|---|---|---|
| `.eif/workspace.yaml` | user | yes, private | Workspace identity plus registry, profile, and content roots |
| `.eif/projects.yaml` | user | yes, private | Registry v2: stable project IDs, names, selected profiles, status, and declared exceptions, with no filesystem paths |
| `.eif/local-state/project-locations.yaml` | user/machine | no | Local path mapping keyed by stable project ID |
| `workspace/profiles/*.yaml` | user | yes, private | Required, default, optional, and explicitly overridden artifact selection |
| `planning/migration-ledger.md` | user | yes, private | Review record for changes that need project migrations |

The public schemas are
[`workspace-config.schema.json`](../../core/schemas/workspace-config.schema.json),
[`project-registry.schema.json`](../../core/schemas/project-registry.schema.json),
[`project-locations.schema.json`](../../core/schemas/project-locations.schema.json),
and
[`workspace-profile.schema.json`](../../core/schemas/workspace-profile.schema.json).
A named v1-to-v2 registry migration is dry-run-first and commits the logical
registry and locations file as one rollback unit.

Workspace materialization resolves the selected profile deterministically,
rejects undeclared collisions, stages the selected files, hashes each file
and the combined manifest, verifies the stage, and then transactionally
replaces `.eif/workspace-runtime/` and `.eif/workspace.lock.yaml`. Required
artifacts may be omitted only through a schema-validated, named exception.
Agents are instructed to read the pinned runtime, not the live workspace.

`eifctl projects upgrade` is plan-only by default. It compares two
independent provenance axes per active project:

1. the installed public EIF version against `.eif/framework.lock.yaml`;
2. the private workspace revision and profile against
   `.eif/workspace.lock.yaml`.

Before the first write it preflights every target, including dirty-tree
refusal, current framework-runtime verification, workspace resolution, and
workspace transaction staging. With `--apply`, it updates projects in order,
framework axis first and workspace axis second.

The fleet operation itself is not atomic across repositories. If a later
apply fails, earlier successful projects remain updated, the failed axis is
reported, and no later project is touched. Project commits remain separate
review and rollback units.

`eifctl projects detach` is also plan-only by default. Apply removes only
`.eif/workspace-runtime/` and `.eif/workspace.lock.yaml`. It preserves
project-owned content and keeps the logical entry as `detached` unless
registration removal is explicitly requested.

## Transactional init/upgrade

Nothing is replaced in place. `eif_init`:

1. resolves and validates provenance (dirty-check, mandatory-source check);
2. renders config and lock **in memory** and validates both against their
   schemas *before writing anything*;
3. **stages** every managed artifact to a `.next` path - config
   (`.eif/config.yaml.next`), the runtime bundle (`.eif/runtime.next`, then
   re-hashed against the manifest to catch corruption), the lock, the
   `CLAUDE.md` and `.gitignore` managed blocks, and (when
   `knowledge.managed`) the knowledge index;
4. **commits** them as one ordered sequence of atomic renames - each stage
   moves its prior live file aside to `.previous`, renames its `.next` into
   place, and on any failure rolls back every already-committed stage to its
   exact prior bytes.

Three failure windows are handled and separately tested (steps 16-37 of
`scripts/tests/test_journey.py`, with `EIF_INIT_TEST_FAIL_AFTER`,
`EIF_INIT_TEST_FAIL_BEFORE`, and `EIF_INIT_TEST_FAIL_PARTIAL` fault
injection at each stage - the last also covers the `--force` config backup
and a nonexistent instance path):

- **After a commit** - `commit_transaction` rolls back every committed
  stage and removes its own uncommitted `.next` files.
- **Before a stage's write** (a fault while staging, before that stage has
  written anything) - the whole staging phase is wrapped so every `.next` is
  removed and the tree returns to its exact prior state; nothing already live
  is touched.
- **Partway through a stage's write/copy** (a mid-copy crash that leaves a
  genuinely PARTIAL `.next` on disk) - each `.next` path is registered for
  cleanup *before* the first byte is written to it, and the runtime bundle
  additionally self-cleans a partial `runtime.next`. The `--force` config
  backup is written the same way (its collision-safe destination is
  registered for cleanup before the copy starts, and the copy self-cleans a
  partial `.bak-*`), so a half-written artifact - including a half-written
  backup - is always removed too, never orphaned. This is the strongest of
  the three claims and is proven against a real partial artifact on disk, not
  just a stage that never started.

In all three windows the outcome is byte-for-byte tree equality: no `.next`/
`.previous` files, no orphaned new directories (a first-ever init removes its
own freshly-created `.eif/` if the run fails; and a **nonexistent
`--instance-path` is supported** - the run records which directories it
creates and, on failure, removes exactly those, deepest-first and only if
empty, never a directory that pre-existed the run), no partial runtime
directory, and no leftover config backup (see below). A successful init
leaves the instance directory it created in place. The instance's prior,
working runtime survives a failed upgrade untouched and remains fully
functional - not just "no crash," but "still works."

### Config-backup policy

A `--force` reconfigure backs up the existing `.eif/config.yaml` to
`.eif/config.yaml.bak-<timestamp>` before overwriting it. The timestamp is
microsecond-resolution with a collision loop, so two reconfigures within the
same second still produce distinct backups and an existing recovery backup is
never overwritten. The backup destination is registered for cleanup before
the copy starts and the copy self-cleans a partial `.bak-*`, so a crash
mid-backup leaves no orphaned partial. The backup is a transient artifact
until the reconfigure commits:

- **Failed reconfigure** -> the backup is deleted, so the tree returns
  byte-for-byte to its prior state (the "no orphaned files / exact prior
  tree" guarantee above holds without exception).
- **Successful reconfigure** -> the backup is kept, as the recovery copy of
  the config that was just replaced.

### Concurrency (single writer)

**Concurrent `eif_init` writers against the same instance are not supported.**
The transactional and backup-collision guarantees above assume a **single
writer**: the `.next` staging paths, the runtime staging directory, and the
`.bak-<timestamp>` collision loop are safe against a mid-run crash of one
process, but not against two `eif_init` processes racing on the same instance
at the same time (two runs could interleave their staging/commit and defeat
the exact-prior-tree guarantee). Run one `eif_init` at a time per instance.

This is a stated, non-blocking limitation, not a fix. A future hardening
(backlog, not implemented here) would add an instance lock file, an atomic
exclusive backup creation, and stale-lock recovery. It is deliberately not
implemented as part of the merge-enforcement work, which does not need it.

### Repository origin

The *historical* `migration_status` is derived from a dedicated, read-only
**repository-origin** check (`eif_init.detect_repository_origin`), run before
any write. It is deliberately a **separate mechanism** from the
governance/entrypoint preflight, which answers a different question ("is
there pre-existing *governance* - a substantial `CLAUDE.md` - to coexist
with?"). An existing code repository with a README, a package manifest, or a
`src/` tree but no `CLAUDE.md` has no governance yet, but is still,
historically, an **adopted** repository - never greenfield. Keying
`migration_status` off the entrypoint file alone recorded such a repo as
`greenfield`, which is simply false about how it came to exist; the two
signals are kept apart.

The origin check classifies the instance directory as one of:

- **empty** - no project-owned entry outside `.git/` and `.eif/` (a
  genuinely empty directory, a not-yet-created one, or one holding only
  version-control / EIF metadata) -> `greenfield` history.
- **pre_existing** - at least one project-owned file or directory outside
  `.git/` and `.eif/` -> `adopted` history.
- **unknown** - the directory could not be read (permissions / I/O). The tool
  **fails closed**: it requires an explicit `--migration-status` and never
  silently guesses `greenfield`.

`.git/` (version-control metadata) and `.eif/` (EIF's own namespace) are
ignored. A **stray or in-progress `.eif/`** left by a failed first init is
therefore *not* evidence the repository pre-existed EIF; only genuine
project-owned content is. On an upgrade/reconfigure the recorded history is
preserved verbatim, so EIF's own generated files can never re-flip a repo's
origin.

### Migration provenance

`.eif/config.yaml`'s `adoption.mode` (the *current* coexistence behavior)
and `.eif/framework.lock.yaml`'s `instance.migration_status` (the
*historical* origin, from the repository-origin check above) answer different
questions but must not contradict the evidence. `migration_status` is
**derived**, not defaulted:

- a `pre_existing` repository, or `adoption.mode: coexist` ->
  `migration_status: adopted`;
- a greenfield **authority** override on a pre-existing repo still records
  `adopted` (an override changes who the block claims authority for; it does
  not rewrite how the repository came to be) - so `adoption.mode: greenfield`
  with `migration_status: adopted` is a valid, expected pairing for an
  existing repo that had no prior agent governance;
- a genuinely `empty`-origin new repo -> `greenfield`;
- an explicit `--adoption-mode coexist --migration-status greenfield`, or an
  explicit `--migration-status greenfield` over a `pre_existing` repo, STOPs
  before any write;
- an `unknown` (unreadable) origin without an explicit `--migration-status`
  STOPs - fail closed, never guessed as greenfield;
- a routine upgrade preserves the persisted status; a reconfigure honors an
  explicit `--migration-status` and otherwise preserves it, and refuses to
  switch to `coexist` over a recorded `greenfield` without an explicit
  `--migration-status adopted` (never silently rewriting history).

`eif_verify_runtime.py` FAILs on the one impossible pairing (`coexist` +
`greenfield`) with a concrete `--force` repair instruction, and never on a
greenfield authority mode over an adopted history (that is the documented
override case above).

## Compatibility

Intentionally simple and conservative for v0.1:

- `schema_version` in `.eif/config.yaml` (config shape) and
  `lock_schema_version` in `.eif/framework.lock.yaml` (lock shape) are
  independent - a breaking change to either must bump its own number.
- Both are validated against the schemas shipped in the *same* bundle that
  produced them (`core/schemas/eif-config.schema.json`,
  `core/schemas/framework-lock.schema.json`), so an instance is always
  checked against the framework version it is actually pinned to.

No automatic cross-version project-config migration exists yet. The v0.1.1
through v0.1.3 project config and framework lock remain compatible with
v0.2.0. Registry v1 has a named v1-to-v2 migration. Future breaking config,
profile, workspace-lock, or knowledge-schema changes must ship a named,
tested migration before the fleet update path can apply them.

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

- Not a package index client. Installation or update of the `eifctl` wheel
  happens before an instance update.
- Not a guarantee of forward/backward compatibility across arbitrary
  framework versions - only the conservative `schema_version`/
  `lock_schema_version` rule above.
- Not a general automatic migrator. The explicit source-provenance migration
  does not migrate a future breaking config shape, knowledge schema or
  private vocabulary.
- Not literally self-contained - the bundle is a pinned *source* copy; Python
  dependencies still need `pip install` once.
