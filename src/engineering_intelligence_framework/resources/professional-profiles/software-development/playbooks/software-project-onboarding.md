# Software project onboarding

This profile adds repository onboarding only. Planning, implementation,
verification, review and learning continue to use the core EIF workflows.

## 1. Establish authority and scope

Read the active agent instruction file, project configuration and pinned EIF
artifacts. Identify the repository's purpose and the requested work boundary.
Do not infer deployment or production authority from local source access.

## 2. Map the repository

Locate application entry points, major components, tests, build configuration,
deployment configuration and durable project documentation. Separate observed
facts from inferred relationships and unresolved questions.

Use structural navigation tools when available, but verify every graph-derived
claim against source before recording it or changing code.

## 3. Verify native commands

Find commands in repository-owned configuration or documentation. Run the
smallest safe form needed to prove the build, test, formatting and static-check
surfaces. Record the exact command, result and relevant environment boundary.
Do not invent a command from ecosystem convention and present it as observed.

## 4. Record the baseline

Complete `templates/software-project-baseline.md`. Put compact, stable agent
instructions below the EIF-managed marker in the project's active instruction
file. Put verified, reusable project facts in project knowledge. Do not record
secrets, credentials or machine-specific paths.

## 5. Verify onboarding

Run `eifctl doctor --instance-path .`, the relevant native project check and the
privacy scan before committing onboarding material. Open questions remain open;
onboarding does not require pretending the whole architecture is understood.
