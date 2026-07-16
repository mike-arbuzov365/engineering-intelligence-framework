# Manual runtime-consumption check (Cursor)

**Status: manual gate pending.** Everything else about this adapter is
code/test-validated (`scripts/tests/test_cursor_adapter.py`, 74/74) and, as
of 2026-07-16, partially confirmed by launching the real installed Cursor
(3.11.19) against a synthetic project - Cursor opens it and its file
Explorer correctly shows the generated files. **Not yet confirmed:**
whether Cursor's Agent chat actually includes the generated rule's content
in a response. Computer-use access to IDE/terminal applications is
click-tier only (no typing, and window content is not reliably visible in
screenshots), so this specific step needs a human at the keyboard - it
cannot be completed from an agent session. Do not describe this adapter as
"runtime validated" until this step is performed and its result is recorded
below.

## Why this specific probe

The check must be **deterministic and unguessable**: the expected answer
has to include something a model could not plausibly produce without
actually having the generated rule loaded in context - not a lucky guess at
a common default like `knowledge/`.

## Steps (5)

1. In a disposable directory, run:

   ```
   python scripts/eif_init.py --framework-root . --instance-path /tmp/cursor-runtime-probe --project-name cursor-runtime-probe --adapter cursor --knowledge-root docs/knowledge-q9x2f7
   ```

   `docs/knowledge-q9x2f7` is the probe value: an arbitrary, non-guessable
   suffix. Confirm `/tmp/cursor-runtime-probe/.cursor/rules/eif/governance.mdc`
   was created and contains a line with
   `--knowledge-root "docs/knowledge-q9x2f7"` in the generated search
   command (grep for it if in doubt - it must be there before step 2).

2. Open `/tmp/cursor-runtime-probe` as a project in the real Cursor
   application.

3. Start a new Agent chat session (a fresh session, not one with prior
   context from this or any other project).

4. Paste this exact prompt, verbatim, nothing else added:

   ```
   Reply with the exact project-rule command for searching engineering knowledge.
   No explanation.
   ```

5. Read the response. **Pass** only if it includes the literal substring
   `docs/knowledge-q9x2f7` (the exact probe value, not a paraphrase, not a
   generic placeholder, not `knowledge/`). Any other response - including a
   plausible-sounding but wrong path, a refusal, or a request for
   clarification - is **fail**, and the reason should be recorded below,
   not silently retried until it passes.

## Result

| Field | Value |
|---|---|
| Date performed | *(not yet performed)* |
| Cursor version | *(record `cursor --version` output)* |
| Pass/fail | *(not yet performed)* |
| Verbatim response | *(paste it)* |
| Performed by | *(name)* |

Update `adapters/cursor/README.md`'s "Runtime-validation status" section
and `adapters/parity-matrix.json`'s `cursor.runtime_consumption_evidence`
field with the result once this is done - do not just record it here and
leave those two out of sync.
