---
type: playbook
status: validated
scope: framework
created: 2026-08-02
review_after: 2026-11-02
---

# Professional profile creation

<!-- Knowledge source: owner-requested professional profile workflow, 2026-08-02. -->

Create a professional profile only for recurring work that is not already
covered by core EIF or by one project's local instructions. A job title alone
is not evidence that another process is needed.

## 1. Confirm the destination

Work only in a private EIF workspace containing `.eif/workspace.yaml`.
Public EIF contains starter profiles; installed and custom profiles are
workspace-owned L2 content. Never place a person's private projects, brand
assets, client names or machine paths in the public catalog.

## 2. Define the gap

Name the repeated professional outcome, its inputs, decisions, failure modes
and evidence of completion. Check the active EIF skills and playbooks first.
If the proposed profile merely restates planning, implementation, verification
or Knowledge Delta rules, do not create it.

## 3. Choose the smallest artifact set

Use `workspace/profiles/<name>.yaml` and only the artifacts needed:

- a playbook for the reusable process;
- a thin skill for each materially different user request that must trigger it;
- templates for structured inputs or delivery evidence;
- a rule only for a real non-negotiable constraint;
- knowledge only when it is verified and reusable across connected projects.

Use `required` for a constraint that cannot be skipped, `default` for the
normal path and `optional` for explicitly selected support. Do not add several
skills that only rename adjacent steps of one process.

## 4. Keep sources single and explicit

Place artifact sources below the workspace content root declared in
`.eif/workspace.yaml`. Skills should point to the workspace-runtime playbook or
template instead of copying its body. Keep personal preferences and project
facts out of a cross-project profile.

## 5. Validate before connection

Run `eifctl workspace doctor --workspace-path <workspace>`. Review and commit
the workspace. Assign the profile only to projects the owner identifies, then
run the fleet dry-run before `--apply`. Start a new agent session after
materialization so the selected skills are discovered.

Treat the first real use as a bounded trial. Retain what improved the verified
outcome; remove ritual that produced no useful difference.
