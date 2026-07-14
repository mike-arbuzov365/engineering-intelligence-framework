# Security Policy

## Reporting a vulnerability

Please do not open a public GitHub issue for security or privacy concerns.

Until a dedicated security contact/email is set up for this project, report
privately via a GitHub Security Advisory
(`Security` tab -> `Report a vulnerability`) on this repository once it is
public, or contact the maintainer directly through the profile listed on
this repository.

Include:
- A description of the issue and its potential impact.
- Steps to reproduce, if applicable.
- Any relevant logs, config, or version information (redact secrets before
  sharing).

## Scope

This is a documentation/methodology + tooling-adapter framework. Security
issues of interest include (non-exhaustive):

- A generated hook, adapter, or script that could execute unintended
  commands or leak data outside the intended boundary.
- A documented pattern that, if followed, would encourage storing secrets
  in tracked files or committing them to version control.
- Supply-chain concerns in any scripted dependency installation.

## Supported versions

Pre-v0.1: no versioned releases yet. Once `v0.1.0` ships, this section will
list which versions receive security fixes.
