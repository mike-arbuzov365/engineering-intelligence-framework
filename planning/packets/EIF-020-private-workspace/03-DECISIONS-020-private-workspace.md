---
packet: EIF-020-private-workspace
type: decisions
status: ratified
created: 2026-07-28
---

# Decisions: EIF 0.2.0 private workspace scope

## D-001: Keep three layers

**Status: ratified.** The private workspace is an optional durable scope
inside L2. It is not L2.5, L4 or a second framework layer. Public diagrams
keep L1 framework, L2 project/workspace and L3 session.

**Evidence:** The current architecture already defines L2 as one project
or a set of related projects. Adding a top-level layer would make the
public model harder to explain without creating a new kind of context.

## D-002: Public EIF remains the only framework distribution

**Status: ratified.** A private workspace repository references a released
EIF package and is itself an EIF project instance. It never copies or
forks the public framework as its update mechanism.

**Evidence:** D-05/D-08 and D-17 already separate the package from
independent project instances. A fork would recreate the divergence this
feature is intended to remove.

## D-003: Creation is explicit and local

**Status: ratified.** `pip install` remains side-effect free.
`eifctl workspace new <path>` creates a local private-workspace repository,
and `eifctl workspace doctor` verifies the workspace itself. Existing
`eifctl projects` commands evolve to connect, inspect, update and detach
projects instead of duplicating those operations under a second command
group. No workspace publication command is part of 0.2.0. Creation does not
create a remote, choose visibility, push or publish.

**Evidence:** `workspace` matches the architecture term and avoids
overloading EIF's general "control plane" descriptor. Project registry
operations already exist under `eifctl projects`; duplicating
`connect/status/apply` would add two public routes to the same state. Remote
publication is supported by existing Git host tooling, adds an external
trust boundary, and is not needed to prove the workspace slice.

## D-004: Separate logical registry from machine locations

**Status: ratified.** Committed `.eif/projects.yaml` stores stable project
IDs, display names, selected profiles and lifecycle status. Gitignored
`.eif/local-state/project-locations.yaml` maps those IDs to paths for one
machine. Registry schema v1 receives a named, non-destructive v2 migration.

**Evidence:** Committed local paths conflict across machines and can expose
filesystem structure. Keeping paths only in local state preserves a shared
private fleet definition without pretending paths are portable.

## D-005: Keep framework and workspace provenance independent

**Status: ratified.** Projects retain `.eif/framework.lock.yaml` for the
public release and add `.eif/workspace.lock.yaml` for an optional private
workspace snapshot. Neither lock embeds a secret, local path or credential.

**Evidence:** Framework version and private workspace commit change on
independent schedules. A merged lock would make one update appear to
re-produce the other.

## D-006: Materialize pinned snapshots

**Status: ratified.** A project uses a deterministic, hashed snapshot under
gitignored `.eif/workspace-runtime/`. It never reads live from a workspace
working tree and does not use a Git submodule. Staging, hash verification
and replacement follow the existing instance transaction pattern.

**Evidence:** The current hashed runtime contract already solves partial
copy and drift risks for the public framework. Reusing it is smaller and
safer than inventing a second orchestration engine.

## D-007: Policies declare enforcement mode

**Status: ratified.** Workspace policies are classified as:

- `required`: an owner-ratified safeguard, overridable only by an explicit
  approved exception;
- `default`: active unless project scope supplies a declared replacement;
- `optional`: included only by the selected profile or explicit project
  selection.

**Evidence:** A single "local always wins" rule would let project files
silently weaken safeguards. A single "workspace always wins" rule would
erase valid project specialization.

## D-008: Same-name overrides are explicit

**Status: ratified.** Project-owned artifacts may specialize workspace or
framework artifacts only through a schema-valid `override_of` declaration,
reason and approval reference. Undeclared same-name collisions fail
verification. Public schemas, privacy boundaries and migration contracts
cannot be overridden by workspace content.

**Evidence:** Agent instructions are executable in effect. Silent shadowing
would make the loaded behavior non-reviewable and could lower safeguards.

## D-009: Profiles are user-owned data

