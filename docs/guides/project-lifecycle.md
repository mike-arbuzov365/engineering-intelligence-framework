---
type: playbook
status: validated
scope: framework
created: 2026-07-28
review_after: 2026-10-28
---

# Project lifecycle

This guide describes the v0.2.0 path from installing EIF to safely
coordinating one or more private project repositories.

## The ownership model

There is one public EIF distribution, an optional private workspace, and any
number of private project instances:

```text
GitHub Release wheel
  -> installed eifctl package
  -> private workspace (optional L2 scope)
       -> committed logical registry and workspace profiles
       -> ignored machine-local project locations
       -> project A (framework lock + workspace lock)
       -> project B (framework lock + workspace lock)
```

Do not copy the public EIF repository into a private framework fork just to
connect projects. The installed release package is the framework source. The
workspace is itself an EIF project instance and adds user-owned rules, skills,
templates, playbooks, and profiles inside L2. It is not another framework
distribution and does not create a fourth intelligence layer.

Each project keeps its own settings and durable knowledge. The workspace
commits `.eif/projects.yaml`, which stores stable logical identities and
profile selection but no filesystem paths. Local paths live in the ignored
`.eif/local-state/project-locations.yaml`. Neither file is sent to the public
EIF repository, and the workspace repository should remain private when its
content or inventory is private.

## Install a released package

EIF is not published to PyPI. Open
[GitHub Releases](https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases),
download the `.whl` file attached to the release, then install the local
file:

```bash
python -m pip install ./engineering_intelligence_framework-0.2.0-py3-none-any.whl
eifctl version
```

The checked-out source can also be installed directly:

```bash
python -m pip install .
```

`pip install engineering-intelligence-framework` is not a supported command
until a release is actually published to PyPI.

## Create a private workspace

Create the workspace locally:

```bash
eifctl workspace new ../eif-control \
  --workspace-name eif-control \
  --adapter codex \
  --locale uk

eifctl workspace doctor --workspace-path ../eif-control
```

The command initializes a local git repository and a base EIF project
instance, then adds the minimal workspace configuration, empty registry,
default profile, ignored local-state directory, and migration ledger. It
does not create a remote, choose visibility, push, publish, or register the
workspace as one of its own projects.

Review and commit the bootstrap in a private repository before connecting
projects. Keep the generated default profile minimal until a real project
proves that a shared artifact is needed.

## Create and connect a new project

From a directory whose parent already exists:

```bash
eifctl new ../my-project \
  --project-name my-project \
  --adapter codex \
  --locale uk \
  --registry ../eif-control/.eif/projects.yaml
```

`eifctl new` builds the project in a temporary sibling directory, initializes
EIF, runs `git init -b main`, moves the completed tree into place, and only
then updates the registry. It refuses an existing target.

This command creates a local git repository. It does not create a GitHub
repository, choose public or private visibility, or push a remote. Those are
separate owner decisions.

## Connect an existing project

Initialize or adopt the repository first:

```bash
eifctl init ../existing-project --adapter codex --locale uk
eifctl doctor --instance-path ../existing-project
eifctl projects add ../existing-project \
  --registry ../eif-control/.eif/projects.yaml
```

Registration requires a valid `.eif/config.yaml` and
`.eif/framework.lock.yaml`. It does not modify project files.

Registry v2 stores the logical entry in `.eif/projects.yaml` and writes the
local path only to `.eif/local-state/project-locations.yaml`. Re-adding a
detached project at the same path explicitly reactivates it.

## Update one project

Install the new release wheel into the environment that provides `eifctl`.
Then plan the update:

```bash
eifctl upgrade --instance-path ../my-project --dry-run
```

If the plan succeeds, apply it:

```bash
eifctl upgrade --instance-path ../my-project
```

The command refuses an uncommitted project by default. It verifies the
currently pinned runtime when present, transactionally refreshes EIF-managed
files from the installed package, and runs `doctor` afterward.

A routine update preserves `.eif/config.yaml` byte for byte. It also
preserves project source, knowledge artifacts, and content outside managed
entrypoint and `.gitignore` markers.

## Keep the two update axes separate

Every connected project records two independent sources:

- `.eif/framework.lock.yaml` pins the public EIF package and its managed
  framework runtime.
