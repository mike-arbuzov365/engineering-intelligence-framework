# RTK optional integration - codex

<!-- Generated from command-registry.json and adapter-capabilities.json. Do not edit by hand. -->

Instruction surface: `AGENTS.override.md or AGENTS.md`.
Tested product versions: `0.144.5`.
Hook behavior: `block-only`; runtime evidence: `mutation-unverified`.

RTK is optional. Core EIF remains valid when RTK is unavailable or degraded.
Trust a filtered route only after its required canary passes. A failed grep canary
makes an empty native search result inconclusive.

## Canonical routes

- `git-native`: `rtk git <subcommand> <args>` - eligible after canary.
- `grep-simple`: `rtk grep <pattern> <paths>` - eligible after canary.
- `grep-alternation`: `rtk grep -e <A> -e <B> <paths>` - eligible after canary.
- `read-bounded`: `rtk read --max-lines <N> <path>` - eligible after canary.
- `generic-space-free`: `rtk summary <tool> <space-free-args>` - eligible after canary.
- `quoted-whitespace`: `rtk proxy <tool> <args> # rtk-raw-ok: preserve argv` - always zero savings.
- `no-native-subcommand`: `unsupported - choose summary or explicit proxy from this registry` - always zero savings.
- `proxy-explicit`: `rtk proxy <tool> <args> # rtk-raw-ok: <reason>` - always zero savings.

The adjacent hook contract is a reviewable template, not an installation.
EIF does not mutate user hooks or configuration.
