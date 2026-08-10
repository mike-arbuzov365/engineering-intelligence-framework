# Session checkpoint: {session_id}

The YAML frontmatter is the canonical continuation state for this logical
session. This human-readable body is navigation only.

Validate before resuming or handing off:

```text
eifctl session validate .session-context/{session_id}.md
eifctl session resume-audit .session-context/{session_id}.md
```
