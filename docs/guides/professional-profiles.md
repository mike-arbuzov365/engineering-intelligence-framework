---
type: playbook
status: validated
scope: framework
created: 2026-08-02
review_after: 2026-11-02
---

# Professional profiles

A professional profile is a reusable private-workspace selection of rules,
skills, playbooks, templates and shared knowledge for a recurring discipline.
It is not a new EIF layer and it is not the agent harness.

Public EIF ships starter profiles. Installation copies a starter into the
private workspace, where it becomes user-owned and will not be overwritten by
future releases.

## Available starters

- `graphic-design`: brief, direction approval, production review and delivery;
- `software-development`: repository onboarding only, because core EIF already
  governs normal planning, implementation, verification and learning.

List and install them:

```bash
eifctl workspace profile list
eifctl workspace profile install graphic-design \
  --workspace-path ../designer-eif
```

The installer validates the public manifest, refuses conflicting local files
and writes no project. Review and commit the private workspace after install.

## Designer laptop setup

1. Install the current EIF release wheel and the chosen supported agent.
2. Create a private workspace:

   ```bash
   eifctl workspace new ../designer-eif \
     --workspace-name designer-eif \
     --adapter codex \
     --locale uk
   ```

3. Review and commit the workspace bootstrap. Install `graphic-design`, review
   the files, then commit that change.
4. Initialize or adopt each exact designer project, then register it with the
   selected profile:

   ```bash
   eifctl init ../design-project --adapter codex --locale uk
   eifctl projects add ../design-project \
     --profile graphic-design \
     --registry ../designer-eif/.eif/projects.yaml
   ```

   For a new project, creation and registration can be one operation. EIF
   checks that the profile exists before it creates the directory:

   ```bash
   eifctl new ../design-project \
     --adapter codex \
     --locale uk \
     --profile graphic-design \
     --registry ../designer-eif/.eif/projects.yaml
   ```

5. Commit the registry change in the private workspace. Run the fleet plan,
   then apply it:

   ```bash
   eifctl projects upgrade \
     --registry ../designer-eif/.eif/projects.yaml
   eifctl projects upgrade \
     --registry ../designer-eif/.eif/projects.yaml \
     --apply
   ```

6. Start a new agent session in each project so it loads the selected skills.

Machine paths remain in the ignored local locations file. When a private
workspace is cloned to another laptop, run `eifctl projects add <local-path>`
for each project to restore that machine's mapping; do not commit those paths.

## Create a custom profile

Ask the agent to use `create-professional-profile`. It checks core EIF first,
creates only the missing professional process, validates every profile with
`eifctl workspace doctor`, and does not connect unidentified projects.

Start with a real repeated task. A job title by itself is not enough reason to
add rules, and a profile that only restates core EIF should not exist.
