# Security Policy

## Reporting a vulnerability

Please do not open a public GitHub issue for security or privacy concerns.

Use the repository's
[private vulnerability reporting form](https://github.com/mike-arbuzov365/engineering-intelligence-framework/security/advisories/new)
(`Security` -> `Advisories` -> `Report a vulnerability`). Private reporting
is enabled, so the report and any follow-up remain visible only to the
reporter and repository maintainers until coordinated disclosure.

Include:
- A description of the issue and its potential impact.
- Steps to reproduce, if applicable.
- Any relevant logs, config, or version information (redact secrets before
  sharing).

## Threat model

**EIF core (this repository's ontology, playbooks, templates, and skills)
does not transmit code or data anywhere.** It is plain files that run
inside your own environment, read by an agent you already trust with your
repository. There is no hosted service, telemetry backend, or cloud memory
store in EIF core.

**Optional integrations may have a different data boundary.** Each
integration in [`integrations/`](integrations/README.md) declares its own
`data_boundary` (`local-only` or `external-api`) in
[`.eif/config.yaml.example`](.eif/config.yaml.example) - `external-api`
means that integration sends queries (not necessarily your source code,
but verify per-provider) outside the local machine. Do not assume an
integration is local-only without checking its declared boundary and the
actual provider's behavior; a declared boundary that doesn't match
observed behavior is itself a security bug, not a documentation nitpick.

**Graphify raw graphs are local artifacts, not public evidence.** Generated
instances ignore `graphify-out/`; the adapter rejects absolute paths, parent
traversal and artifacts outside that directory. A structural graph can still
contain private identifiers and relationships, so do not commit or paste it
into reports. Semantic/deep mode is external processing and fails closed unless
the config names a provider, declares `external-api`, and sets a positive cost
cap. `eifctl doctor` validates that gate but never starts the paid scan.

**Generated adapters and hooks run with the same permissions as the agent
they're installed for.** A hook that can rewrite or block a shell command
can, in principle, also be a vector for unintended command execution if
its rewrite logic is wrong. Adapter code should be reviewed like any other
code with execution privileges, not treated as "just config."

**Do not assume hook enforcement is reliable across agents or versions.**
This framework's own dogfooding found hook rewrite instructions silently
ignored by one agent in roughly half of observed cases over several days.
Do not build a security-relevant control (e.g. "this hook blocks dangerous
commands") without verifying it actually fires, per agent and per version,
end to end.

## In scope

- A generated hook, adapter, or script that could execute unintended
  commands or leak data outside its declared boundary.
- A documented pattern that, if followed, would encourage storing secrets
  in tracked files or committing them to version control.
- A privacy-relevant check (see [`scripts/eif_privacy_scan.py`](scripts/eif_privacy_scan.py))
  that has false negatives on a realistic private-data shape.
- Supply-chain concerns in any scripted dependency installation.
- An integration whose declared `data_boundary` doesn't match its actual
  behavior.

## Supply chain

- Scripts in this repository should not pipe a remote URL directly into a
  shell (`curl ... | sh` or equivalent) - fetch, review, then execute.
- Any script that installs a dependency should pin a version, not float on
  `latest`.
- Third-party attribution and license tracking for anything vendored or
  closely adapted belongs in a `NOTICE` file once this repository actually
  vendors something (none yet).

## Private vulnerability reporting

GitHub private vulnerability reporting is enabled for this public
repository. Do not include vulnerability details in a public issue or
discussion; use the private form linked above.

## Automated checks

[`scripts/eif_privacy_scan.py`](scripts/eif_privacy_scan.py) scans tracked
files for absolute-path leaks, a configurable private-token denylist (see
[`.eif/local-denylist.txt.example`](.eif/local-denylist.txt.example)), and
secret-shaped patterns (API keys, bearer tokens, connection strings). It
is wired into CI - see [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
It is a heuristic scanner, not a guarantee: false negatives are possible,
especially for secret shapes it doesn't yet recognize.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| < 0.1.0 | No |
