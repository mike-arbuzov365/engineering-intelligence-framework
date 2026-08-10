# Required rule: graphic-design package та final delivery

`package_allowed` має default `false`. Відсутній або invalid approval state
означає заборону, а не implicit approval.

Перед EIF-managed action `package` або `final_delivery` виконайте:

```text
eifctl delivery check --action <package|final_delivery> --scope <exact-scope> --instance-path .
```

Command має PASS лише коли:

- active professional profile є `graphic-design`;
- цей required rule присутній у verified workspace lock/runtime без exception;
- `.eif/local-state/design-delivery-approval.yaml` schema-valid;
- `package_allowed: true`;
- owner, exact scope, approved actions, `decided_at`, `valid_until` і
  `evidence_ref` записані;
- approval ще чинний і evidence reference не виходить за project boundary.

EIF-managed package або final delivery не продовжується після nonzero result.
Model не може самостійно створити owner approval. Recording approval state є
`owner_gate`; validation є `machine` лише для EIF-managed command.

Довільна external ZIP, export, upload або shell command не проходить через цей
checker автоматично. Без окремого verified adapter guard ця ширша заборона є
`instruction_only`; не називайте її machine enforcement.

## QA scope

`changed_only` дозволено лише для явно localized change, коли shared font,
palette, brand rule, layout system, export setting, rights або cross-deliverable
input не змінювалися. Запишіть changed inputs/outputs, rationale та checks.

`full` QA обов'язкове, якщо змінено shared/global input, affected dependency
невідома, change охоплює кілька deliverable families або може змінити final
package. Це explicit human/model classification, не automatic dependency
engine.
