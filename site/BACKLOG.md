# Site backlog

Open work on the presentation site, carried between sessions so it is not
re-derived from chat history each time. Same rule as everywhere else here:
an item states what is wrong or missing and how it would be judged done,
not just a wish.

Closed items move to the bottom with the commit that closed them, rather
than being deleted, so a reader can tell the difference between "never
raised" and "raised and handled".

Status: `open` | `in-progress` | `done` | `dropped` (with a reason).

---

## SB-001 - Strengthen the hero figure

**Status:** done (2026-07-25)
**Raised:** 2026-07-25, owner review

Resolved by making the figure work everywhere rather than hiding it: shown
at all widths, as a compact centred mark under the CTAs on phones and the
tall column beside the wordmark from 1080px up. The `T1/T2/T3` labels were
removed entirely - the figure sits outside the i18n block, so any text in
it would have been frozen in one language, and it is a mark rather than a
diagram. That fixed the bilingual problem and the small-screen legibility
problem in one move.

The three-layer hero figure works but is thin. There is room beside the
wordmark for something more expressive, and the accumulation idea could
read harder.

Constraint that makes this non-trivial: it must still look right on mobile
**in both languages**. Ukrainian strings are longer than English and the
figure is currently hidden below 1080px rather than solved for small
screens.

**Done when:** the figure reads as clearly at 390px as at 1440px, in both
languages, without pushing the CTAs below the fold; Lighthouse performance
stays at 100 with the visibility pause in place.

## SB-002 - Traced-diagram polish

**Status:** done (2026-07-25)
**Raised:** 2026-07-25, owner review (with screenshots)

