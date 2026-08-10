# Контрольна точка сесії: {session_id}

YAML frontmatter є canonical continuation state для цієї логічної сесії.
Цей текстовий блок використовується лише для навігації.

Перед продовженням або handoff виконайте валідацію:

```text
eifctl session validate .session-context/{session_id}.md
eifctl session resume-audit .session-context/{session_id}.md
```
