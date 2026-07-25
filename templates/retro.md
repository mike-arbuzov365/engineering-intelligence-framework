# Template: Retro

<!-- Knowledge source: GENERALIZE of the private EI's retro artifact shape
(run-retro.md Step 5 / retro SKILL.md). Kept: the trigger/scope, metrics,
recurring-pattern, hotspot and Knowledge Delta sections. Dropped: that
instance's "Visual hub" drift section, which tracks one private HTML
artifact that does not exist in this framework. -->

Output of [`playbooks/run-retro.md`](../playbooks/run-retro.md). Written to
the project instance's own documented retro location.

Unlike a session closeout, this artifact is about the period, not the task:
every section below should be answerable only by looking across several
sessions.

---

```markdown
# Retro: <packet / incident / period>

Period: <start date> - <end date>
Trigger: <packet closeout | incident | cadence>

## Scope

<!-- Which repository, which packets/sessions, what is deliberately out of
scope for this retro. -->

## Activity

<!-- Derived from the repository (git log/shortlog, merged PRs, closeouts),
not from recollection. State the commands used. -->

## Completed

## Not completed, and why

<!-- Deferred, blocked or abandoned work with the reason, not just a list. -->

## Recurring patterns

<!-- The point of this artifact. Each entry needs the number of distinct
occurrences and where they were observed. A single occurrence is not a
pattern - record it as an incident or a risk instead. -->

| Pattern | Occurrences | Where observed | Type |
|---|---|---|---|

## Hotspots

<!-- Files or areas changed disproportionately often in the period. -->

## Rule gaps

<!-- Cases where the agent followed existing rules and the outcome was
still wrong. These are defects in the rules, not in execution. -->

## Stale knowledge

<!-- Artifacts whose review_after has passed, with a disposition for each:
still valid / superseded / deprecated. -->

## Knowledge Delta

<!-- Same contract as templates/knowledge-delta.md, including the explicit
promotion decision and the explicit "stays local" case. -->

## Entrypoint updates

<!-- Rules that changed as a result of this retro AND were applied to the
persistent agent-instruction file in this same retro. A rule recorded only
here is not in force. If none: say so explicitly. -->

## Next period

<!-- Priorities, not aspirations. -->
```

---

## If the period had nothing recurring

That is a legitimate and common result, especially for a short or quiet
period. Record it explicitly rather than inventing a pattern to fill the
table:

```markdown
## Recurring patterns

None. <N> sessions and <M> merged pull requests reviewed; no failure
signature, rule gap or hotspot appeared more than once.
```

Manufacturing a pattern from a single occurrence is the specific failure
this section guards against.