Root cause of the lines not meeting the lanes was systematic, not visual:
flows terminated at y=344/346/74 while the lanes sit at 352/64. Every flow
now ends exactly on its lane, in the drawn paths and in the matching
`offset-path` values the dots travel, which have to stay byte-identical or
the dots drift off the line. The one real label overlap ("reusable
elsewhere" sitting on the L1 lane) was moved clear.

Two concrete defects in the packet-trace diagram:

- flow lines do not meet the layer lines cleanly - they approach at a
  slight offset instead of terminating on the lane;
- labels overlap other elements at some viewport widths.

**Done when:** every flow terminates exactly on its lane line, and no label
overlaps a line or another label at 1280px, 1440px and the mobile
breakpoint, in both languages.

## SB-003 - Show the multi-project and curator picture

**Status:** done (2026-07-25)
**Raised:** 2026-07-25, owner review

Variant A (orbit) was selected; Variant B (spine) is deleted. The kept
figure was then reworked rather than just moved:

- **Paired, not stacked.** Explanation on the left, figure on the right, so
  the figure is small enough to take in at once instead of running the page
  width. Stacks below 900px, capped at 19rem on phones.
- **A legend replaces in-figure text.** `CURATOR` was the only
  English-only string in the SVG and it also collided with the P4 spoke.
  It is now a translated legend item, which leaves the SVG fully
  language-neutral (EIF / P1..P4 / PACKET / SESSIONS) and identical in both
  templates.
- **Four beats in causal order** on one 16s cycle: method descends into the
  project before its packet starts, the three sessions run in turn, the
  lesson climbs only after the packet closes, and only then reaches P3 -
  with a ripple on the receiving project. Previously it was two beats and
  had no downward flow at all.
- Present in **both** language templates.

The site currently shows one project. The real shape is: one global
framework layer, many project repositories connected to it, packets inside
those projects containing many sessions, with session/packet open and close
rules, and validated learning rising to the global layer and descending to
other relevant projects.

Also missing: the **curator**, which watches the health and state of the
framework itself. It exists in the private instance
(`40-playbooks/knowledge-curator.md`) but **is not ported to this public
repository**, so it must not be drawn as a shipped capability until it is.
See SB-007.

Owner suggested producing two or three variants to choose from.

**Done when:** a visitor can see that this is a multi-project system, and
nothing shown is a capability the public repo does not have.

## SB-004 - Token economics on the site

**Status:** done (2026-07-25)
**Raised:** 2026-07-25, owner review

Nothing on the site says what governance costs. The honest position:
running EIF spends tokens up front (retrieval before work, packet
artifacts, Knowledge Delta, closeouts) and aims to repay that through
controllability and fewer wrong paths, with RTK and agent hooks
compressing tool output on top.

**Hard constraint:** `docs/product/claims-evidence.md` forbids claiming
efficiency or quality gains (CLM-08, CLM-09), and forbids quoting any
specific reduction percentage (CLM-06). So the page may state the cost
structure and that compression is measured, and must **not** state that the
net is positive - that has not been measured.

**Done when:** the cost/benefit structure is stated, the measured part is
separated from the unmeasured part, and `verify:claims:strict` still
passes.

## SB-005 - Expand RTK on the site

**Status:** done (2026-07-25)
**Raised:** 2026-07-25, owner review

The integrations section says "RTK" without expanding it. Verified via
Context7 (source reputation: High): **RTK is "Rust Token Killer"**, a CLI
proxy that filters and compresses command output before it reaches the
model.

Their published figure is a 60-90% reduction. **Do not put that number on
the site** - CLM-06 forbids any specific reduction percentage, and it is
the vendor's claim, not ours.

**Done when:** the acronym is expanded in both languages, in this site's
voice, with no borrowed performance number.

## SB-006 - Describe the wiki-like knowledge structure

**Status:** done (2026-07-25)
**Raised:** 2026-07-25, owner review

Added as a ruled block in the governed-learning section, in both
languages: front matter and `related:` links as what makes it a graph, a
generated index searched offline, status lifecycle excluding
rejected/superseded from retrieval, the three distinct failure outcomes,
and the curator as its maintenance pass. Nothing claimed beyond what the
public repo ships.

The framework's knowledge base is a linked, indexed, wiki-like structure
(generated index, cross-referenced artifacts, lifecycle status per node,
offline retrieval over it). The site never says this, and it is one of the
more concrete things a reader can picture.

**Done when:** the structure is described accurately for what the **public**
repo ships (`eif_generate_index.py`, `eif_search_knowledge.py`, `related:`
links, status lifecycle), without implying the private instance's larger
index set.

## SB-007 - Decide whether the curator is in v0.1 scope

**Status:** done (2026-07-25) - decided in, and ported
**Raised:** 2026-07-25

Decision: **in v0.1**, as a procedure rather than automation
(`playbooks/knowledge-curator.md`, `skills/knowledge-curator/`,
`templates/curator-report.md`; the private instance's scripted collectors
are not ported). It may therefore appear on the site, and does - in the
scale figure's legend and in the knowledge-base block (SB-006).

The curator is a substantial, working part of the private instance:
health/CI/lint/eval/index/closeout/retro aggregation into a ranked
maintenance backlog, a findings ledger with stable IDs and recurrence
escalation, and a closed set of safe auto-fix classes that never merge and
never touch project-layer source.

`HOW-EIF-WORKS.md` currently lists curator/knowledge-health as post-v0.1.
Porting it is comparable in size to the retro port, and it is arguably the
most differentiated piece of the whole system.

**Decision needed:** port for v0.1 (and then it can appear on the site), or
keep it explicitly post-v0.1. Until decided, it must not appear on the site
as shipped. Blocks part of SB-003.

## SB-008 - Consider borrowing from external workflow patterns

**Status:** open (analysis done, no implementation)
**Raised:** 2026-07-25, owner request

Reviewed the six patterns in the referenced dynamic-workflows article
against what this framework already does. Full reasoning is in the session
notes; the short version:

**Already covered, and more strictly:**

- *Loop Until Done* -> the Bounded Evidence Loop, which additionally
  carries iteration and remote-run budgets, failure signatures and a hard
  stop. The article's version guards against stopping early; ours guards
  against both stopping early and retrying forever.
- *Classify-and-Act* -> the routing checkpoint and skill-routing table.
  Notably this costs **zero** extra model calls, where the article uses a
  classifier agent.
- The article's core idea, that the plan should live outside the model's
  context, is what an execution packet already is - and a packet is a
  durable reviewable artifact rather than a single-run script.

**Partially covered:**

- *Adversarial Verify* -> `execution-packet-review.md` provides independent
  review at packet level, but there is no equivalent at session level.
  Worth considering, with cost in mind.

**Deliberately rejected:**

- *Fan-out-Synthesize* - multiplies model calls and directly conflicts with
  the single-agent operating policy.
- *Tournament*, *Generate-and-Filter* - both spend many calls to pick among
  candidates. Not compatible with a token-conscious system.

**Done when:** an owner decision exists on the session-level adversarial
verification question; the rest is recorded as considered-and-declined so
it is not re-litigated.

## SB-009 - Ukrainian caption and "before implementation" wording

**Status:** done (2026-07-25)
**Raised:** 2026-07-25, owner review

The traced-diagram caption read awkwardly in Ukrainian and said "до
роботи" where "до реалізації" is the sharper claim: experience has to
arrive before implementation, not merely before work starts. Reworded in
both languages and shortened; the English heading now says "before
implementation" too.

## SB-010 - Strengthen the hero figure again

**Status:** done (2026-07-25)
**Raised:** 2026-07-25, owner review ("good, but make it stronger")

SB-001 made the figure work at every width; it still only showed dots
rising. It now carries the whole model as one circuit - down the left,
across the bottom, up the right:

- **Retrieval descends first.** Method from the framework layer, then prior
  experience from the project layer, animated *before* any session dot
  moves. The ordering is the claim, so it is the first thing that happens.
- **One packet, three sessions.** An open bracket under the session lane
  (not a closed box, which read as a second container) with a tick per
  session, and the rising dots start from those ticks.
- **Promotion climbs the right arc** once per cycle, after the packet is
  done, and leaves a dimmer mark on the framework layer.
- **The curator** sweeps the framework lane on its own 26s period, never in
  step with the promotion beat.

Static/reduced-motion reading is unchanged in kind: three layers and a
packet, nothing accumulated yet.

## SB-011 - Strengthen the traced-packet figure

**Status:** done (2026-07-25)
**Raised:** 2026-07-25, owner review

SB-002 fixed the geometry; this makes the figure say more:

- **Session 2 retrieves too**, from a project layer that now contains
  session 1's own validated result. That is the compounding claim drawn
  rather than asserted, and it was previously missing - session 2 only
  received packet memory.
- **Each gate brightens** as the thing that must pass it arrives, so
  RETRIEVAL / CLOSEOUT+RETRO / PROMOTION DECISION read as checks in a
  sequence instead of three static rules.
- **Work is drawn while its session runs** instead of sitting there already
  finished.
- Two label overlaps found at 1100px were fixed: "facts and decisions
  carried forward" sat on the packet arc and crossed the closeout gate (now
  two lines, moved into the clear gap); a second retrieval label had no
  position free of the promotion flow, so it was dropped rather than
  crowded in - the dotted style and the left-hand label already carry it.

