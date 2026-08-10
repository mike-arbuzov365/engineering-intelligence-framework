# Admission зовнішніх skills

## Статус

Current EIF source не імпортує, не встановлює і не активує third-party skills.
Цей документ визначає metadata і review gates для майбутнього candidate, але
не створює installer, universal plugin manifest або marketplace.

`eifctl skills check` перевіряє лише 12 repository-owned core skills і 3 skills
із bundled starter profiles. Їхні local fixtures мають
`provenance.external_import: false`; schema і checker fail-closed, якщо це
значення змінено.

## Обов'язкові admission gates

Future external candidate можна розглядати лише після виконання всіх gates:

1. Source URL і revision pinned до immutable commit digest.
2. License identified, reviewed і сумісна з intended use та redistribution.
3. Усі `scripts/`, `references/` і binary assets переглянуті.
4. Secrets, network, installation, filesystem, permissions і side effects
   задокументовані та пройшли security review.
5. Upstream містить real tests або evals, а evidence прив'язане до pinned
   revision.
6. Candidate проходить local `eifctl skills check` та додаткові bounded
   security checks без model calls.
7. Local comparative eval не показує regression або unjustified token cost;
   model/version/settings/budget і artifacts записані.
8. Owner явно погодив activation scope після review усіх попередніх gates.

Popularity, stars, publisher name або marketplace presence не замінюють
жоден gate. Upstream update є новим candidate і потребує повторного review.

## Required metadata для future candidate

До появи executable admission command candidate record має щонайменше містити:

```yaml
source:
  url: https://example.invalid/owner/repository
  revision: 40-hex-commit
license:
  identifier: SPDX-ID
  reviewed: true
surfaces:
  scripts_reviewed: true
  references_reviewed: true
  secrets_reviewed: true
  network_reviewed: true
  install_reviewed: true
  permissions_reviewed: true
upstream_evidence:
  tests_or_evals: path-or-url-at-pinned-revision
local_evidence:
  static_check: pass
  comparative_eval: pass-or-deferred
activation:
  owner: owner-reference
  scope: exact-profile-or-project-scope
  approval_evidence: durable-reference
```

Це metadata example, не accepted schema і не approval. `url`, commit, license,
owner та evidence не можна вигадувати або залишати implicit.

## Researched candidates, не imports

Point-in-time source review 2026-08-09 підтвердив лише architecture patterns:

| Source | Observed pattern | Current EIF disposition |
|---|---|---|
| [`dotnet/skills`](https://github.com/dotnet/skills) | MIT repository, static validation, tests та skill eval infrastructure; current source також документує baseline/treatment quality work. | Research reference only. Не pinned і не imported. |
| [`NVIDIA/skills`](https://github.com/NVIDIA/skills) | Agent Skills structure, per-skill evidence, Apache-2.0 code та CC-BY-4.0 documentation licensing. | Research reference only. Licensing split потребував би per-file review. |
| [`GoogleChrome/modern-web-guidance-src`](https://github.com/GoogleChrome/modern-web-guidance-src) | Source/eval separation, harness і guidance removal based on evaluation; Apache-2.0 code та CC-BY-4.0 guide content. | Research reference only. Не imported. |
| [`dash0hq/agent-skills`](https://github.com/dash0hq/agent-skills) | Dedicated `evals/`, deterministic telemetry assertions і Apache-2.0 license. | Research reference only. Не imported. |
| [`aws-samples/sample-agent-skill-eval`](https://github.com/aws-samples/sample-agent-skill-eval) | Model-free audit before trigger/functional eval, negative safety fixtures, tests і MIT-0 license. | Harness pattern only. Не imported. |

`anthropics/skills`, `mgechev/skills-best-practices`,
`hamelsmu/evals-skills` і broad community catalogs не були admitted під час
EIF-021. Planning research не знайшов достатнього combination root license,
real tests/evals і strict local admission evidence для first-package use.
Цей висновок не є permanent quality judgment; він лише пояснює, чому import
відсутній.

## Enforcement boundary

- `machine`: current `skill-contract.schema.json` і `eifctl skills check`
  відхиляють `external_import: true` у active first-party catalog та не
  виконують supporting scripts.
- `owner_gate`: future activation потребує explicit owner approval після
  completed admission record.
- `instruction_only`: EIF не може блокувати довільну third-party install
  command поза EIF-managed surfaces без окремого verified adapter guard.

Current implementation не має `inspect`, `admit`, `install`, `update` або
`remove` command для external skills. Такий lifecycle лишається backlog item
B-07 і потребує окремого security design.
