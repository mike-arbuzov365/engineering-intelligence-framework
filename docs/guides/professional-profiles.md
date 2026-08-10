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

In this guide, **agent harness** means the active combination already assembled
for one project: the generated persistent agent instruction, adapter, selected
professional profile, discoverable skills, project memory and verification.
It is a useful name for the whole working context, not a new file, schema or
configuration layer. `eifctl doctor` reports that context after validating it.
This makes activation inspectable; it is not evidence that the instruction
improves design quality. D-19 still requires the same task to be compared with
and without the instruction under matched conditions before making that claim.

Public EIF ships starter profiles. Installation copies a starter into the
private workspace, where it becomes user-owned and will not be overwritten by
future releases.

## Available starters

- `graphic-design`: bounded everyday work plus brief, direction approval,
  production review and delivery for larger projects;
- `software-development`: repository onboarding only, because core EIF already
  governs normal planning, implementation, verification and learning.

Professional profile лишається canonical grouping unit для its skills,
playbooks і templates. Кожен bundled starter skill має local
`tests/contract.yaml`, який materializes у private workspace і далі у pinned
project runtime разом із skill directory. Adapter loader читає лише selected
`SKILL.md` і не injects test fixture у normal model context.

Current source candidate перевіряє всі 12 core і 3 starter-profile contracts:

```bash
eifctl skills check
```

Це model-free structural/grounding check, не evidence, що skill покращує
design або software outcomes. External skills не встановлюються; admission
policy описано в
[`docs/reference/external-skill-admission.md`](../reference/external-skill-admission.md).

List and install them:

```bash
eifctl workspace profile list
eifctl workspace profile install graphic-design \
  --workspace-path ../designer-eif
```

The installer validates the public manifest, refuses conflicting local files
and writes no project. Review and commit the private workspace after install.

## Designer laptop setup

The public EIF repository does not need to be cloned for normal use. Download
the wheel attached to the [current GitHub release](https://github.com/mike-arbuzov365/engineering-intelligence-framework/releases),
install that local file, and verify the command:

```bash
python -m pip install ./engineering_intelligence_framework-<version>-py3-none-any.whl
eifctl version
```

Clone the public repository only when the owner intends to develop EIF itself.
The private workspace created below is the designer's own local EIF repository.

1. Install the current EIF release wheel and Codex.
2. Create a private workspace. Start outside the intended workspace directory
   and pass a target path that does not exist yet. An already-created empty
   directory is also refused because EIF verifies a temporary sibling tree and
   then moves that finished tree into place atomically:

   ```bash
   eifctl workspace new ../designer-eif \
     --workspace-name designer-eif \
     --adapter codex \
     --locale uk
   ```

3. Review and commit the workspace bootstrap. Install `graphic-design`, check
   the resulting workspace, review the files, then commit that change:

   ```bash
   eifctl workspace profile install graphic-design \
     --workspace-path ../designer-eif
   eifctl workspace doctor --workspace-path ../designer-eif
   ```

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
   Run this inside the project once at the start of that session:

   ```bash
   eifctl doctor --instance-path .
   ```

   A healthy Codex project reports `AGENTS.md`, profile `graphic-design`, the
   profile skills and the project memory location. On a project with no durable
   knowledge yet, a managed index is reported as deferred. This is healthy: the
   `knowledge-ingest` workflow creates the first knowledge artifact and
   regenerates the index together instead of creating an empty memory stub at
   setup time.

7. Перед EIF-managed package або final delivery owner створює project-local
   approval state за starter template
   `.eif/workspace-runtime/templates/design-package-approval.yaml`. Copy
   зберігається у ignored
   `.eif/local-state/design-delivery-approval.yaml`; default лишається
   `package_allowed: false`. Потім exact action і scope перевіряються:

   ```bash
   eifctl delivery check \
     --action package \
     --scope <exact-delivery-scope> \
     --instance-path .
   ```

   Nonzero result блокує EIF-managed action. Цей command не intercepts
   arbitrary external ZIP, export, upload або shell command. Без окремого
   verified adapter guard така ширша заборона є `instruction_only`.

   Для localized change запишіть `QA scope: changed_only` разом із changed
   inputs/outputs, rationale та checks. Зміна shared font, palette, brand rule,
   layout system, export setting, rights, кількох deliverable families або
   unknown dependency потребує `full` QA. Це explicit classification, не
   automatic dependency engine.

Each connected path is a project repository, not a broad asset library. Keep
images, fonts and editable sources in the project or its approved asset system;
store decisions and reusable lessons in EIF project memory, not binary assets.
Turn a plain folder into a repository only with its owner's approval.

Machine paths remain in the ignored local locations file. When a private
workspace is cloned to another laptop, run `eifctl projects add <local-path>`
for each project to restore that machine's mapping; do not commit those paths.

## One-time Codex setup prompt

Use this prompt in a Codex session outside the projects when setting up a new
designer laptop. Replace only the paths; the agent should read the guide rather
than rely on copied framework rules:

```text
Set up the current released EIF for a graphic designer who uses Codex.
Follow this guide as the source of truth:
https://github.com/mike-arbuzov365/engineering-intelligence-framework/blob/v<eifctl-version>/docs/guides/professional-profiles.md#designer-laptop-setup

Use the wheel from the current GitHub release, not PyPI, and use the guide from
the matching release tag. Start outside <workspace-path>; that target must not
exist yet, including as an empty directory. Create a private workspace there,
install the graphic-design professional profile, and connect only these exact
project repositories: <project-paths>.

Before writing, inspect the paths and existing Git state. Do not connect broad
asset folders, overwrite existing project instructions, create remotes or push
anything. Initialize or adopt each approved project with the Codex adapter,
register it with profile graphic-design, apply the workspace snapshot, then run
the workspace doctor and each project's eifctl doctor. Report the active
instruction, profile, profile skills, project memory and anything that still
needs an owner decision. Treat a managed memory index reported as deferred as
healthy when no durable project knowledge exists yet.
```

This prompt is needed only for bootstrap because no project instruction exists
yet. After setup, Codex automatically reads the generated `AGENTS.md` whenever
a session starts inside the project. EIF also exposes the selected skills in
Codex's discovery directory, so ordinary design prompts do not need to repeat
the framework process.

Do not copy the full EIF rules into Codex personal memory: that creates a stale
second source. If a personal reminder is desired, keep only this pointer:

```text
Inside an EIF project, follow its AGENTS.md and verify the active project
context with eifctl doctor at the start of a fresh session.
```

## Create a custom profile

Ask the agent to use `create-professional-profile`. It checks core EIF first,
creates only the missing professional process, validates every profile with
`eifctl workspace doctor`, and does not connect unidentified projects.

Start with a real repeated task. A job title by itself is not enough reason to
add rules, and a profile that only restates core EIF should not exist.
