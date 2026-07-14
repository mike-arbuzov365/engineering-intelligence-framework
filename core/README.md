# core/

Framework-level, project-agnostic definitions. Nothing here should reference
a specific project, customer, or private repository.

- `ontology/` - shared vocabulary: authority model, knowledge-artifact
  taxonomy, confidence levels, status lifecycle.
- `policies/` - non-negotiable rules (safety, scope, git/PR discipline)
  that apply regardless of project instance, plus the public
  [decision ledger](policies/decisions.md) (which brand/license/structure
  decisions are ratified vs. provisional vs. open).
- `schemas/` - machine-readable JSON Schemas
  ([`knowledge-frontmatter.schema.json`](schemas/knowledge-frontmatter.schema.json),
  [`eif-config.schema.json`](schemas/eif-config.schema.json)) that mirror
  the prose in `ontology/` and `.eif/config.yaml.example`. Nothing
  currently validates against them automatically - see
  [`scripts/README.md`](../scripts/README.md).
