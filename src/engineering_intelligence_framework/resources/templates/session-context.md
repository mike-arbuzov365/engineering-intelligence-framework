# Session context checkpoint template

Use this template only for a logical session that must survive a physical-chat
transition, manual compaction, or another planned interruption. Light tasks do
not need a checkpoint by default.

The generated checkpoint lives at
`.session-context/<logical-session-id>.md`, is machine-local and gitignored,
and validates against
`core/schemas/session-context.schema.json`. The YAML frontmatter is the
canonical state; prose below it is navigation only.

```yaml
---
schema_version: 1
artifact_type: session_context
status: in_progress
updated_at: "<RFC3339 timestamp>"
project:
  id: <stable-project-id>
  name: <project-name>
  root: <absolute-local-project-root>
  config_path: .eif/config.yaml
  config_sha256: <sha256>
  lock_path: .eif/framework.lock.yaml
  lock_sha256: <sha256>
  adapter: <adapter>
source_artifact:
  path: <project-relative-source-artifact>
  sha256: <sha256>
logical_session:
  id: <logical-session-id>
  continuation_mode: same_chat | new_chat | auto
  adapter: <adapter>
goal: <current-goal>
scope:
  in_scope:
    - <bounded-item>
  no_touch:
    - <explicit-boundary>
approvals:
  state: approved | pending | not_required
  evidence: []
decisions: []
progress:
  completed: []
  changed_artifacts: []
verification:
  status: not_run
  checks: []
blockers: []
failed_approaches: []
unresolved_risks: []
next_action: <one-exact-action>
git:
  repository: true
  root: <absolute-git-root>
  branch: <branch-or-null>
  head: <forty-hex-commit-or-null>
  status_fingerprint: <sha256>
  changed_files: []
physical_chats: []
---
```

Create or refresh this file with `eifctl session checkpoint`; do not manually
invent hashes or Git observations. Validate it with `eifctl session validate`
and run `eifctl session resume-audit` before resuming or handing off.
