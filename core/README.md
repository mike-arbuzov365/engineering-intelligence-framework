# core/

Framework-level, project-agnostic definitions. Nothing here should reference
a specific project, customer, or private repository.

- `ontology/` - shared vocabulary: authority model, knowledge-artifact
  taxonomy, confidence levels, status lifecycle.
- `policies/` - non-negotiable rules (safety, scope, git/PR discipline)
  that apply regardless of project instance.
- `schemas/` - machine-readable schemas (frontmatter, `.eif/config.yaml`,
  Knowledge Delta) that tooling and CI validate against.

`schemas/` is not populated yet - see
[`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#roadmap).
