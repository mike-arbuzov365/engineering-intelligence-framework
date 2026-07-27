---
type: rule
status: validated
scope: framework
evidence: OBSERVED
source: code
created: 2026-07-27
review_after: 2026-10-27
---

<!-- Frontmatter corrected 2026-07-27: this carried `type: reference` and
`status: active`, neither of which exists in the ontology. It is
prescriptive - what a post may and may not say - so `rule`, not a
descriptive type. OBSERVED/code because its forbidden-wording list is not an
aspiration: it mirrors the list `site/scripts/verify-claims.mjs` actually
enforces on every site build. -->


# Publishing rules

The rules everything published about EIF is written under: a ten-post series
in English and Ukrainian, planned as one arc rather than ten announcements,
and comments on other people's threads.

This file sits next to [`claims-evidence.md`](claims-evidence.md) on
purpose. A post is a public claim. Every claim published has to survive the
same register that governs the website, including its forbidden wording
list. If a draft needs a sentence the register does not allow, the sentence
is wrong, not the register.

**The drafts are not here.** They live in a separate private repository,
along with the comment history and the reactions, for three reasons in
descending order of weight. It holds other people's words, and storing named
third parties' arguments in a public repository without their knowledge is a
privacy problem rather than a matter of taste. A draft in a public
repository reads as a statement. And reaction data is worth keeping and
worth nothing to publish, since publishing it changes how people behave in
the threads it came from.

What stays here is what governs those drafts, because being checkable is the
entire point of it. Anyone can read the constraints this project publishes
under and hold a published post to them.

## What the series is for

Not reach. The framework has one maintainer and no support capacity, so a
thousand curious readers is worse than twenty who try it on a real
repository and say what broke.

The series succeeds if an engineer who runs coding agents daily reads one
post, recognizes a failure they have had, and understands the specific
mechanism that addresses it well enough to argue with it. That is the whole
goal. Every editing decision below follows from it.

## Audience

Primary: senior and staff engineers, tech leads and hands-on engineering
managers who already use coding agents on a real codebase and have hit the
memory problem. They do not need convincing that agents are useful. They
need a name for what keeps going wrong.

Secondary: the Ukrainian engineering community. Ukrainian is not a
translation courtesy here, it is the reason the locale layer exists and one
of the few parts of this project a reader can verify in two minutes.

Not the audience: buyers, executives looking for a platform, and anyone who
wants a tool that removes engineering judgment. The posts should read as
uninteresting to them, and that is fine.

## What the series claims, and what it never claims

Claims, all backed:

- Chat history is not engineering memory, and the failure modes are
  specific and nameable.
- EIF separates methodology, durable project knowledge and session context
  into three layers, with an explicit decision governing promotion between
  them.
- Retrieval happens before implementation.
- Execution is bounded: scope, evidence, stop conditions, closeout.
- Optional integrations stay optional, with named fallback paths.
- The project states what it has verified and inside what bounds.

Never, in any language:

- That it is production-ready, proven at scale, or an official release.
- That it improves quality, reduces rework, produces fewer bugs, or saves
  developer hours. None of that is measured.
- Any comparison of governed against ungoverned work. No such study exists.
- Any token reduction percentage.
- Any claim that a tool is needed for EIF to work.
- Any duration claim about a human. Nothing has been timed against a
  person.

The full list of banned strings is in
[`site/src/content/claims.json`](../../site/src/content/claims.json), and
the site build enforces it. Run a draft past that list before posting.

## Voice

The single rule: write the way you would write a message to one engineer
you respect, who is busy and has seen a lot of frameworks.

Everything below is a consequence of that rule.

**Never use, in either language:**

- Long dashes of any kind. Comma, colon, full stop, or rewrite the
  sentence.
- Emoji. Not as bullets, not as decoration, not one at the end.
- A rhetorical question as the opening line.
- One-sentence paragraphs stacked for rhythm. That layout is the single
  clearest tell that a post was optimized rather than written.
- "Here's the thing", "Let that sink in", "The result?", "Spoiler",
  "Plot twist", "Game changer", "unlock", "leverage", "supercharge",
  "10x", "revolutionize", "in a world where".
- Ukrainian equivalents: «А тепер найцікавіше», «І ось що я зрозумів»,
  «Результат?», «Це змінює все», «проривний», «революційний»,
  «наразі» (use «зараз»), «даний» (use «цей»), «у якості» (use «як»),
  «здійснювати» plus a noun where one verb exists.
- Numbers that are not measured. If a figure appears, it must be traceable
  to a file in the repository.
- A closing plea for engagement. No "what do you think", no "drop a
  comment", no "let me know below".
- Hashtags on more than the first and last post, and never more than three.

**Do use:**

