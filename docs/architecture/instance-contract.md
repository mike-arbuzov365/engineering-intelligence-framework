# Instance contract, provenance and upgrade model

<!-- Knowledge source: takeover architecture review 2026-07-15. This is the
minimum viable contract between the framework and a project instance,
introduced because the earlier bootstrap generated a placeholder framework
ref and had no upgrade or adoption story - both blockers for the eventual,
safe migration of an existing repository onto EIF. Status: experimental. It
does not ratify D-08 (dependency/distribution model). -->

Status: **experimental**. This describes how a project instance records where
it came from and how it is upgraded. It is deliberately small and reversible;
it does not ratify the final distribution model (D-08 in
[`../../core/policies/decisions.md`](../../core/policies/decisions.md) remains
open).

## What a project instance is

A project instance is any repository that has been initialized (or adopted)
by `scripts/eif_init.py`. It contains:

| Path | Managed by | Committed? | Purpose |
|---|---|---|---|
| `.eif/config.yaml` | eif_init (created once) | yes | Instance identity, provenance, locale, governance |
| `.eif/runtime/` | eif_init (regenerated) | **no** (gitignored) | Pinned, self-contained copy of the framework scripts/schemas/ontology/locales/templates the instance's own commands run against |
| `CLAUDE.md` (EIF-managed block) | eif_init (block only) | yes | Agent entrypoint; the block between the `EIF:BEGIN`/`EIF:END` markers is regenerated on upgrade, everything else is project-owned |
| `knowledge/` | the project | yes | The instance's own knowledge artifacts |

The instance does **not** need the framework itself checked out to run its own
commands - `.eif/runtime/` is self-contained. That is the whole point of the
bundle: a separate repository can retrieve knowledge, validate, and render
localized output with `python .eif/runtime/...`, offline, with no framework on
the path.

## Provenance

`.eif/config.yaml` records the real framework commit the instance was
generated from:

```yaml
framework:
  version: 0.1.0-dev
  ref: <full 40-char git SHA>     # resolved by eif_init via `git rev-parse HEAD`
  ref_short: <short SHA>
  bundle: .eif/runtime
```

This is a real, immutable reference - never a placeholder branch name. It
answers "which framework produced this instance?" precisely, which is what
makes upgrades and audits possible.

## Upgrade

Upgrading an instance to a newer framework is a re-run, not a manual rebuild:

```
python <newer-framework>/scripts/eif_init.py \
    --framework-root <newer-framework> \
    --instance-path <this-instance> \
    --project-name <name> --locale <locale> --force
```

- `.eif/runtime/` is fully refreshed to the new framework's code.
- `.eif/config.yaml` `framework.ref` advances to the new commit (the old one
  is backed up first because of `--force`).
- The `CLAUDE.md` EIF-managed block is regenerated; **project-authored content
  outside the markers is untouched**.
- `knowledge/` is never modified by upgrade.

Because the instance's own knowledge lives in `knowledge/` (project-owned) and
never inside the managed bundle, an upgrade cannot lose instance knowledge.
That property is what makes the later migration of a real, knowledge-heavy
repository safe.

## Compatibility

For v0.1 the compatibility rule is intentionally simple and conservative:

- `schema_version` in `.eif/config.yaml` is the config shape version. A newer
  framework that changes the config shape in a breaking way must bump it and
  provide a migration note. Until then, `schema_version: 1`.
- The framework validates a config against the schema shipped in that same
  framework bundle (`.eif/runtime/core/schemas/eif-config.schema.json`), so an
  instance is always validated against the framework version it is pinned to,
  not a drifting global.

No automatic cross-version config migration exists yet. When a breaking config
change first lands, a `schema_version`-aware migration step is the first thing
to add - it is deliberately out of scope for v0.1.

## Adoption (existing repositories)

`--migration-status adopted` marks an instance created on top of a
pre-existing repository (as opposed to `greenfield`). eif_init's
non-destructive defaults make adoption safe:

- an existing `.eif/config.yaml` is never overwritten without `--force` (which
  backs it up first);
- an existing `CLAUDE.md` keeps all its content - the EIF block is appended (or,
  on re-run, its managed block replaced in place), never clobbering project
  rules;
- `--dry-run` reports exactly what would change before anything is written.

This is the property the eventual migration of the private production instance
depends on: it must be possible to bring a real, populated repository under EIF
without discarding its existing configuration, instructions, or knowledge.

## What this is not

- Not a package manager or a ratified distribution model (D-08 open).
- Not a guarantee of forward/backward compatibility across arbitrary framework
  versions - only the conservative `schema_version` rule above.
- Not an automatic migrator - upgrades refresh the bundle and managed block;
  anything more (config-shape migration, knowledge schema migration) is future
  work, called out where it does not exist rather than implied.
