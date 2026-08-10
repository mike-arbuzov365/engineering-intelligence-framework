# Graphic design project

The process protects the brief, decisions and verification without imposing a
visual style or a particular design tool.

## 0. Choose the size of the process

- **Light task**: one bounded edit, resize, export or check; the requested
  output, constraints and approval are clear; risk is low; the result can be
  checked directly. Do not force a full brief or delivery form. Confirm the
  objective, output, channel and important constraints, retrieve relevant
  project knowledge, use only the applicable checks and finish with a learning
  check.
- **Structured single task**: a new deliverable or meaningful change that
  needs a written brief, direction decision or recorded delivery checks. Use
  the process below and the templates that are actually needed.
- **Execution packet**: multiple sessions or deliverable families, a disputed
  direction, important rights or production risk, or unattended work. Plan the
  packet first, then use this playbook inside its sessions.

A short prompt does not automatically mean a light task. Missing approval,
unclear rights or irreversible production cost moves the task to a structured
path even when the requested edit looks small.

## 1. Establish the brief

Complete `templates/design-brief.md`. Stop and clarify when the objective,
audience, deliverables, channels, mandatory elements, acceptance criteria or
decision owner are unknown.

Keep four things separate: approved requirements, verified channel facts,
designer assumptions and stakeholder preferences. Do not invent missing brand
rules; record the gap or propose a decision for approval.

## 2. Validate inputs

Check the current logos, fonts, palette, copy, images, usage rights and channel
requirements. Prefer original or approved source assets. Do not treat an old
chat attachment as authoritative when its source can be checked.

## 3. Select a direction

When no direction is approved, prepare a small number of meaningfully different
directions and explain how each supports the brief. Do not create variations
only to increase the count.

Start final production after an explicit direction choice. Record who approved
what and which concerns remain open. Direction approval is not final-delivery
approval.

## 4. Produce and review

Work from editable sources to derived exports. Name the purpose of each review:
brief alignment, composition, readability, brand consistency, technical limits
or a specific comment. Do not collapse every question into “like/dislike”.

Before delivery, run only checks relevant to the brief:

- dimensions, format, colour mode and transparency;
- unintended crops, font substitutions and unresolved links;
- readability at the target size and background;
- consistency across a series;
- permission to use fonts, images and other third-party material;
- accessibility with a real checking method when the brief requires it.

Зафіксуйте `QA scope` як `changed_only` або `full`. `changed_only` допустимий
лише для localized change без зміни shared font, palette, brand rule, layout
system, export setting, rights або cross-deliverable input. Якщо shared/global
input змінився, dependency невідома, change охоплює кілька deliverable
families або може вплинути на final package, виконайте `full` QA. Це explicit
classification, не automatic dependency engine.

## 5. Deliver and retain learning

Перед package або final delivery виконайте fail-closed guard:

```text
eifctl delivery check --action <package|final_delivery> --scope <exact-scope> --instance-path .
```

Nonzero result блокує EIF-managed action. Approval state є project-local,
default `package_allowed: false`; arbitrary external shell/export command не
має machine enforcement без окремого verified adapter guard.

Complete `templates/design-delivery.md` with editable sources, exports, checks,
known limits and approval state. A preview alone is not a completed delivery.

Run a learning check on every path. Propose only reusable learning to project
memory: approved brand decisions, verified channel requirements, approved
directions, durable rights or production constraints, repeated errors and
lessons that should change later work.

Keep one-off subjective changes, unapproved directions and agent assumptions in
the task or project history. A light task does not need a Knowledge Delta when
no reusable knowledge surfaced. When it did, use the EIF `knowledge-ingest`
skill and name the memory artifact changed. Structured work uses the normal EIF
Knowledge Delta and closeout.
