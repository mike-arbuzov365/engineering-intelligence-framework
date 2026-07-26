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

---

## Closed

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