## SB-012 - Make the figures legible to a first-time reader

**Status:** done (2026-07-26)
**Raised:** 2026-07-26, owner review ("I understand it because I wrote the
framework; for everyone else it is just nice motion")

Every figure now names what it is showing, in the reader's language, with
markers that match the drawing:

- **Hero.** Four legend lines for the four moves. The SVG itself stays
  text-free and single-copy; the legend is its own i18n block.
- **Knowledge base.** Three legend lines: a circle is an artifact, a line
  is a `related:` link, the search enters from the index lane, and the
  dashed node is excluded and curator-flagged. Nodes now light in turn as
  the query reaches them, so it reads as a walk rather than a constellation.
- **Multi-project.** Already had a legend; P3 and P4 swapped so the numbers
  run clockwise from P1 instead of skipping.
- **Control plane.** The zigzag was a static drawing of a sequence. One
  pass now walks intent to durable knowledge and each station lights as it
  arrives. The numbered list beside it remains the complete version.
- **Token cost.** The column beside the cost statement was empty; it now
  holds the one thing this section may honestly show - output filtered
  before it reaches the model, and the unfiltered core path underneath.
  Proportions are illustrative of the mechanism, deliberately with no
  number, per CLM-06.

## SB-013 - Geometry and Ukrainian wording pass

**Status:** done (2026-07-26)
**Raised:** 2026-07-26, owner review (with screenshots of the junctions)

- **Junctions.** Screenshots showed flows arriving a few units short of, or
  past, the point they should meet. The closeout fork now leaves one exact
  point (492,352) for all three fates instead of three nearby ones;
  retrievals land exactly on the session node; the promotion flow reaches
  the promotion gate instead of stopping 50 units short and letting the
  bare lane stand in for it. Round caps and joins on every flow. All
  `offset-path` values updated to stay byte-identical to the drawn paths.
- **Hero stub.** The promotion arc landed 24 units short of the end of the
  framework lane, leaving a visible tail. It now lands on it, and the
  viewBox is cropped to the ink so the figure and its legend sit together.
- **"Робота" in Ukrainian.** Reads as "labour/job" where the sense is a
  unit of scoped work. Replaced with "задача" where that is what is meant,
  and "до початку роботи" with "до початку реалізації" throughout.
- **What descends.** "Метод спускається" undersold it. Both languages now
  name it: ontology and the authority model, rules and constraints,
  playbooks, templates and skills, plus the project's own prior experience.
- **"Три прискорювачі"** was arguable - they are not accelerators, they are
  optional help. Both languages now say so directly: "Three tools that
  help. None of them is the method."

## SB-014 - One legend system, and no long dashes anywhere

**Status:** done (2026-07-26)
**Raised:** 2026-07-26, owner review

- **One component.** Four figures had four hand-rolled legends with
  markers hung from the top of the first line, so a circle and a rule sat at
  different heights next to identical text. There is now a single
  `.figure-legend`: markers are centred on the first line's optical middle
  (`top: 0.75em; translateY(-50%)` against `line-height: 1.5`), and a marker
  means the same thing in every figure.
- **Missing markers.** The hero legend never mentioned the amber curator
  dot that is visibly on screen. It does now, as its own line.
- **Packet marker.** A plain rule read as "a line", not "these three belong
  together". Both the hero and the multi-project figure now draw the packet
  as a bracket with turned-up sides, and the legend marker is the same
  bracket.
- **Long dashes.** Em and en dashes are an AI tell and the owner does not
  want them on the site or in the repository. Purged; the only survivor was
  a pre-existing one in the social-card generator.

## SB-015 - Density and mobile quality

**Status:** done (2026-07-26)
**Raised:** 2026-07-26, owner review

- **Methodology (02).** The boundary note ran full width under a
  two-column grid whose left column was short, leaving a tall hole. It now
  sits with the statement it qualifies, and the columns end level.
- **Knowledge base (07).** Was the odd one out: figure stacked under its
  text with the legend under the figure. Rebuilt as the same pairing the
  multi-project figure uses, which is the composition that worked; the graph
  was re-laid into a squarer viewBox to suit the narrower column.
- **Phone CTAs.** Four wrapped pills produced a ragged 2+1+1 stack whose
  shape changed with language, because widths came from label length.
  Replaced below 720px with `repeat(auto-fit, minmax(min(100%, 13rem), 1fr))`
  (per current MDN guidance, checked via Context7): equal cells, one
  full-width column on a phone, identical in both languages.

## SB-016 - The last two static figures

**Status:** done (2026-07-26)
**Raised:** 2026-07-26, owner review

- **Control plane (04).** Covered in SB-012.
- **Evidence loop (06).** The ring predates the figure style and had become
  the one diagram that did not move. It now carries the same pulse on a
  slow 21s lap. The active phase is still driven by scroll position, not by
  where the pulse is, so the JS behaviour is untouched.
- **Capabilities (08).** The cost figure showed RTK only, which
  misrepresented a section about three tools. Rebuilt as three rows, one per
  tool, each with a solid route and the dashed core path under it, both
  arriving. Amber marks the two boundaries that exist: what RTK drops, and
  the point where a Context7 query leaves the machine. Both routes travel at
  the same pace on purpose, so nothing here implies a speed claim.
- **Sides alternate.** Hero right, multi-project right, evidence loop left,
  knowledge base right, capabilities left, so the page does not run down one
  rail.

## SB-017 - Hero composition and legend weight

**Status:** done (2026-07-26)
**Raised:** 2026-07-26, owner review

- **The key outweighed the drawing.** Legend markers were list-bullet
  sized: the curator's amber dot is the smallest mark in every figure and
  had become the largest object in the key, which reads as a different and
  more important thing. Every marker is now drawn at the weight it has in
  the figure, with 1.5px strokes matching the SVG, and small filled shapes
  where the figure fills them.
- **Figure and key are one object.** They sat in separate hero grid rows
  with a hole between them. They are now a single centred column bound by
  one hairline, spanning all three rows of the hero grid. That needed
  explicit `grid-template-rows`: with an implicit grid, `grid-row: 1 / -1`
  collapses to a single row and drops the aside above the wordmark.
- **The background path competed with the key.** A 2px rule running through
  13px mono text costs more legibility than that texture is worth; its
  opacity is down.

## SB-018 - Two figure defects found on screen

**Status:** done (2026-07-26)
**Raised:** 2026-07-26, owner review ("is `raw reasoning, dropped`
deliberately blurred?")

- **Not deliberate, a bug.** One CSS rule was shared between the dropped
  flow `<path>` and its `<text>` label, so the label got a stroke as well as
  a fill and every glyph rendered with a soft outline. De-emphasis belongs
  to colour, never to blur. Rules split; the label is now sharp muted text.
- **Labels on the lines.** The traced-packet figure names its own flows and
  is the easiest figure on the page to read because of it. The other three
  now do the same: the multi-project figure names what descends, what
  climbs and what the dashed relay depends on; the knowledge graph names its
  index lane and its superseded node; the capabilities figure names its two
  amber boundaries. A legend explains a vocabulary, a label says what that
  particular line is; both, not either.

## SB-019 - Ten defects from a full read-through

**Status:** done (2026-07-26)
**Raised:** 2026-07-26, owner review of the rendered page in both languages

Ten separate findings, kept as one item because eight of them share a single
cause: a component's own defaults or a decorative colour outranking the thing
it was meant to serve.

- **The hero key was not bound to its figure.** `sections.css` imports after
  `hero.css`, so `.figure-legend`'s `padding: 0` and
  `max-width: var(--eif-measure)` beat `.hero__legend` at equal specificity.
  The rule sat 1px above the first line of the key and ran 48px wider than
  the figure it captions. Scoped to `.hero__aside`; both now measure 336px
  and there is 32px under the rule.
- **"Flows up" looked like it had lost a paragraph.** Each flow is a two-row
  grid stretched to the taller column's height, and auto rows stretch, so the
  shorter half distributed its spare height into the gap under its own
  lead-in. `align-content: start`, plus the sentence the up direction was
  actually missing: what happens to validated knowledge that is *not*
  promoted.
- **The traced figure stuttered at session 2.** The packet-memory dot ran
  past its destination onto session 2's work segment and stopped on the exact
  point the promotion dot started from, so one dot froze, vanished and
  reappeared in place. The packet dot now ends where packet memory ends; the
  promotion dot starts at session 2's origin node and runs its work segment
  itself. The bridge geometry is symmetric about x=554 instead of leaning
  left.
- **"At closeout" was green for no stated reason.** The rule colours were the
  colours of the dots in the drawing above, but nothing said so, so the third
  column simply read as promoted above its neighbours. Uniform hairlines now,
  with each column carrying the marker of its own mark from the shared legend
  vocabulary.
- **The evidence-loop figure came from a different site.** 18px labels in a
  300-unit box drawn at 320px rendered at ~19 CSS px, against 10-13 for every
  other figure. Now 11px, r=7 nodes, a dotted ring at the page's weight, and
  an amber exit gate ending in an open stop mark, so a ring finally says the
  loop is bounded. Guarded by a test that compares its rendered label size to
  the traced map's.
- **Preconditions/Exits read as noise for three reasons.** Both headings were
  `.label` - the quietest element in each column - above terms in the same
  mono, same size, painted accent green; six preconditions in signal green
  said nothing; and `flex: 0 0 9rem` with wrapping let long terms push their
  definitions onto the next line, so definitions started at a different x in
  almost every row. Real headings with a one-line note each, a two-track grid
  for one axis, and accent kept for PASS/BLOCKED/DEFERRED where it means
  something.
- **`related:` in Ukrainian prose.** The field name was doing the explaining
  in a sentence that should have explained what the links do. Reworded in the
  paragraph and in the legend; English keeps the field name, where it is not
  an anglicism.
- **The quickstart raised two questions it did not answer.** Why Ukrainian
  (because a closeout rendered in English proves nothing about a locale
  layer - the point is that the language is configuration), and why a PyPI
  line was there at all. The clearer no-package-index wording from the
  removed limitations section replaced it.
- **Limitations removed as a section.** A page of disclaimers reads as a
  disclaimer page. Its two load-bearing statements moved next to the claims
  they qualify: no-quality/no-rework into the bounded-proof list, and
  no-package-index into the quickstart. Section numbering closed up to 11.
- **The page had no way to reach its author.** "Public repository (link added
  at publication)" also put a parenthetical disclaimer inside a call to
  action, and rendered in English on the Ukrainian page. The label is now the
  same promise in both states and both languages, the caveat is its own line
  that the production build empties, and the page ends with two contact
  channels in the page's own row idiom rather than a social-icon strip.

Also found on the way: the site's own privacy scanner read the `s` in
`https://` as a Windows drive letter, so the first outbound link the site
ever carried was reported as a leaked machine path.

## SB-020 - Second pass on the same five screens

**Status:** done (2026-07-26)
**Raised:** 2026-07-26, owner review of the SB-019 result

- **"Flows up" was still written as clauses on dashes.** Rewritten as plain
  sentences in both languages: what goes up, that it needs its own decision,
  that it usually stays put, and that promotion is the exception. Same
  treatment applied to "Flows down" so the pair matches.
- **Optional capabilities was overloaded, and it was overloaded by
  repetition.** Three surfaces carried the same three facts: a flow figure
  with a three-item legend, a bridge table, and three expandable rows with
  the actual boundaries and health evidence. The bridge table is gone. The
  two labelled paragraphs of measured/not-measured accounting are gone too;
  what they protected (no claim that the net balance is positive) survives as
  one clause, and what they restated (RTK measures compression) was already
  in the RTK row.
- **"Залишає машину" is not Ukrainian anyone writes.** Both languages now say
  the query goes to the network, in all four places the old phrasing had
  reached.
- **`pip install` was a caveat, not a capability.** It is a capability: the
  quickstart command is `pip install .` then `eifctl init`, which is what the
  installed-wheel suite already exercised, and `scripts/eif_release.py` now
  builds, index-validates and clean-installs the artifacts. Only the upload
  is left, and that needs credentials nobody automates.
- **The closing screen looked unfinished, because it was.** Three underlined
  links, a status line floating under them, a 100px hole, then a contact
  block bolted on at a different measure. Rebuilt as one grid: "Read on" and
  "Reach me", five rows, each with a label, a destination and one line of
  purpose. The repository's pre-publication status now sits inside the
  repository row, in the amber this page already uses for declared-but-not-
  yet-true. Footer reduced to name and licence.

---

## SB-021 - Release pass on capabilities, quickstart and the closing screen

**Status:** done (2026-07-27)
**Raised:** 2026-07-27, owner review ahead of the release

- **Optional capabilities looked bad and read worse in Ukrainian.** The
  figure sat in a 24rem column beside the cost note, behind a shared amber
  rule, so a drawing and a caveat were bracketed as if they were the same
  kind of thing. Rebuilt as four blocks in reading order: claim, figure,
  the three tools, then the price. The figure is full width, its legend is
  four one-line keys in two columns instead of three paragraphs, and the
  context box on the right finally has a key at all. The amber rule now
  brackets only the caveat, which is what it means everywhere else.
- **The screen answered nothing in its default state.** Three collapsed
  rows carried a name and a subtitle; the boundary, which is the fact
  people actually arrive with, was the opening clause of a paragraph inside
  a disclosure nobody had opened. Each row now shows `Local` or `Network`
  as a tag, and the Context7 tag is amber, matching its lane in the figure
  directly above.
- **Rows did not look like rows that open.** A caret, drawn only under
  `.js` because the no-JS path is already expanded, on both this list and
  the evidence ledger that shares the component.
- **The Ukrainian was translated, not written.** "Три інструменти, які
  допомагають. Жоден із них не є методом", "по одній обмеженій
  спроможності", "Керованість не безкоштовна в токенах", and "Без неї" for
  three masculine tool names. Rewritten against the English line by line,
  as Ukrainian someone would write.
- **The quickstart was a disclaimer with a command in it.** Heading,
  lede and a closing caveat all argued about release status. The commands
  work from a clone and the page never printed the package-index form, so
  the status notes were not protecting the reader from anything. They moved
  to [`docs/product/release-status.md`](../docs/product/release-status.md), and an
  end-to-end test now asserts they are gone and that the failing install
  form never appears.
- **The closing screen performed an attitude.** "Right now disagreement is
  worth more to me than agreement, so the second column is not decoration"
  told the reader how to feel about a contact form. Replaced with what is
  below it. Written against GOV.UK content guidance: plain words, no
  "please", front-loaded and self-explanatory link text. On-page rows now
  carry the page's own section numbers rather than saying "on this page"
  twice down one column, and each destination sits next to its purpose line
  instead of 44px above it.
- **Found on the way:** `all: unset` on the disclosure trigger also unsets
  the reset's `border-box`, so the caret's right padding measured wider
  than the row and put the whole document into horizontal overflow at every
  width below 1024px.

---

## SB-022 - Release pass, second round

**Status:** done (2026-07-27)
**Raised:** 2026-07-27, owner review of the SB-021 result

- **Full width was the wrong correction for the capabilities figure.** It
  read well on a phone and badly on a laptop: the drawing is three thin
  lanes between x=92 and x=392, so at 46rem it opened a gap down the middle
  of every lane while the legend sat stranded underneath. Recomposed on the
  section 07 knowledge-base grid instead: explanation and legend on the
  left, drawing capped at 24rem on the right, the three rows spanning both.
  The two screens now read as the same kind of object, and the figure keeps
  the proportions it already had at phone width.
- **The evidence ledger was out of date.** The install row still led with
  "not published to PyPI" as its limitation, which is release status, not
  evidence, and which the previous pass had already moved off the page
  everywhere else. It now states the command that works, `pip install .`
  from a clone, and keeps only the bounds on the evidence itself. The
  switching row still described Codex and Hermes as pending rather than as
  a frozen four-adapter scope.
- **"Bounded proof on record" was a disclaimer block appended to a page of
  claims.** Gone as a block. Measuring is one of the things this framework
  does, so it is now an eighth row, `Measure`, with the pilot in it and its
  two limits inside it rather than trailing the whole section. Nothing was
  dropped: CLM-08, CLM-09 and CLM-10 all still resolve, and the strict
  claims gate proves it.
- **The closing screen said less than it could.** "Developed in the open"
  left the reader to work out whether the framework or the engineer was
  being described, and it buried the strongest available fact. The screen
  now opens with what this repository actually is: the public extraction of
  a private framework in daily use on real projects, across different
  agents and models, where the models change and the governance does not.
  Two notes follow it, on the two layers experience accumulates in and on
  why adapters exist, stated as mechanism rather than as an outcome claim
  nothing here has measured.

---

## SB-023 - The two figures swap places, and every figure answers on hover

**Status:** done (2026-07-27)
**Raised:** 2026-07-27, owner review

- **The wrong drawing was at the top of the page.** The hero carried the
  circuit diagram: three lanes, a packet bracket, and five lines of key
  under it. That is a diagram, and a diagram at the top of a page asks to be
  studied before the reader has any reason to. The orbit map from section 03
  is a mark: symmetrical, self-contained, one shape. They swapped. The hero
  has no key now, because a hero is a poster, and the circuit landed in
  section 03 where its five-line key belongs and where the surrounding prose
  is already about exactly what it draws.
- **The hero mark carries text, the circuit does not.** So the hero grew its
  own i18n block and a Ukrainian twin, and section 03's two templates now
  hold an identical language-neutral copy. The mark also went from 21rem to
  26rem: at 21rem its route notes rendered near 10px, under this page's
  floor for anything meant to be read.
- **Two class-name collisions came with the swap.** `.hero__figure` is now
  in both places, so the pause rule and main.js both had to scope to
  `.hero`, or scrolling past the hero would freeze the section 03 circuit
  exactly when someone is reading it. And the hero figure now lives inside
  an i18n block, so the IntersectionObserver had to become re-bindable and
  disconnect its predecessor rather than leaking one per language toggle.
- **Every drawn object that means something now names itself on hover**, in
  whichever language the page is showing. The text lives in `data-tip` on
  the shape inside the i18n block, so the Ukrainian template carries its own
  copy and there is no translation table. One shared tooltip node, clamped
  to the viewport so a tip on a shape at the edge of a figure does not hang
  off the page.
- **Pointer-only, deliberately.** Every figure already has a written key
  carrying the same content, so making forty SVG shapes focusable would add
  forty tab stops that tell a screen-reader user nothing new. The figures
  stay `aria-hidden`, the tips are hidden entirely under `hover: none` where
  they would flash on tap and sit behind a finger, and Lighthouse
  accessibility stays at 100.

---

## SB-024 - Hoverable lines on the hero mark, and a copy button

**Status:** done (2026-07-27)
**Raised:** 2026-07-27, owner review

Recorded after the fact: this round shipped as commit `8d50b25` without a
backlog entry, which is the one thing this file exists to prevent.

- **The hero mark's thin lines were unhittable.** A 1px dashed stroke is not
  a pointer target. Every line carrying a tip got an invisible twin at 18
  units of the viewBox laid over it, with the tip on the group holding both,
  so the wide twin and the drawn shape answer the same. `pointer-events:
  stroke` rather than `all`, or the twin's empty fill area would swallow
  hovers meant for whatever sits inside a large circle.
- **The command block had no way to copy it.** A copy button now sits in the
  corner of the block, always visible rather than revealed on hover - the
  common pattern hides the one affordance the block has from anyone who does
  not think to hover. The confirmation is the button itself changing, not a
  toast covering the thing that was just copied, and it confirms nothing
  unless the write actually succeeded: `navigator.clipboard` rejects on an
  insecure origin and under permission policy, and the selection fallback
  still works there.

---

## SB-025 - Five defects from an owner read of the quickstart

**Status:** done (2026-07-27)
**Raised:** 2026-07-27, owner review

- **A clicked loop node kept a focus artifact.** `:focus-visible` was
  already suppressing the outline, and it never fired for the case that
  needed it: Chromium does not match `:focus-visible` on an SVG group
  clicked with a mouse, only on one reached by keyboard. So the browser drew
  its own ring around the group's bounding box, which includes the label 24
  units below the dot - a pale rectangle around a node rather than a ring
  around a control. Suppressed on `:focus`; the keyboard indicator is
  untouched and was verified separately, `Tab` onto a node still matches
  `:focus-visible`.
- **A Ukrainian tooltip read as an unadapted translation.** "Її міркування
  тимчасові, переживає її лише перевірене" is the English word order with
  Ukrainian words in it, and a bare nominalized adjective doing the work of
  a subject. The same defect class appeared three more times in the same two
  figures: "ніж набуте пропонують нагору", and a curator that "нічого не
  зливає" twice, where "зливає" reads as leaking rather than merging. All
  four rewritten, and the session line now matches the phrasing the layers
  figure already used for the same idea.
- **The quickstart answered none of the questions it was actually being
  asked.** Two bare lines and a full stop: where do I paste this, is that
  trailing dot a typo, and what do I do on macOS or Linux or anything that
  is not the machine this was written on. It is two numbered steps now,
  because only the first differs per platform, with a command block each for
  macOS/Linux/WSL, Windows PowerShell and Windows CMD behind a tab strip. It
  names the prerequisites, explains the dot, and states the one shell
  difference a reader would otherwise hit as an error - PowerShell 5.1
  parses `&&` as a parser error, which is exactly the trap the reference
  implementations of this pattern call out too.
  Every command was run before it was published: clean 3.11 virtual
  environment, `pip install .` from the clone, `eifctl init` into a fresh
  directory, which initialized an instance and reported in its declared
  locale. All three panels ship in the static markup and stay open without
  JavaScript, each under its own heading, so the no-script path is the
  complete one rather than a strip that cannot switch.
- **The copy button had no hover label.** An icon-only control that says
  nothing until it is pressed. It reuses the figure-tip machinery already on
  the page rather than growing a second tooltip system, which also gets it
  the viewport clamping, the `hover: none` suppression and the language
  rebinding for free. The tooltip is also where the confirmation lands now:
  the icon swap alone does not name what happened, and a pointer user had no
  written confirmation at all.
- **The paragraph after the commands never got muted.** It was the only
  unclassed direct `<p>` child of a `.section__inner` on the whole page, so
  it inherited the body foreground and read at lede weight while every
  comparable supporting paragraph on every other screen is
  `--eif-fg-muted`. It also opened by explaining two commands that the two
  numbered steps now explain in place, so that half is gone rather than
  restated.

Two things this round found that were not on the list:

- **The social-image URL was relative on any host with a deployment
  sub-path.** Setting a real project-page `EIF_SITE_URL` for the first time
  made `verify:bundle` fail immediately: Vite rebases root-relative asset
  paths against `base` before the metadata plugin runs, so the plugin's
  literal `/social-card.png` match found nothing. Matched on filename now.
  Only a root-domain site URL ever hid this.
- **`verify:bundle` did not check for surviving build markers.** It does
  now, in every mode. The clone URL is the first command a reader pastes, so
  an unsubstituted `__EIF_*__` there is a broken first impression rather
  than a cosmetic slip.

---

## SB-026 - Five more from the same read, and the site goes live

**Status:** done (2026-07-27)
**Raised:** 2026-07-27, owner review

- **The quickstart never said English is the default.** The demo declares
  Ukrainian on purpose, and a reader could easily take that for the default.
  Verified by running `eifctl init` with no `--locale` at all: it writes
  `locale: en` and reports in English. Now stated where the flag is
  explained, in bold, because it is the sentence that stops the
  misunderstanding.
- **The argument note was one sentence holding three arguments.** The owner
  could not parse it either, which is the whole verdict. It is a definition
  list now, one row per argument on the same two-track grid the loop's
  contract block uses, so a reader can find the one they are stuck on
  instead of re-reading a sentence to extract it. `--instance-path` also
  says that `.` works, which is true and was the missing practical detail.
- **The Source link went nowhere.** `EIF_REPOSITORY_URL` was
  production-gated, so dev and preview resolved the closing screen's one
  outbound destination to `#evidence` and printed "the repository link is
  added at publication" underneath it. Correct while publication was an
  undecided owner call; a dead link and a false caption the moment the
  repository is public. The URL is a project constant now, resolved in every
  mode, and the pending line is deleted rather than left permanently empty:
  it captioned a state that no longer exists.
- **The repository had no social preview.** Every link to it rendered as
  GitHub's generic auto-card. `generate:social-assets` emits a 1280x640
  card from the same brand source as the site's own, written to `.github/`
  rather than `public/` because the site never serves it. Found one defect
  while drawing it: a 3px accent rule in a centred flex column shrinks to
  nothing without `flex: none`, so the rule was silently absent from the
  first render.
- **The site is deployed.** `.github/workflows/pages.yml`, on any change
  under `site/`. It runs the three fail-closed verifiers and nothing else;
  the browser gate stays local, because duplicating it in CI would cost
  minutes to re-prove what a local run already proved. It contradicts D-14's
  "push to main triggers no workflow", so the boundary is recorded as D-15
  rather than left for a reader to find: D-14 governs validation topology,
  and this job runs no test.
  Two runs failed before one worked, and both failures were worth having.
  The first: `configure-pages` returned "Get Pages site failed ... Not
  Found", because Pages had never been turned on. The obvious fix,
  `enablement: true`, produced the second: "Create Pages site failed:
  Resource not accessible by integration". A workflow's `GITHUB_TOKEN` may
  deploy to a Pages site and may not create one, which is not something the
  action's own documentation leads with. Creating it is therefore a one-time
  owner-credentialed call, made and then written into the workflow beside
  the step that needs it, so the next person reads it there instead of
  deriving it from a red run.

---

## Closed

- **SB-026** default locale stated, argument note rebuilt as a list, the
  Source link made live in every mode, a GitHub social card, and the Pages
  deploy.
- **SB-025** loop focus artifact, four Ukrainian tooltips, per-platform
  quickstart with a copy tooltip, muted outcome paragraph; plus a sub-path
  social-image bug and a build-marker check found on the way.
- **SB-024** hoverable twins on the hero mark's thin lines, and a copy
  button on the command block that confirms only a real write.
- **SB-023** hero and layers figures swapped, hero key removed, hover tips
  on every meaningful object in both languages.
- **SB-022** capabilities recomposed on the knowledge-base grid, ledger
  brought current, proof block folded into a Measure row, closing screen
  given its strongest fact.
- **SB-021** release pass: capabilities rebuilt around the boundary
  question, quickstart stripped of release notes, closing screen rewritten.
- **SB-020** second review pass: capabilities de-duplicated, `pip install`
  made real, closing screen rebuilt as one grid.
- **SB-019** ten review findings fixed; limitations folded into the claims
  they qualify, and the page now ends with a way to reach its author.
- **SB-017** hero figure and key composed as one object; legend markers
  drawn at the weight they have in the figures.
- **SB-018** the dropped-reasoning label was outlined, not blurred by
  choice; fixed, and the remaining figures now carry labels on their lines.
- **SB-014** one legend component across every figure; long dashes purged.
- **SB-015** methodology and knowledge-base density fixed; phone CTAs
  rebuilt as an auto-fit grid.
- **SB-016** the evidence loop and the capabilities figure now move in the
  same language as the rest, and figure sides alternate down the page.
- **SB-012** every figure explains itself in the reader's language; the
  control-plane sequence and the token-cost column are no longer static.
- **SB-013** every junction meets exactly, and the Ukrainian says "задача"
  and "реалізація" where it meant them.
- **SB-003** Variant A selected, Variant B deleted, figure paired with its
  text, curator moved into a translated legend, four-beat animation, both
  languages.
- **SB-006** wiki-like knowledge structure described in both languages.
- **SB-007** curator decided into v0.1 and ported; it may appear on the site.
- **SB-010** hero figure carries retrieval, packet, promotion and the
  curator as one circuit.
- **SB-011** traced figure gains session-2 retrieval, gate pulses and drawn
  work; two label overlaps fixed.
- **SB-004** token economics stated on the site, with the measured part
  (compression) separated from the unmeasured part (net balance), inside
  what CLM-06/08/09 permit.
- **SB-005** RTK expanded as Rust Token Killer in both languages, verified
  via Context7 (High reputation), without borrowing the vendor's reduction
  percentage.
- **SB-009** caption reworded in both languages; "before implementation"
  replaces "before the work".
- **SB-001** hero figure shown at every width, compact on phones, and made
  language-neutral by dropping its labels.
- **SB-002** every flow now terminates on its lane; the one real label
  overlap moved clear.
