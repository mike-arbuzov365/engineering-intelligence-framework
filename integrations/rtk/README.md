# integrations/rtk/

Optional shell-output compression with correctness-first routing and local,
content-free counters.

## Status: behavioral adapter implemented

EIF now ships a removable RTK adapter with:

- a compatible version range `>=0.42.0,<0.44.0`, tested with `0.43.0`;
- a machine-readable provider manifest and command registry;
- canaries for the CLI surface, proxy argv preservation, search alternation and
  git diff;
- generated compact routing instructions for the shared contract and all four
  public agent adapters;
- a provider/version capability matrix plus generated, non-installing hook
  contract templates that distinguish rewrite-capable from block-only hosts;
- strict local telemetry that cannot store command text, argv, paths, cwd or
  output;
- doctor states `disabled`, `healthy`, `degraded`, `misconfigured` and
  `unavailable`.

The version range is necessary but not sufficient. `healthy` requires every
required behavioral canary to pass. PATH reachability alone is never health.

The upstream project is [RTK - Rust Token Killer](https://github.com/rtk-ai/rtk),
not the unrelated Rust Type Kit package with the same executable name. Follow
the upstream [installation verification](https://www.rtk-ai.app/docs/getting-started/installation/)
and confirm both `rtk --version` and `rtk gain` before enabling the adapter.
EIF never installs RTK.

## Enable in a project instance

Edit the user-owned `.eif/config.yaml`, then rerun `eifctl doctor`:

```yaml
integrations:
  shell_output_compression:
    enabled: true
    provider: rtk
    processing: local
    data_boundary: local-only
    telemetry_enabled: false
    failure_policy: degrade
```

`failure_policy: degrade` keeps core EIF usable when RTK is missing or a
behavioral canary fails. `fail-closed` makes any non-healthy state a doctor
failure. A boundary mismatch or wrong provider is always `misconfigured`, even
under degrade.

For machine-readable evidence:

```text
eifctl doctor --instance-path . --integration-report .eif/integration-health.json
```

Do not commit a report that contains project-specific local configuration.

## Command routing contract

Canonical routes live in [`command-registry.json`](command-registry.json).
Provider-specific delivery facts live in
[`adapter-capabilities.json`](adapter-capabilities.json). The command registry
remains the only route source. Together they generate
[`generated-instructions.md`](generated-instructions.md), four compact adapter
fragments under [`generated/adapters/`](generated/adapters/) and four reviewed
hook contracts under [`generated/hooks/`](generated/hooks/). They must pass:

```text
python scripts/eif_generate_rtk_guidance.py --check
```

Critical invariants:

- `rtk proxy` is raw and contributes zero estimated savings;
- an unsupported `rtk <tool>` fallback is a parse failure, not filtering;
- generic `rtk summary` is restricted to space-free argv on the tested Windows
  boundary;
- correctness-sensitive whitespace/special-character argv uses explicit raw
  proxy after the proxy canary passes;
- search output is trusted only when the search canary passes; empty output from a
  failed route is inconclusive;
- user hooks and user-level agent config are never installed or modified.

The generated hook JSON files are contract templates, not executable hook
scripts or active configuration. They make the provider event, input path,
output behavior and current evidence boundary reviewable. Claude Code and
Cursor are marked rewrite-capable from their available evidence; Codex and
Hermes remain block-only because input mutation is unverified or known not to
apply on the tested version. A maintainer must still review, implement and
behaviorally test any active hook before installation.

## Content-free local telemetry

Telemetry is opt-in and local. The bundled recorder writes only under
`.eif/local-state/`, which EIF adds to the managed `.gitignore` block:

```text
python .eif/runtime/eif_rtk_telemetry.py record --instance-root . \
  --attempt-id benchmark-attempt-001 \
  --command-class git-native --route native-filtered --outcome success \
  --raw-bytes 400 --emitted-bytes 40
python .eif/runtime/eif_rtk_telemetry.py summary --instance-root . \
  --attempt-id benchmark-attempt-001
```

The schema rejects additional fields, so command content, argv, paths and
output cannot be added accidentally. Estimates are byte-based and remain
estimates. Raw proxy, parse failure, unsupported, failed and degraded routes
always record zero savings, even if their output happens to be shorter.
`attempt_id` is an optional content-free identifier; it enables benchmark
attribution without storing a prompt, command, path or output.

## Release-candidate evidence and Windows search routing

The first Windows release-candidate probe resolved RTK `0.43.0` but reported
`degraded`: `rtk grep` selected an unrelated Embarcadero `grep.exe` earlier on
PATH, and that executable rejected RTK's `-I` argument. The failure was real,
but it was not a failure of RTK's native ripgrep filter.

The portable contract now uses `rtk rg` explicitly. This route is present in
RTK `0.43.0`, bypasses the ambiguous `grep.exe` lookup and preserves repeated
`-e` arguments. The revised installed-host suite passes 24/24 on that Windows
host and the adapter now reports `healthy`. This is evidence for the tested
host/version/command set, not every RTK installation. No global PATH edit or
vendor-tool removal is required.

No general token-reduction or quality-improvement claim follows from these
canaries. Comparative benchmark evidence remains a separate requirement.
