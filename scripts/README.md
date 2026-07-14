# scripts/

## Available

| Script | Does | Used by |
|---|---|---|
| [`eif_privacy_scan.py`](eif_privacy_scan.py) | Scans tracked files for absolute-path leaks, secret-shaped patterns, and instance-specific denylisted tokens (`.eif/local-denylist.txt`, gitignored) | CI, and manually before any commit that references a real project/path/person |
| [`eif_validate_frontmatter.py`](eif_validate_frontmatter.py) | Validates knowledge-artifact YAML frontmatter against `core/schemas/knowledge-frontmatter.schema.json` | CI |
| [`eif_check_links.py`](eif_check_links.py) | Checks relative Markdown links (and same-file/cross-file anchors) resolve | CI |

Run any of them with `--help` for options. All three are stdlib-only
(no `pip install` needed) except the CI-only YAML syntax check, which uses
PyYAML.

## Not populated yet

Bootstrap (`eifctl init` equivalent), health checks (`eifctl doctor`
equivalent), knowledge-index generation, graph-freshness checks, and
merge-gate enforcement. The private instance has working, tested versions
of a graph-freshness checker and a controlled merge-gate script; porting
requires removing private repo names and machine-specific paths from both
the script and its default config. See
[`docs/guides/vertical-slice.md`](../docs/guides/vertical-slice.md) for
sequencing.
