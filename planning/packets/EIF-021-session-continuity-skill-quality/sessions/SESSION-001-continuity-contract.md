---
id: SESSION-001
type: session-launch
status: prepared-awaiting-owner-approval
source_artifact: ../04-ROADMAP-021-session-continuity-skill-quality.md
session_context: .session-context/eif-021-session-001.md
depends_on: []
---

# Session 001: контракт continuation та enforcement

## Мета

Визначити семантику session/chat continuation і enforcement у чинній EIF architecture до runtime implementation.

## Обов'язковий порядок читання

1. Packet files `00`-`04` і detailed backlog.
2. `AGENTS.md`.
3. `core/policies/decisions.md`.
4. `docs/architecture/HOW-EIF-WORKS.md` і `docs/reference/terminology.md`.
5. Playbooks і templates для session preparation, execution та closeout.
6. Claims про capabilities і operating-layer tests.

## Experience Retrieval Preflight

Знайти у current decisions, docs і tests згадки `session context`, `compaction`, `resume`, `chat`, `thread`, `three-layer`, `required`, `enforcement`. Записати exact relevant sources у checkpoint.

## У межах session

- Logical session окремо від physical chat.
- Поведінка `same_chat | new_chat | auto`.
- Transition за принципом checkpoint-first і non-authoritative compaction.
- Enforcement-level terminology.
- Вузьке decision update і structural tests.

## Поза межами та no-touch zone

- Без CLI/runtime behavior.
- Без adapter automation.
- Без skill fixtures.
- Без profile changes.
- Без claim про Available behavior до implementation.
- Без broad rewrite architecture docs.

## Кроки

1. Повторно перевірити кожну packet recommendation проти ratified decisions.
2. Додати narrow decision або explicit supersession лише за необхідності.
3. Оновити одне canonical architecture explanation і направити до нього playbooks/templates.
4. Визначити light-task behavior, щоб continuity не додавала ceremony.
5. Додати tests для three layers, same-chat option, checkpoint authority і enforcement labels.
6. Виконати language і capability-claim audit для touched docs.

## Перевірка

```text
rtk python scripts/tests/test_operating_layer.py
rtk python scripts/tests/test_locale.py
rtk python scripts/eif_check_links.py
rtk python scripts/eif_privacy_scan.py
rtk git diff --check
```

## Контракт bounded loop

- `success_evidence`: усі canonical sources узгоджені, а structural tests ловлять contradictory fixtures.
- `evaluator`: commands вище плюс exact source search.
- `max_iterations`: 3.
- `remote_run_budget`: 0.
- Stop за conflict із ratified decision, implication четвертого layer або unsupported enforcement claim.

## Критерії виходу

- [ ] Logical session і physical chat розділено.
- [ ] Same-chat continuation підтримується explicitly.
- [ ] New-chat automation залежить від capability.
- [ ] Compaction є необов'язковою і non-authoritative.
- [ ] Enforcement levels визначено без false guarantees.
- [ ] Tests, privacy і link checks проходять.

## Closeout та Knowledge Delta

Записати final definitions, decision status, rejected alternatives і implementation constraint, які Session 002 має успадкувати.
