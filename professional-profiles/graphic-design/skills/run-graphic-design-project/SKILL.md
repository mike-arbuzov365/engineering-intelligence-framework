---
name: run-graphic-design-project
description: >
  Route and execute graphic-design work, from a small bounded edit, resize or
  export through a full brief, direction, production and delivery flow. Use
  when creating or modifying identity, campaign, print, social, presentation
  and other graphic-design deliverables; choose the lightest safe path.
---

# Run a graphic design project

1. Read `.eif/workspace-runtime/playbooks/graphic-design-project.md`.
2. Classify the work as light, structured single task or execution packet. Do
   not create a full brief, delivery form or packet for a genuinely light task.
3. On the light path, confirm the objective, output, channel and important
   constraints; retrieve relevant project knowledge; run only applicable
   checks; then perform the learning check.
4. On the structured path, create or verify the brief with
   `.eif/workspace-runtime/templates/design-brief.md`. Do not begin final
   production until inputs, constraints, acceptance criteria and the direction
   decision owner are known. Close with
   `.eif/workspace-runtime/templates/design-delivery.md`.
5. Record reusable learning through the normal EIF knowledge process. Do not
   promote a stakeholder's one-off preference, an unapproved direction or an
   agent assumption into project memory. Use `knowledge-ingest` when durable
   learning surfaced; otherwise do not create a memory artifact.
6. Перед `package` або `final_delivery` виконайте `eifctl delivery check` з
   exact scope. Nonzero result блокує EIF-managed action; external shell/export
   лишається `instruction_only` без verified adapter guard.