- `.eif/workspace.lock.yaml` pins one private workspace revision, selected
  profile, overrides, and the hashes of materialized workspace artifacts.

Updating the public package does not silently rewrite workspace content.
Changing workspace rules does not change the public framework package.
`projects upgrade` coordinates both transactions for convenience, but
reports and verifies them as separate axes.

Upgrade the workspace repository itself first because it is deliberately
excluded from its own registry:

```bash
eifctl upgrade --instance-path ../eif-control --dry-run
eifctl upgrade --instance-path ../eif-control
```

Review and commit that change. Then update workspace profiles or artifacts,
review them as normal private-repository changes, and record any required
project migration in `planning/migration-ledger.md`.

## Plan and update every connected project

Inspect the registry first:

```bash
eifctl projects status --registry ../eif-control/.eif/projects.yaml
```

Plan all updates without writing:

```bash
eifctl projects upgrade --registry ../eif-control/.eif/projects.yaml
```

Apply only after every registered project passes preflight:

```bash
eifctl projects upgrade \
  --registry ../eif-control/.eif/projects.yaml \
  --apply
```

The plan compares the current and target framework version separately from
the current and target workspace revision, profile, override set, and
materialization health. It writes nothing.

The apply command checks every active project before the first write. It
then updates one project at a time, framework axis first and workspace axis
second. A multi-repository update is not one atomic transaction. If a later
apply fails, earlier successful projects stay updated, the failed axis is
named, and later projects remain untouched.

For a private dogfood gate, keep only one controlled project active first.
Review and commit its generated framework and workspace locks, runtime
selection, entrypoint changes, and project tests. Expand to the rest of the
fleet only after that project passes. EIF does not treat a successful
materialization as proof that project behavior is correct.

## Detach a project from the workspace

Preview the operation:

```bash
eifctl projects detach my-project \
  --registry ../eif-control/.eif/projects.yaml
```

Apply it:

```bash
eifctl projects detach my-project \
  --registry ../eif-control/.eif/projects.yaml \
  --apply
```

Detach removes only `.eif/workspace-runtime/` and
`.eif/workspace.lock.yaml`. Project source, knowledge, local rules, skills,
history, framework runtime, and configuration remain untouched. The logical
entry stays in the registry as `detached`; add `--remove-registration` only
when the inventory entry and local mapping should also be removed.

## Migrate a registry from v1

The v0.2.0 registry separates logical state from machine paths. Plan the
named migration first:

```bash
eifctl projects migrate-registry-v1-to-v2 \
  --registry ../eif-control/.eif/projects.yaml
```

After reviewing the two-file plan, apply it:

```bash
eifctl projects migrate-registry-v1-to-v2 \
  --registry ../eif-control/.eif/projects.yaml \
  --apply
```

The migration preserves stable project identity, writes paths only to the
ignored locations file, and rolls both files back if either write fails.

## Migrate an older git-sourced instance

An instance created directly from an EIF checkout records `source_type:
git`. Moving it to the released-package model changes provenance, so the
change must be explicit:

```bash
eifctl upgrade \
  --instance-path ../existing-project \
  --dry-run \
  --migrate-source

eifctl upgrade \
  --instance-path ../existing-project \
  --migrate-source
```

For a registry:

```bash
eifctl projects upgrade \
  --registry ../eif-control/.eif/projects.yaml \
  --migrate-source

eifctl projects upgrade \
  --registry ../eif-control/.eif/projects.yaml \
  --migrate-source \
  --apply
```

This source-only migration preserves the user config. `--force` is reserved
for an intentional reconfiguration and is not required for this migration.

## Before committing an update

Review the diff, then run:

```bash
eifctl doctor --instance-path ../my-project
git -C ../my-project diff
```

Commit the lock and managed-file changes in each project only after they are
reviewed. The regenerable `.eif/runtime/` remains ignored.

## Current compatibility boundary

The v0.1.1 through v0.1.3 project config and framework lock remain compatible
with v0.2.0. Registry v1 has the named migration above. No automatic
migration is claimed for a future breaking project-config, workspace-profile,
knowledge-schema, or private-vocabulary change. A release that bumps one of
those contracts must ship and test a named migration before users apply it
through this path.
