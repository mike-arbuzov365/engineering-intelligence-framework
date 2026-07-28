---
type: playbook
status: validated
scope: framework
created: 2026-07-28
review_after: 2026-10-28
---

# Project lifecycle

This guide describes the v0.1.1 path from installing EIF to safely updating
one or more private project repositories.

## The ownership model

There is one public EIF distribution and any number of private project
instances:

```text
GitHub Release wheel
  -> installed eifctl package
  -> private project registry
       -> project A (.eif/config.yaml + pinned runtime)
       -> project B (.eif/config.yaml + pinned runtime)
```

Do not copy the public EIF repository into a private framework fork just to
connect projects. The installed release package is the framework source.
Each project keeps its own user settings and durable knowledge. A private
control repository may keep `.eif/projects.yaml`, which only records the
names and local paths of connected projects.

The registry is not sent to the public EIF repository. Commit it only to a
private repository because its paths reveal the user's local project
inventory.

## Install a released package

EIF is not published to PyPI. Open
[GitHub Releases](https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases),
download the `.whl` file attached to the release, then install the local
file:

```bash
python -m pip install ./engineering_intelligence_framework-0.1.1-py3-none-any.whl
eifctl version
```

Installing from a checked-out release is also supported:

```bash
python -m pip install .
```

`pip install engineering-intelligence-framework` is not a supported command
until a release is actually published to PyPI.

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

## Update every connected project

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

The apply command checks every project before the first write. It then
updates projects one at a time and stops at the first apply failure. A
multi-repository update is not one atomic transaction, so earlier successful
projects stay updated if a later project fails.

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

v0.1.1 updates instances whose config and lock schemas remain compatible.
It does not provide an automatic migration for a future breaking config,
knowledge-schema, or private-vocabulary change. A future release that bumps
one of those schemas must ship and test a named migration before users can
apply it through this path.
