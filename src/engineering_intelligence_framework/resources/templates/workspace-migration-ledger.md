# Private workspace migration ledger

Use this ledger before moving any artifact from an older private operating
repository. Classify first. Do not copy a directory wholesale.

| Source artifact | Classification | Target | Evidence and owner decision | Status |
|---|---|---|---|---|
| `<path or identifier>` | `already-public`, `private-workspace`, `project-local`, `archive`, or `reject-obsolete` | `<reviewed target or none>` | `<why this boundary is correct>` | `proposed` |

## Acceptance rules

- `already-public`: the canonical public EIF release already supplies it.
- `private-workspace`: reusable across this user's projects, but not public
  framework methodology.
- `project-local`: belongs to one project's product, customer or domain
  context.
- `archive`: retained for history but not loaded as current authority.
- `reject-obsolete`: intentionally not migrated, with the reason recorded.

Only an explicitly accepted row may be copied to its target. Verify the
accepted target before changing or removing the source.
