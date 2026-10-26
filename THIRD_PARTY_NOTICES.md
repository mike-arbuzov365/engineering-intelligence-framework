# Third-party notices

EIF itself is licensed under Apache-2.0 (see [`LICENSE`](LICENSE)). This
file lists every Python package `scripts/requirements.txt` actually resolves
to at runtime - the two direct dependencies plus their full transitive
closure - with the license each declares. Generated from a real, resolved
dependency install (`pip install -r scripts/requirements.txt` into a clean
virtualenv, then `pip freeze`), not by hand-transcribing `requirements.txt`.
See [`sbom.cdx.json`](sbom.cdx.json) for the machine-readable CycloneDX
equivalent, and `scripts/eif_check_licenses.py` /
`core/policies/license-policy.json` for the CI-enforced policy this list is
checked against on every build.

**Direct dependencies** (declared in `scripts/requirements.txt`):

| Package | Version | License |
|---|---|---|
| PyYAML | 6.0.2 | MIT |
| jsonschema (`[format-nongpl]` extra) | 4.23.0 | MIT |

**Transitive dependencies** (pulled in by the two above, `format-nongpl`
extra specifically):

| Package | Version | License |
|---|---|---|
| arrow | 1.4.0 | Apache-2.0 |
| attrs | 26.1.0 | MIT |
| fqdn | 1.5.1 | MPL-2.0 |
| idna | 3.18 | BSD-3-Clause |
| isoduration | 20.11.0 | ISC |
| jsonpointer | 3.1.1 | BSD |
| jsonschema-specifications | 2025.9.1 | MIT |
| python-dateutil | 2.9.0.post0 | Apache-2.0 / BSD |
| referencing | 0.37.0 | MIT |
| rfc3339-validator | 0.1.4 | MIT |
| rfc3986-validator | 0.1.1 | MIT |
| rpds-py | 2026.6.3 | MIT |
| six | 1.17.0 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| tzdata | 2026.3 | Apache-2.0 |
| uri-template | 1.3.0 | MIT |
| webcolors | 25.10.0 | BSD-3-Clause |

**Not a dependency of this list, mentioned for context**: the GPL-3.0-or-later
`rfc3987` package, which the plain `jsonschema[format]` extra (not used here)
would pull in for the same `uri`/`iri` format checks - `format-nongpl`
resolves `uri` via `rfc3986-validator` (MIT) instead, and EIF's schemas
never use `iri`/`iri-reference` at all (verified by
`scripts/tests/test_format_dependencies.py`, which reads every schema's
declared formats directly rather than trusting this claim). `rfc3987` is
not installed, not required, and not shipped by this project.

Every license above is permissive (MIT/BSD/ISC/Apache-2.0/PSF-2.0) or
weak-copyleft at the file level only (MPL-2.0, `fqdn`) - none is GPL/AGPL.
This is a factual license inventory, not a legal compatibility opinion;
`core/policies/license-policy.json` records which license families are
currently accepted and is the actual enforcement mechanism, re-checked on
every CI run via `scripts/eif_check_licenses.py`.

This file lists dependencies as of the commit that introduced it. Re-run
the generation steps above after any dependency change rather than
hand-editing stale entries - and regenerate `sbom.cdx.json` too:
`scripts/eif_check_licenses.py` checks that file by default (not this one,
and not the live environment), and fails the build if it disagrees with
`requirements.txt`'s pins.

## Optional MCP runtime

The optional `[mcp]` environment is inventoried separately in
[sbom-mcp.cdx.json](sbom-mcp.cdx.json), with the exact 41-component Windows /
Python 3.11 resolution in [constraints](integrations/eif-mcp/constraints.txt).
The base dependency list above is unchanged. The tested SDK is `mcp==2.1.1`;
other admitted 2.x versions need their own verification. Reproduce this
inventory only in a clean runtime environment, without build/test tooling:

```text
python scripts/eif_generate_mcp_inventory.py --check
python scripts/eif_check_mcp_licenses.py
python scripts/eif_check_licenses.py --environment
```

Raw license declarations remain in the SBOM. The exact standard PSF Trove
classifier maps to the policy's existing `PSF-2.0`; a bare ambiguous `PSF`
string still fails closed. This inventory records metadata rather than a
legal compatibility opinion. Linux and Python 3.12 runtime checks were not run.

| Package | Version | First declared license identifier |
|---|---|---|
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| arrow | 1.4.0 | License :: OSI Approved :: Apache Software License |
| attrs | 26.1.0 | MIT |
| cffi | 2.1.1 | MIT-0 |
| click | 8.5.0 | BSD-3-Clause |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| fqdn | 1.6.0 | MPL-2.0 |
| h11 | 0.16.0 | MIT |
| httpcore2 | 2.16.0 | BSD-3-Clause |
| httpx2 | 2.16.0 | BSD-3-Clause |
| idna | 3.20 | BSD-3-Clause |
| isoduration | 20.11.0 | License :: OSI Approved :: ISC License (ISCL) |
| jsonpointer | 3.6 | Modified BSD License |
| jsonschema | 4.23.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| mcp | 2.1.1 | MIT |
| mcp-types | 2.1.1 | MIT |
| opentelemetry-api | 1.45.1 | Apache-2.0 |
| pycparser | 3.12 | BSD-3-Clause |
| pydantic | 2.14.1 | MIT |
| pydantic-core | 2.50.1 | MIT |
| pyjwt | 2.15.1 | MIT |
| python-dateutil | 3.0.0 | Dual License |
| python-multipart | 0.0.32 | Apache-2.0 |
| pywin32 | 312 | PSF |
| pyyaml | 6.0.2 | MIT |
| referencing | 0.37.0 | MIT |
| rfc3339-validator | 0.1.4 | MIT license |
| rfc3986-validator | 0.1.1 | MIT license |
| rpds-py | 2026.9.1 | MIT |
| six | 1.17.0 | MIT |
| sse-starlette | 3.6.0 | BSD-3-Clause |
| starlette | 1.10.0 | BSD-3-Clause |
| truststore | 0.10.5 | MIT |
| typing-inspection | 0.4.4 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| tzdata | 2026.5 | Apache-2.0 |
| uri-template | 1.3.0 | MIT License |
| uvicorn | 0.54.0 | BSD-3-Clause |
| webcolors | 25.10.0 | BSD-3-Clause |
