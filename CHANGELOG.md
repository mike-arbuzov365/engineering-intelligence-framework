# Changelog

Notable changes to the Engineering Intelligence Framework.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning is [semantic](https://semver.org/), with the caveat that
**anything marked experimental below may change shape within 0.x** - see
[`core/policies/decisions.md`](core/policies/decisions.md) for which
decisions are ratified rather than provisional.

This file follows the same evidence rule as the rest of the repository: a
capability is listed under Added only if it is runnable, not if it is
designed. Anything verified within bounds says so, and the bounds are part
of the entry rather than a footnote.

## [Unreleased]

## [0.2.2] - 2026-07-29

Completes the line-ending contract 0.2.1 started. Found the same way and on
the same day: by cloning a real connected project on Windows after installing
the published 0.2.1 wheel, instead of trusting that the fix was finished.

### Fixed

- The managed `.gitattributes` block now covers every file EIF writes, not
  only the ones whose bytes it hashes. 0.2.1 left `.gitattributes` and
  `.gitignore` uncovered, so those two landed in exactly the trap the block
  exists to close: EIF writes them as LF, `core.autocrlf` wants CRLF, and git
  reports them modified forever with an empty diff. A dirty `.gitattributes`
  is the worst file to leave dirty, because git reads the attribute stack
  from it while deciding how to materialize everything else.
- `.eif/config.yaml`, `.eif/framework.lock.yaml` and `.gitignore` are written
  as bytes rather than through text mode. Python's newline translation was
  landing them as CRLF on Windows while git stored LF, which the new
  attributes then surfaced as a permanent phantom modification. The
  entrypoint and the knowledge index already wrote bytes for this reason;
  these three were the ones that had never needed it before.
- `scripts/tests/test_line_endings.py` now asserts the property end to end
  rather than the mechanism: clone a connected project with
  `core.autocrlf=true`, upgrade it, and the tree must still be
  committable-clean. `core.autocrlf` is set explicitly so the check means the
  same thing on a Linux runner as on the Windows machine where the symptom
  appeared. That check fails on 0.2.1 and passes here.

### Known limitations

- Unchanged from 0.2.1, including the three installed-wheel
  integration-status checks that fail on 0.2.0, 0.2.1 and 0.2.2 alike.

## [0.2.1] - 2026-07-29

Owner-walkthrough patch. Every entry below comes from running the documented
0.2.0 path end to end on two real private repositories on Windows, not from
a synthetic fixture. It changes no schema and needs no migration.

### Fixed

- The documented `eifctl init <path>` form now exists. It previously failed
  with `unrecognized arguments`, which meant the first command of the
  published "connect an existing repository" path did not run. The path may
  also be given as `--instance-path`, and on a first-ever init the project
  name defaults to the directory name instead of being required.
- Each instance now carries an EIF-managed `.gitattributes` block pinning
  `text eol=lf` on the config, both locks, the agent entrypoint, the
  knowledge index, and a workspace's content root. Git for Windows enables
  `core.autocrlf` system-wide, so a fresh clone previously checked those
  files out converted, failed the knowledge-index hash check on content
  nobody edited, and left every upgrade reporting files as modified with an
  empty diff.
- `doctor` distinguishes a line-ending conversion from a hand-edit. A file
  that matches its recorded hash after CRLF-to-LF normalization is reported
  as exactly that, with the normalization command, instead of accusing the
  user of editing it.
- A routine upgrade that resolves to identical provenance no longer rewrites
  `.eif/framework.lock.yaml` to move its timestamp. Every fleet apply used to
  leave every project dirty with a one-line diff that had no content behind
  it, and that diff then blocked the next fleet run on its own clean-tree
  gate.
- Workspace freshness is decided by resolved content rather than by the
  workspace's git HEAD. Registering project N+1 previously invalidated the
  pinned snapshot of all N already-connected projects and forced a
  re-materialization plus a commit in each, for a byte-identical bundle.
- A pre-existing workspace-runtime problem is no longer reported as
  `axis=framework`. The framework axis defers the workspace check to the
  coordinated workspace step that immediately follows and can repair it, so
  drift no longer blocks the command that fixes it.
- `doctor` ends with its own verdict line. The wrapped script printed "all
  checks passed" before the wrapper's checks had run, so a failing command's
  last line claimed success.
- The private-workspace test suites shipped in 0.2.0 were registered in no
  runner, so no workflow executed them. They are now part of the inventory
  that `release-check.yml` runs.

### Changed

- `eifctl projects upgrade` reports `change=yes` or `change=no` per axis and
  states plainly when every active project is already current, instead of
  inviting an apply that would write nothing.
- `eifctl workspace doctor` prints the registered projects and their
  machine-local mapping, which its own help already promised.
- Error messages name the next command: a dirty workspace explains that
  `projects add` edits committed state, a missing machine-local location
  explains that the map is per-machine and how to rebuild it, a missing
  workspace runtime names the command that re-materializes it, a missing
  pinned runtime names the rehydration command, and a dirty project blocking
  detach names `--allow-dirty-project`.
- `eifctl --help` lists the real `projects` subcommands, `eifctl init --help`
  documents the packaged interface rather than leaking the standalone
  script's own required flags, and each subparser reports its true program
  name.
- The project lifecycle guide covers committing the registry, working from a
  second machine, repairing a drifted snapshot, and Windows line endings.

### Known limitations

- Carried forward from 0.2.0: fleet apply is preflighted but is not atomic
  across repositories, workspace profiles remain experimental within 0.x,
  EIF creates no GitHub repository and pushes nothing, and the package is
  distributed through GitHub Releases rather than PyPI.
- `scripts/tests/test_package_build.py` fails three integration-status
  checks against an installed wheel, on this release and on 0.2.0 alike:
  the doctor reports a configured Graphify provider as `misconfigured`
  rather than reaching its degraded, healthy and RTK-canary states. It was
  never caught because `release-check.yml` is `workflow_dispatch` only and
  has no recorded run, so the one suite that exercises an installed wheel
  had never executed in CI. Reproduced against the `v0.2.0` tag before
  being reported here; it is not a regression from this release, and it is
  not fixed by it. The remaining 72 checks in that suite pass, including
  the whole workspace lifecycle from a built wheel.
- The packaged `integrations/vendor-docs/manifest.json` does not validate
  against `core/schemas/integration-provider-manifest.schema.json`. Found
  while investigating the item above, unrelated to this release's scope,
  and left unfixed rather than changed without evidence about which of the
  two is wrong.

## [0.2.0] - 2026-07-28

First private-workspace release. It adds an optional user-owned workspace
inside the project intelligence layer. The public EIF package remains the
only framework distribution.

### Added

- `eifctl workspace new|doctor` creates and verifies a local private
  workspace repository without creating a remote, choosing visibility,
  pushing, or publishing anything.
- Registry schema v2 keeps stable logical project identities in committed
  state and moves machine-local paths into a separate ignored locations
  file. A named dry-run-first v1-to-v2 migration rolls both files back on
  failure.
- Workspace profiles resolve required, default, optional, and explicitly
  overridden artifacts. Selected content is staged, hashed, verified, and
  materialized into each project with a separate workspace lock.
- Fleet planning now compares framework and workspace provenance
  independently, preflights every active project before the first write,
  and reports the exact completed, failed-axis, and untouched sets.
- `eifctl projects detach` removes only workspace-managed runtime and lock
  files. It is plan-only by default and keeps the logical registration
  unless removal is explicitly requested.
- Synthetic workspace, resolution, transaction, fleet, migration, and
  installed-wheel coverage.

### Changed

- Ratified D-18 defines the private workspace as optional durable scope
  inside L2, not a fourth intelligence layer or a private framework fork.
- `eifctl` now exposes 11 commands, adding `workspace`.
- Project lifecycle documentation now distinguishes the public framework
  update axis from the private workspace update axis and documents the
  migration ledger and review boundary.

### Fixed

- Pinned-runtime verification now disables bytecode writes, so a fleet
  dry-run does not leave `__pycache__` in a connected project.

### Known limitations

- Workspace profiles and fleet coordination are experimental within 0.x.
- EIF does not create GitHub repositories, choose their visibility, or push
  project history.
- Fleet apply is preflighted but is not atomic across repositories. Earlier
  successful projects remain updated if a later apply fails.
- The package remains distributed through GitHub Releases, not PyPI.

## [0.1.3] - 2026-07-28

Small planning-continuity patch. It adds the missing steps between a raw
idea and a prepared implementation packet. It does not change project
schemas or add the planned private workspace runtime.

### Added

- Canonical `plan-idea` and `plan-prd` skills, backed by one playbook and
  one reusable template each. The flow keeps source evidence, assumptions,
  approval and routing explicit from idea to PRD to task or execution
  packet.
- Structural tests for the planning chain, including the approved-idea
  boundary, observable PRD acceptance criteria and carry-over into packet
  planning.
- A fully prepared, sanitized
  [EIF 0.2.0 execution packet](planning/packets/EIF-020-private-workspace/00-README.md)
  for the optional private workspace scope. It is planning evidence only,
  not an Available capability claim.

### Changed

- The operating protocol now routes raw ideas and approved ideas that still
  need requirements before it classifies implementation as one task or an
  execution packet.
- The public operating set now contains 15 playbooks, 17 templates and 11
  skills.

## [0.1.2] - 2026-07-28

Small dogfood stabilization patch. It changes no methodology or project
schema.

### Fixed

- Installed-package provenance and project runtime manifests now ignore
  interpreter-generated `__pycache__`, `.pyc`, and `.pyo` files. Resource
  digests are stable across Python installs and runtime bundles contain only
  portable release inputs.
- Repeated upgrades no longer add a blank line after EIF-managed blocks.
  The marker merge preserves the existing project-owned tail byte for byte
  with both LF and CRLF line endings.

## [0.1.1] - 2026-07-28

Small stabilization release for using the public package with real private
projects. It adds the missing create, connect and update lifecycle without
changing the methodology's core model.

### Added

- `eifctl new` creates a greenfield EIF project as a local git repository in
  a temporary sibling directory, then atomically moves it into place. It can
  register the completed project in a private project registry.
- `eifctl upgrade` plans or applies a guarded update from the installed EIF
  package. It blocks dirty repositories, verifies the pinned runtime,
  preserves user config and runs `doctor` after the transaction.
- `eifctl projects add|remove|status|upgrade` manages a schema-validated,
  user-owned private registry. Fleet updates preflight every project before
  the first write and remain plan-only until `--apply` is explicit.
- A project lifecycle guide documents the exact GitHub artifact, private
  registry, source-migration and compatibility boundaries.

### Changed

- Added one bilingual terminology contract and matching machine-readable
  English and Ukrainian terminology packs. The contract distinguishes
  standards-aligned, industry-established, and EIF-defined terms.
- Reworked Ukrainian project templates and presentation-site copy for clearer
  sentences, consistent terminology, and the canonical `Knowledge Delta`,
  `execution packet`, and `Bounded Evidence Loop` names.
- Fresh package-based instances now record the actual installed release
  version instead of the old development placeholder.
- Migrating an older git-sourced instance to installed-package provenance
  uses explicit `--migrate-source` and preserves `.eif/config.yaml`.

### Fixed

- Frontmatter validation now handles both flat and nested configured
  knowledge paths, deduplicates overlaps and skips only EIF's generated
  managed index. A hand-authored frontmatter-less index still fails closed.
- Fleet dry-runs now reject dirty repositories, so `--apply` cannot start
  changing earlier projects before discovering an unsafe later target.

## [0.1.0] - 2026-07-27

First public release, and the public extraction of a private production
instance that has run this methodology daily since May 2026. The repository
is functional, reviewable and installable from a clone, and the presentation
site is live. What this release does not claim is listed under Known
limitations below, in the same file as what it does.

### Added

**Methodology core**

- Four-axis authority model (normative, empirical, agent-execution,
  knowledge-lifecycle) replacing a single ranked source hierarchy. A
  normative source disagreeing with an empirical one is recorded as a
  discrepancy, not resolved by rank.
- Knowledge taxonomy, confidence levels, and a status lifecycle
  (`draft` -> `validated` -> `superseded`/`deprecated`, plus `rejected`
  for hypotheses only) with append-only retraction.
- Three-tier context model: reusable framework method, durable project
  knowledge, ephemeral session state, with Knowledge Delta governing
  promotion between them.
- Two-loop learning model: an inner per-session loop, and an outer
  [retro loop](playbooks/run-retro.md) that asks what repeats across many
  sessions. Promotion is driven by the outer loop, because one session
  cannot establish that its lesson generalizes.
- Bounded Evidence Loop contract: named evaluator, iteration and
  remote-run budgets, failure signatures, and `PASS`/`BLOCKED`/`DEFERRED`
  exits.

**Operating layer**

- 13 playbooks, 15 templates, 9 invokable skills covering session
  preparation/execution/closeout, execution-packet planning/execution/
  review, knowledge search/ingest/lint, the bounded evidence loop, and
  retro.
- Execution packets: a canonical artifact set for work spanning more than
  one session, carrying charter, facts, decisions and roadmap across
  sessions so later ones do not reopen settled questions.

**Tooling**

- Installable `eifctl` package with 7 subcommands (`init`, `doctor`,
  `search`, `render`, `privacy-scan`, `validate`, `version`), verified
  from a built wheel in a clean virtual environment whose path contains a
  space and non-ASCII text. **Not published to PyPI.**
- Instance bootstrap and upgrade with real provenance, a sha256-hashed
  runtime bundle, and transactional rollback proven by fault injection
  after each commit stage and partway through individual writes.
- Instance self-verification (`eif_verify_runtime.py`): config/lock schema
  validity, per-file bundle hashes, adapter/config consistency, marker
  integrity, and drift between config and the generated entrypoint.
- Adoption onto an existing, already-governed repository: a preflight that
  stops before any write when there is no coexistence decision on record,
  a `coexist` mode that defers to existing rules, configurable knowledge
  paths with path-escape validation, and finding-specific privacy-scan
  suppressions.
- Offline, Unicode-aware, lifecycle-aware knowledge retrieval that reports
  unparseable, schema-invalid and not-found as three distinct outcomes
  rather than collapsing them into "no results".

**Adapters** (scope frozen at four)

- Claude Code, Cursor, Codex and Hermes, all four supported (D-16), each
  re-verified against that agent's own primary or installed source rather
  than a documentation page, with real installed-CLI runtime proof from
  isolated home directories. What differs between them is hook mechanics,
  stated per adapter: Cursor has no tool-call hook to enforce through, and
  the Codex and Hermes contracts block rather than rewrite.
- All 12 directed switching pairs proven, with exactly one active EIF
  block and project content preserved after every switch.

**Optional integrations** (none required; each degrades to a named core path)

- RTK shell-output compression: version/argv/native-search/diff canaries,
  a command registry, and content-free local telemetry. A failed required
  canary reports `degraded`; raw proxy routes record zero savings.
- Graphify structural graph: query/path/explain canaries and an artifact
  lifecycle bound to source commit, graph digest, repository identity and
  reviewed scope. Only `fresh` reports healthy.
- Vendor docs: declares Context7 over MCP, with generated routing guidance
  and a reviewable per-adapter config template.

**Governance and safety**

- Privacy scanner, frontmatter/config/lock validation, link checking, and
  Knowledge Delta classification, each with its own test suite and each
  runnable from a project instance's own bundle.
- Controlled merge entrypoint that re-verifies checks, Knowledge Delta and
  review state twice before merging, pinned to a verified head SHA.
- Public claims-evidence ledger recording, per claim, what is `OBSERVED`
  vs `UNVERIFIED` and the exact wording each claim does and does not
  permit.
- Issue templates that require the command and real output rather than a
  recollection, including an evidence-report template for contributing
  verification of anything the repository lists as unverified.

**Localization**

- English-canonical framework docs with a per-instance documentation
  locale. Ukrainian is the first locale pack: status messages, Knowledge
  Delta, closeout headings and knowledge retrieval.

**Presentation**

- Bilingual site source in [`site/`](site/README.md), locally buildable,
  gated on claim citations, byte budgets, two browser engines, axe and
  Lighthouse. Published to GitHub Pages, which re-runs the same fail-closed
  verifiers before it serves anything.

**Release and publication**

- [`scripts/eif_release.py`](scripts/eif_release.py): builds the sdist and
  wheel, validates both the way a package index will (`twine check --strict`,
  installed into a throwaway environment rather than required on the host),
  installs the built wheel into a clean virtualenv and runs `eifctl version`
  from it. It prints the publish commands and stops. Publication takes owner
  credentials and stays an owner decision, which is the same boundary
  everything else here observes: EIF generates what a person then chooses to
  run. Passes end to end.
- [`docs/product/linkedin-series.md`](docs/product/linkedin-series.md): the
  rules everything published about EIF is written under. Audience, claim
  boundaries, voice rules, commenting rules, and the sentences the series
  may never write regardless of how well they would perform. It sits beside
  the claims register deliberately: a post is a public claim, so it is held
  to the same forbidden-wording list the site build enforces. The drafts it
  governs are private, and the file says why. The short version is that
  comment history holds named third parties' arguments, and putting those in
  a public repository without their knowledge is a privacy problem rather
  than a matter of taste.
- The site's quickstart carries a command block per platform: macOS/Linux/WSL,
  Windows PowerShell and Windows CMD, behind a tab strip, split into two
  numbered steps because only the first one differs per platform. It answers
  what the screen was actually being asked - where do I paste this, what is
  that lone `.`, and what happens on my OS - and it states the one shell
  difference a reader would otherwise hit as an error, that Windows
  PowerShell 5.1 parses `&&` as a parser error. Every command was run before
  it was published: a clean 3.11 virtual environment, `pip install .` from
  the clone, then `eifctl init` into a fresh directory, which initialized an
  instance and reported in the locale its config declared. All three panels
  ship in the static markup and stay open without JavaScript, each under its
  own heading, so the no-script path is the complete one rather than a strip
  that cannot switch.
- `site/.env.production`, committed: the two owner-supplied production inputs
  (`EIF_SITE_URL`, `EIF_REPOSITORY_URL`) in one file rather than in one
  machine's shell, so a production build is reproducible from a clean
  checkout and moving hosts is a one-line change. Both values are public by
  definition - they are emitted into the shipped HTML - so nothing secret is
  committed. `verify:bundle` now fails on any `__EIF_*__` marker that
  survived into `dist/index.html`, because the first of those markers a
  reader meets is the `git clone` line.
- `scripts/tests/smoke.py` fails when the installable package's bundled
  copies drift from their sources. The only sync check lived in the manual
  release gate, so a documentation-only change never reached it - see Fixed.
- `.github/workflows/pages.yml` publishes the site to GitHub Pages on any
  change under `site/`. It runs the three fail-closed verifiers and nothing
  else: no Playwright, no Lighthouse, no axe, because those are the local
  gate and re-proving them in CI would buy nothing. What it does enforce is
  what must never reach a public page - an unknown claim ID, forbidden
  wording, a leaked private path, a third-party runtime request, a missing
  metadata marker or a surviving `__EIF_*__` build marker. It contradicts
  D-14's "push to main triggers no workflow", so the boundary is recorded
  as D-15 rather than left for a reader to discover: D-14 governs
  validation topology and this job runs no test.
- `.github/social-preview.png`, 1280x640, generated by
  `npm --prefix site run generate:social-assets` from the same brand source
  as the site's own card, for the repository's Social preview setting.
  Written outside `site/public/` because the site never serves it. The
  release card identifies `v0.1.0`; it no longer carries the stale
  `pre-release` label.
- Repository-level release controls: `main` branch protection requires the
  consolidated PR smoke context and prevents force-push/deletion, while
  Discussions, private vulnerability reporting, dependency alerts, secret
  scanning, and the evidence-report label are enabled for public intake.
- `CITATION.cff`, so GitHub exposes a machine-readable “Cite this
  repository” entry for the framework and version.
- The site's quickstart states that the instance locale defaults to English.
  The reference walkthrough declares Ukrainian on purpose, which was easy to
  read as the default; verified by running `eifctl init` with no `--locale`,
  which writes `locale: en`. The three `eifctl init` arguments are a
  definition list now instead of one sentence holding all three.
- Every drawn object on the site that means something names itself on hover,
  in whichever language the page is showing: what the framework layer holds,
  why the promotion route is dashed, which segment of the capabilities figure
  leaves the machine, why a superseded artifact stays readable but out of
  results. The text lives on the shape inside the i18n block, so each
  language template carries its own copy. Pointer-only on purpose: every
  figure already has a written key with the same content, so the shapes stay
  out of the tab order rather than adding forty stops that tell a
  screen-reader user nothing new, and the tips are suppressed entirely on
  touch where they would flash and sit under a finger.
- Site now describes the knowledge base itself - front matter and
  `related:` links as the graph, a generated index searched offline, the
  status lifecycle that keeps rejected and superseded artifacts out of
  retrieval, three distinct failure outcomes, and the curator as its
  maintenance pass - with a figure of one query walking that graph.
- The control-plane sequence and the token-cost statement gained figures in
  the same visual language: one pass from intent to durable knowledge with
  each station lighting as it arrives, and command output filtered before
  it reaches the model with the unfiltered core path drawn underneath. No
  quantity is shown for the second, because none may be claimed.

### Changed

- The two figures at the top of the page swapped places. The hero carried a
  circuit diagram with a five-line key, which asks to be studied before a
  reader has any reason to; it is now the orbit mark, symmetrical and
  unkeyed, because a hero is a poster. The circuit moved to section 03,
  where its key belongs and where the prose is already about exactly what it
  draws. Two collisions came with the swap and are fixed: `.hero__figure`
  now exists in both places, so the pause behaviour is scoped to the hero or
  scrolling past would freeze the section 03 circuit while it is being read,
  and the hero figure now sits inside an i18n block, so its
  IntersectionObserver disconnects its predecessor instead of leaking one
  per language toggle.
- The evidence ledger is current again, and one row longer. The install row
  led with "not published to PyPI", which is release status rather than
  evidence; it now leads with the command that works, `pip install .` from a
  clone, and keeps only the bounds on the evidence itself. The switching row
  says adapter scope is frozen at four rather than describing two of them as
  pending. The "Bounded proof on record" block that trailed the section is
  folded into an eighth row, `Measure`, so the pilot's two limits sit beside
  the pilot instead of reading as a disclaimer appended to a page of claims.
  CLM-08, CLM-09 and CLM-10 all still resolve, which the strict claims gate
  proves.
- The capabilities figure is composed like the knowledge-base block in
  section 07: explanation and legend on one side, drawing capped at 24rem on
  the other, rows spanning both. Full width had been the wrong correction.
  The drawing is three thin lanes, so stretching it opened a gap down the
  middle of each one and stranded the legend underneath, which read fine on
  a phone and badly on a laptop.
- The closing screen leads with what the repository is rather than with an
  adjective about how it is developed: the public extraction of a private
  framework in daily use on real projects, across different agents and
  models, where the models change and the governance around them does not.
  Two notes carry the mechanism behind that, the two layers experience
  accumulates in and why adapters exist, stated as mechanism rather than as
  an outcome claim nothing here has measured.
- The site's release-status notes moved off the site, into
  [`docs/product/release-status.md`](docs/product/release-status.md). The
  quickstart used to spend a heading, a lede clause and a closing paragraph
  arguing about whether this is a release. The command it prints is
  `pip install .`, which works from a clone, and the page never printed the
  package-index form that would fail for a reader, so those notes were not
  protecting anyone. An end-to-end test asserts both facts: the failing
  install form never appears, and the removed notes stay removed.
- The optional-capabilities section now answers the boundary question in its
  default state. Whether an integration leaves the machine was the opening
  clause of a paragraph inside a collapsed disclosure; it is a `Local` or
  `Network` tag on each row, amber for the one that goes to the network,
  matching that tool's lane in the figure directly above. The figure moved
  out of a 24rem column into full width, its legend went from three
  paragraphs to four one-line keys, and the amber rule that had been
  bracketing a drawing and a caveat together now brackets only the caveat.
- The Ukrainian on that section was translated rather than written, in a way
  a reader would notice: a heading calqued word for word, "по одній
  обмеженій спроможності", "Керованість не безкоштовна в токенах", and a
  feminine "Без неї" standing in for three masculine tool names. Rewritten
  against the English line by line.
- Disclosure rows on the capabilities list and the evidence ledger show a
  caret, so a row that opens looks like one. Drawn only when the enhancement
  is active, since the no-JS path is already expanded.
- The closing screen says what is below it instead of performing an
  attitude about it. "Right now disagreement is worth more to me than
  agreement, so the second column is not decoration" was telling a reader
  how to feel about a contact column. On-page destinations carry the page's
  own section numbers rather than repeating "on this page" down a column,
  and each destination now sits next to its purpose line instead of 44px
  above it.
- The site says how to install rather than that you cannot. `pip install .`
  followed by `eifctl init` is the quickstart command now, which is the path
  the installed-wheel suite has been exercising all along, and the caveat is
  narrowed to the one thing that is actually missing: publication to an index.
- The optional-capabilities section was carrying the same three facts three
  times over: a flow figure with its legend, a bridge table, and three
  expandable rows with the real detail. The bridge table is gone, and the
  two-paragraph measured/not-measured accounting beside it is now one clause
  in the cost statement, which is where the honesty was load-bearing and the
  accounting was not.
- "Leaves the machine" is now "goes to the network" in both languages. The
  Ukrainian rendering of it was not idiomatic, and the phrase had spread to
  four places.
- The closing screen was three underlined links, a floating status line, a
  100px hole and a contact block bolted underneath, all at different measures.
  It is one grid now: two matched columns of destinations, each row saying
  what it is, where it goes and one line of why you would. The footer no
  longer announces "local build, not yet deployed", which was a note to the
  person building the site rather than to the person reading it.
- The two knowledge directions under the layers are written as plain
  sentences in both languages instead of clauses hung off dashes.
- The site's standalone Limitations section is gone, and its two load-bearing
  statements moved to where the claims they qualify are actually made: the
  no-quality/no-rework claim now sits in the bounded-proof list beside the
  pilot it qualifies, and the no-package-index caveat sits in the quickstart
  beside the command it applies to. A limits section read as a disclaimer
  page; a limit next to its claim reads as part of the claim.
- The site ends in a way a reader can act on. The repository call to action
  carries the same label in both states and in the reader's own language,
  with the pre-publication caveat on its own line instead of in brackets
  inside the link text, and the page closes with two contact channels rather
  than three on-page anchors.
- The evidence loop's figure and its contract block were drawn as if they
  came from a different site: labels at roughly 19 rendered pixels where
  every other figure annotates itself between 10 and 13, and a
  Preconditions/Exits table whose two headings were the quietest elements in
  their own columns while six decorative accent-green terms were the
  loudest. Both are now in the page's own weights, the accent appears only
  where PASS/BLOCKED/DEFERRED actually mean something, and the figure gained
  an amber exit mark so a ring finally says the loop is bounded.
- Fixed the traced-packet figure's session handoff: the packet-memory dot ran
  past its own destination onto session 2's work segment and stopped dead on
  the exact point the promotion dot started from, so one dot appeared to
  freeze, vanish and reappear in place. The bridge between the two sessions
  is also symmetric now instead of leaning left.
- The four outcome columns under that figure no longer tint their own rules,
  which had made "At closeout" look promoted above its three neighbours for
  a reason nothing on the page stated. Each column carries the marker of the
  thing it describes instead, in the page's existing legend vocabulary.
- Fixed the hero key: `sections.css` loads after `hero.css`, so the shared
  legend component's own padding and max-width were winning - the rule sat
  1px above the first line of the key and ran 48px wider than the figure it
  captions.
- The two knowledge directions under the layers now read as a matched pair.
  The up direction says what happens to the knowledge that is not promoted,
  and no longer loses a paragraph's worth of height to a stretched grid row.
- Ukrainian copy: the knowledge base is described by what its links do rather
  than by naming the front-matter field in English, and the quickstart says
  why the reference run closes in Ukrainian - the language is configuration,
  not a hardcoded default.
- The site's own privacy scanner read the "s" in `https://` as a Windows
  drive letter, so the first outbound link the site ever carried was
  reported as a leaked machine path.
- Site terminology finished the layer rename: the last `tier` class names
  in the site's markup, styles and tests are now `layer`, so nothing in the
  repository calls the context model a tier. "Tier" survives only where it
  genuinely means a ranking - the authority model and adapter capability
  levels - which is why the two were kept verbally distinct in the first
  place.
- Site figures rebuilt to carry the model rather than decorate it: the hero
  mark now runs retrieval down, one packet of three sessions across, and a
  rare promotion up, with the curator on its own period; the traced-packet
  figure gains a second retrieval into session 2, gate pulses and work
  drawn as it happens; the multi-project figure is paired with its
  explanation, animates four beats in causal order, and appears in both
  languages. Both language templates carry every figure now.
- Site copy: what flows down the layers is named as the whole operating
  layer rather than "method"; the traced-figure caption reworked in both
  languages; "before implementation" used consistently in place of "before
  the work".

- One legend component now serves every figure, with markers optically
  centred on their first line and drawn at the weight they have in the
  figure they explain, so a key never outweighs its drawing. Em and en
  dashes removed from the site and the repository.
- Figures carry labels on their own lines, not only a legend beside them.
- Fixed a label that rendered with a stroke as well as a fill, which read as
  an out-of-focus caption rather than a de-emphasised one.
- Site figures now explain themselves. Each carries a short legend in the
  reader's language whose markers match the drawing, so the figures read as
  diagrams rather than decoration; the SVGs stay text-free and single-copy.
  Ukrainian copy reworked where it said "робота" for a scoped task and
  "метод" for the whole framework layer, and the optional capabilities are
  no longer called accelerators.

### Fixed

- The vendor-docs integration suite now emits the standardized
  `EIF-RESULT: passed=P total=T` footer. Its 63 checks were passing, but the
  exact-inventory release gate correctly treated the suite as `unknown`
  because prose-only `63/63` output is not machine-trustworthy.
- CI's own frontmatter validation was failing, and had been since the two
  files that break it were added. `docs/product/release-status.md` and
  `docs/product/linkedin-series.md` carried `type: reference` and
  `status: active`, neither of which exists in the ontology, and CI
  validates `docs/product/*.md`, so the single required PR job could not
  pass on any pull request. Typed honestly instead: `fact` for the one that
  states where the release stands, `rule` for the one that says what a post
  may and may not claim, both `OBSERVED` from code, because the second
  one's forbidden-wording list is the list `site/scripts/verify-claims.mjs`
  actually enforces rather than an aspiration.
- The site's repository CTA went nowhere outside a production build.
  `EIF_REPOSITORY_URL` was production-gated, so dev and preview resolved
  the closing screen's one outbound destination to an on-page anchor and
  printed "the repository link is added at publication" beneath it. Right
  while publication was an undecided owner call; a dead link and a false
  caption once the repository is public. The URL is a project constant now,
  resolved in every mode and still overridable per build, and the pending
  line is removed rather than left permanently empty.
- The installable package was missing two of its own declared resources.
  `docs/product/linkedin-series.md` and `docs/product/release-status.md` are
  inside a tree that `scripts/sync_package_sources.py` bundles into the
  wheel, and neither had ever been copied - a wheel built before this would
  have shipped without them. The drift survived because the only sync check
  lived in the manual release gate, which a documentation-only change never
  reaches; `scripts/tests/smoke.py` now runs that check in the fast loop,
  and `AGENTS.md` names the trees that need a re-sync after an edit.
- The site's social-image URLs were relative on any host with a deployment
  sub-path. Vite rebases root-relative asset paths against `base` before the
  metadata plugin runs, so the plugin's literal `/social-card.png` match
  found nothing and shipped a path no crawler could resolve. Only a
  root-domain site URL ever hid it. Matched on filename now, and
  `verify:bundle` caught it the first time a project-page URL was set.
- A clicked node in the site's evidence-loop diagram left a pale rectangle
  around itself. Chromium does not match `:focus-visible` on an SVG group
  clicked with a mouse, so the rule meant to suppress the browser's own ring
  never fired, and the ring was drawn around the group's bounding box -
  which includes the label sitting below the dot. Suppressed on `:focus`;
  the keyboard indicator is unchanged.
- Four Ukrainian tooltips read as unadapted translation rather than as
  Ukrainian: a session whose reasoning "переживає її лише перевірене", a
  packet closing before "набуте пропонують нагору", and a curator that
  "нічого не зливає" twice, where the English says it merges nothing.
- `docs/README.md` listed a `concepts/` directory that does not exist and
  omitted `architecture/instance-contract.md`,
  `architecture/merge-enforcement.md` and the whole `research/` tree.

### Known limitations

Stated here rather than left to be discovered:

- **Not on PyPI.** No `pip install` from a package index.
- **No quality or rework claim.** No comparative study has been run.
- **The benchmark is one bounded run**: one model, three of ten fixtures,
  one attempt per A/B cell, six attempts total. Modes C/D have executable
  integrity contracts but no real-agent result. This cannot support a
  directional efficiency claim.
- **No second-party review requirement.** Branch protection technically
  requires the consolidated PR check and prevents force-push/deletion, but
  this remains a single-maintainer project and no adapter ships a hook guard
  against invoking a merge outside the supported wrapper.
- **Pre-release history contains a retired private identifier.** The current
  tree passes the privacy scan and commit `c64baaa` removed the identifier
  from all four affected files, but older public commits remain reachable.
  Rewriting that history is a separate destructive owner decision.
- **Cursor runtime consumption is unconfirmed.** The generated rule file is
  code/test-validated, but no human has verified that Cursor's agent
  actually reflects its content - see
  `examples/demo-cursor-workspace/MANUAL-RUNTIME-CHECK.md`.
- **Vendor-docs is not probed.** EIF generates configuration for an agent
  to load and does not itself speak MCP, so transport reachability is
  reported by the agent and marked unverified in the manifest.
- **EIF installs nothing at the user level.** Not a limitation so much as a
  deliberate boundary: MCP servers and agent hooks are configured outside
  the project instance, and this framework never mutates user-level
  configuration.
- **Existing-governance detection is a heuristic**, a content-length check
  rather than semantic understanding, and can both over- and under-trigger.
- **Retrieval is keyword-based**, not semantic, and is untested against a
  realistically large knowledge base.
- **Adoption is proven against one real target.** A second, different real
  repository has not been exercised.
- **Localization covers project surfaces**, not an agent's own free-form
  responses.

### Explicit non-goals for 0.1

Hosted SaaS, an autonomous multi-agent runtime, a proprietary cloud memory
service, a mandatory code-graph or shell-compression dependency, and any
universal token-savings claim.

[Unreleased]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases/tag/v0.2.2
[0.2.1]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases/tag/v0.2.1
[0.2.0]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases/tag/v0.2.0
[0.1.3]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases/tag/v0.1.3
[0.1.2]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases/tag/v0.1.2
[0.1.1]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases/tag/v0.1.1
[0.1.0]: https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases/tag/v0.1.0
