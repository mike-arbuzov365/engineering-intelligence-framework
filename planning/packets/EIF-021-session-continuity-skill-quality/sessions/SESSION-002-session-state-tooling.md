---
id: SESSION-002
type: session-launch
status: prepared-awaiting-owner-approval
source_artifact: ../04-ROADMAP-021-session-continuity-skill-quality.md
session_context: .session-context/eif-021-session-002.md
depends_on: [SESSION-001]
---

# Session 002: deterministic state сесії і resolution project

## Мета

Реалізувати canonical `.session-context` structure, file-based lifecycle commands і fail-closed project resolution.

## Обов'язковий порядок читання

1. Files цього packet і closeout/checkpoint Session 001.
2. Чинні templates, renderer locale і schemas.
3. Чинна implementation parser/commands CLI і registry v2/local-state.
4. Runtime bundling, package smoke та суміжні tests.

## Experience Retrieval Preflight

Знайти knowledge, decisions, tests і Git history щодо checkpoint drift, wrong-project incidents, render truthfulness, local-state migration та path-policy failures.

## У межах session

- Session-context template і schema.
- `eifctl session checkpoint`, `validate`, `handoff`, `resume-audit`.
- `eifctl projects resolve <id-or-name>`.
- Unit, journey, negative та package tests.
- Required resource/locale mirrors.

## Поза межами та no-touch zone

- Без database, transcript store, UI або daemon.
- Без adapter-specific chat creation.
- Без global `--project` migration.
- Без model calls.
- Без automatic approval decisions.

## Кроки

1. Спроєктувати schema із separation semantic та observable fields.
2. Додати localized template без duplicate workflow prose.
3. Реалізувати atomic checkpoint write і strict validation.
4. Збирати project/Git observations без secrets і worktree mutation.
5. Реалізувати resume-audit mismatch categories.
6. Реалізувати exact registry resolver та incomplete-instance checks.
7. Додати fail-closed fixtures і installed-wheel journey.

## Перевірка

```text
rtk python scripts/tests/test_locale.py
rtk python scripts/tests/test_operating_layer.py
rtk python scripts/tests/test_package_smoke.py
rtk python scripts/eif_validate_frontmatter.py
rtk python scripts/eif_privacy_scan.py
rtk git diff --check
```

Додати і запустити focused session/resolver tests, створені цією session.

## Контракт bounded loop

- `success_evidence`: valid checkpoint round-trip; кожний required mismatch повертає nonzero; resolver визначає exactly one correct project.
- `evaluator`: focused tests плюс commands вище.
- `max_iterations`: 4.
- `remote_run_budget`: 0.
- Stop за schema ambiguity, що дублює launch/task authority, або за leak machine-local path у committed artifacts.

## Критерії виходу

- [ ] Template/schema підтримують packet і structured single task.
- [ ] Light task лишається file-free by default.
- [ ] Усі four session commands працюють із source та installed wheel.
- [ ] Wrong/stale project state блокує handoff/resume.
- [ ] Resolver проходить positive і negative multi-project fixtures.
- [ ] Package mirrors і tests проходять.

## Closeout та Knowledge Delta

Записати schema version, lifecycle, atomicity behavior, mismatch taxonomy і exact CLI examples для Session 003.