- A concrete first line that states something, so the preview earns the
  click on its own.
- Paragraphs of two to four lines, blank line between.
- The specific mechanism rather than the adjective. "Promotion is a
  decision someone makes" beats "intelligent knowledge management".
- The bound, stated by you, before anyone else finds it. On LinkedIn this
  is the differentiator, not a weakness.
- One link, at the end, and only where there is something to read.

## Format and cadence

- Two posts a week, Tuesday and Thursday, roughly 09:00 Kyiv time. Five
  weeks for the arc.
- 900 to 1600 characters. Long enough to say the mechanism, short enough
  that nobody has to press "see more" twice.
- LinkedIn does not render code blocks or markdown. Any command goes on its
  own line as plain text, at most two lines, and only where it is the
  point.
- No images for the first three posts. From post four onward, one figure
  from the site per post is allowed where the figure genuinely explains
  something, exported as a plain PNG.

## Bilingual policy

Two separate posts, not one post with both languages stacked. Stacked
bilingual posts halve the readable length of each and read as neither.

- English post on the main feed.
- Ukrainian version as a separate post the following day, or on a Ukrainian
  professional community where one fits.
- The Ukrainian is written, not translated. Same facts, same order, same
  bounds. Where a literal rendering would sound like machine output, the
  sentence gets rebuilt.

## The arc

| # | Working title | The one thing a reader should take away |
|---|---|---|
| 1 | Chat history is not engineering memory | The problem has specific, nameable failure modes, and there is now a public repository |
| 2 | Three layers, and a rule for each | What is allowed to survive a session, and what should evaporate |
| 3 | Retrieval before implementation | Storing knowledge is the easy half |
| 4 | One session cannot promote its own lesson | Why learning runs as two loops, not one |
| 5 | A merged PR is not evidence | Bounded execution: scope, stop conditions, closeout |
| 6 | Ranking your sources in one list is the bug | Authority is multi-axis |
| 7 | What governance costs | The honest token accounting, with the balance left open |
| 8 | The tools are optional, and that is a design constraint | Named fallback paths, and the one call that leaves the machine |
| 9 | I made it hard for my own site to overclaim | The claims register and the build gate |
| 10 | The language is configuration, not a default | The locale layer, and what it does not cover |

---

## Commenting on other people's posts

The series is one half. The other half is arriving in threads that are
already happening, which reaches the audience described at the top of this
file far more directly than a post on a small account does.

Rules, in order of how easy they are to get wrong:

1. **Enter through the strongest objection in the thread, not through the
   post.** A comment that agrees with the author adds nothing. A comment
   that answers what three commenters are already arguing about is the one
   people read.
2. **Say the one thing nobody in the thread has said.** If it is already
   there, do not comment.
3. **Link only when the link is checkable.** If the repository is private
   or the site is not deployed, do not post. A comment whose whole argument
   is "here is a thing you can go read" and then cannot be read is worse
   than silence.
4. **Concede the author's frame.** Their model is usually not wrong, it is
   usually incomplete in one specific place. Say which place.
5. **State the bound in the comment itself.** Same rule as the posts. "It
   is explicit about what it has not measured" belongs in the comment, not
   in a follow-up when someone challenges it.
6. **One comment. No reply-to-own-comment threads, no editing to add a
   link.**

## What to watch, and what to ignore

Ignore: impressions, likes, follower count. They measure how well a post
suits a feed, which is not the goal stated at the top of this file.

Watch, in order of what each is worth:

1. Someone reports running it on a repository that is not mine. This is the
   only outcome that changes what gets built next.
2. A specific objection to a mechanism. "The two-loop thing will not survive
   a team of eight" is worth more than fifty agreements.
3. Someone finds a claim on the site that the evidence does not support.
   That is a bug report, and it goes in the register.
4. Comments that engage with the bound rather than the headline. A reader
   who says "n=1 per cell is not a benchmark" has read the post.

If four weeks in, nobody has done any of the four, the series is not
working, and the answer is probably that the posts are describing mechanisms
to people who have not hit the problem yet. In that case: fewer mechanism
posts, more concrete failure stories with the mechanism at the end.

## Reserve topics

Written up only if the arc lands and there is appetite for more.

- The privacy scan and its suppression mechanism. A suppression identifies
  one finding by rule, exact path, content fingerprint, rationale and review
  date. It never disables a rule and never weakens a pattern, and an expired
  suppression is itself a finding. Good post about the difference between
  an exception and a hole.
- Adopting an existing repository that already has its own governance. The
  preflight refuses to write anything until someone decides how the two
  coexist.
- Adapters as a frozen scope. Four, no fifth, and why deciding to stop was
  harder than adding another.
- What "experimental" is actually doing in the capability table, and why
  half the rows say it.
