# Template: Execution Packet Closeout

<!-- Knowledge source: GENERALIZE of the private EI's packet-closeout
pattern (paired with execution-packet-review.md, its independent-audit
counterpart). Kept: plan-vs-actual per session, verification results as
PASS/FAIL with the commands run (not prose), and the explicit
"not done / deferred" section - a closeout that only lists what succeeded
is the single most common way a packet's actual state drifts from its
claimed state. Dropped: the private dashboard/visual-hub update section -
re-add only if a project instance maintains a visual status page a packet
could make stale. -->

One file per packet: `<packet-root>/07-CLOSEOUT-<NNN>-<slug>.md`. Filled
in the final session, after every other session's work is done - not
drafted early and "topped up." Should be independently reviewable: someone
other than the agent that did the work should be able to verify every
claim below against actual repository/tool state, not just trust the
prose. See [`playbooks/execution-packet-review.md`](../playbooks/execution-packet-review.md)
for exactly how that independent check is done.

```yaml
---
packet: <packet-id>
type: closeout
status: not-started
created: YYYY-MM-DD
completed:
---
```

## Final status

`not-started | in-progress | completed | implementation-complete-integration-deferred | blocked`

- Final branch/SHA:
- PR/merge URL (if applicable):

## Plan vs. done

| Session | Planned result | Actual result | Evidence | Residual |
|---|---|---|---|---|
| | | | | |

## Verification

<Every command from every session's verification section, re-run once
at closeout time if the roadmap calls for a final full pass, or listed
as already-verified-per-session with the result. `PASS`/`FAIL`, not
"looks fine" - a passing build or a merged PR is not behavioral evidence
on its own.>

| Command | Result | Evidence |
|---|---|---|
| | | |

## Not done / deferred

<Anything in the charter's Definition of Done that isn't actually done,
with the real reason (owner-gated action, resource constraint, scope cut
mid-execution) - never silently omitted.>

## Knowledge Delta

<New facts, rules, decisions, risks, edge cases, and rejected hypotheses
from across the whole packet - see [`templates/knowledge-delta.md`](knowledge-delta.md)
for the section structure. Note anything worth promoting to shared
knowledge beyond this one project instance.>

## Next action

<What the owner (a human, not the agent) needs to decide or do next -
e.g. a go/no-go call, a follow-up packet, an owner-only action this
packet deliberately didn't perform.>