**Status: ratified.** EIF ships a profile schema and a minimal default
example, not product-specific or communications-specific profiles. A
private workspace defines its own named profiles and tests their resolved
bundles before connecting projects.

**Evidence:** Baking private workflow categories into the public package
would turn one user's fleet into public methodology and would not scale to
other adopters.

## D-010: Fleet apply is preflighted, sequential and honest

**Status: ratified.** A plan compares both target EIF version and target
workspace snapshot. Apply preflights every selected target before the
first write, then updates one project at a time with a per-project
transaction. It stops on first failure and reports the completed set.
Fleet-wide atomicity is not claimed.

**Evidence:** This extends the already ratified D-17 behavior instead of
adding a distributed transaction or unsafe rollback across repositories.

## D-011: The workspace does not register itself

**Status: ratified.** The private workspace repository is initialized as an
EIF project instance for its own governed development, but it is excluded
from its own project registry.

**Evidence:** Self-registration would create recursive status, update and
detach semantics with no user value.

## D-012: Legacy migration classifies before copying

**Status: ratified.** A migration ledger assigns each legacy artifact to
one of: already public, private workspace, project-local, archive, or
reject as obsolete. No directory is copied wholesale. The source remains
read-only until accepted targets are verified.

**Evidence:** The public clean-room extraction and current private
instances have different ownership and privacy boundaries. Bulk copying
would reintroduce duplication and stale authority.

## D-013: Detach preserves project ownership

**Status: ratified.** Detach removes only workspace-managed runtime,
workspace lock and managed instruction blocks. It removes the logical
registry entry only when explicitly requested. It never deletes
project-owned knowledge, rules, skills, history or product files.

**Evidence:** D-17 makes connected projects independent. A workspace
connection cannot become ownership of their durable content.

## D-014: Community skill review stays read-only and later

**Status: ratified.** A future curator may periodically research community
skills, compare them with the local catalog, and propose provenance-rich
improvements. It may not automatically install, execute, promote or trust
third-party content. It is not part of the 0.2.0 vertical slice.

**Evidence:** Automated discovery is adjacent to, but not necessary for,
safe workspace propagation. Combining them would expand the trust boundary
and delay the first usable slice.

## D-015: Minimum sufficient architecture

**Status: ratified.** Extend the current package, registry and transaction
primitives. Do not add a database, daemon, dashboard, GitHub App,
submodule, private package index or new orchestration service.

**Evidence:** The Ponytail ladder recommends reusing codebase and platform
mechanisms before adding dependencies, while explicitly retaining
validation, security and data-loss protection. Existing EIF primitives
already cover most required mechanics.

## D-016: Public name and user-owned repository name are separate

**Status: ratified.** Public documentation calls the feature "private
workspace scope" and the repository a "private workspace repository" or
"workspace control repository". The user may name the actual repository
freely. A repository name is not an architectural layer.

**Evidence:** Stable conceptual terminology should not depend on one
user's repository naming convention.

## D-017: Breaking shapes require named migrations

**Status: ratified.** A breaking workspace config, registry, profile or lock
shape must bump its own schema version and ship a named, tested migration
before fleet apply accepts it.

**Evidence:** The current instance contract explicitly forbids assuming
automatic compatibility across breaking shapes.

## D-018: Site presentation stays simple

**Status: ratified.** The site keeps "The three layers". Once the vertical
slice is available, L2 copy may say that one private workspace can share
selected operating artifacts across several independent projects. It must
not draw a new ring or imply automatic promotion.

**Evidence:** Workspace is a scope and distribution boundary inside L2,
not a new kind of context.

## Open (not yet decided)

*(none required for this packet)*

## Least-risk defaults

- Prefer a dry-run or plan over a write.
- Prefer existing transaction helpers over parallel implementations.
- Refuse dirty or unverifiable sources unless a narrowly named diagnostic
  override already exists and records reduced assurance.
- Keep user-owned files unchanged unless the command explicitly names and
  previews the managed block.
- If a feature is not required by the charter, defer it rather than
  scaffold it.
- If a real private target is needed, stop the public packet and create a
  private follow-on packet instead of adding its identity here.
