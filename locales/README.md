# locales/

Localized template/message packs for **generated project artifacts**
(ADR headings, Knowledge Delta section labels, session-context boilerplate,
lint messages). Framework source documentation itself is English-canonical
and is not duplicated per locale.

```text
locales/
  en/
    messages.yaml       # not populated yet
    terminology.yaml
    templates/
  uk/
    messages.yaml
    terminology.yaml
    templates/
```

A locale is selected per project instance via `.eif/config.yaml`
(`localization.documentation_locale`) - see
[`.eif/config.yaml.example`](../.eif/config.yaml.example). Canonical
methodology text is never fully re-translated; only generated,
project-facing output is localized. See
[`docs/architecture/HOW-EIF-WORKS.md`](../docs/architecture/HOW-EIF-WORKS.md#language-configuration).

The `terminology.yaml` files are a matched controlled vocabulary. They keep
preferred English and Ukrainian terms under the same keys and distinguish
standards-aligned, industry-established, and EIF-defined terms. The
human-readable definitions, translation rules, and reference basis live in
[`docs/reference/terminology.md`](../docs/reference/terminology.md).
