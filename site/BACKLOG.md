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

**Status:** in-progress - two variants built, awaiting selection
**Raised:** 2026-07-25, owner review

Two compositions of the same model are now on the page for comparison:

- **Variant A, orbit.** Projects orbit one framework core; the packet hangs
  below the active project; the curator is a ring around the core.
- **Variant B, spine.** The framework layer is a horizontal spine, projects
  branch down from it, one branch opens into a packet of sessions, and the
  curator sweeps the spine.

Both show: one shared framework, several projects, a packet of sessions
inside one project, learning climbing out of it, and reaching another
project only when relevant (drawn dashed, because it is conditional).

**Known limitation, must be fixed before ship:** both figures live inside
the English `.i18n-block`, so they disappear in Ukrainian mode. The SVGs
themselves are language-neutral by design (EIF / P1..P4 / PACKET), so the
fix is to move the chosen one into both templates with a translated
caption. Deliberately not done twice for two variants when one is going to
be deleted.

**Next:** pick one, delete the other, translate its caption, add it to the
Ukrainian template.

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

**Status:** open
**Raised:** 2026-07-25, owner review

The framework's knowledge base is a linked, indexed, wiki-like structure
(generated index, cross-referenced artifacts, lifecycle status per node,
offline retrieval over it). The site never says this, and it is one of the
more concrete things a reader can picture.

**Done when:** the structure is described accurately for what the **public**
repo ships (`eif_generate_index.py`, `eif_search_knowledge.py`, `related:`
links, status lifecycle), without implying the private instance's larger
index set.

## SB-007 - Decide whether the curator is in v0.1 scope

**Status:** open (decision, not implementation)
**Raised:** 2026-07-25

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

---

## Closed

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
