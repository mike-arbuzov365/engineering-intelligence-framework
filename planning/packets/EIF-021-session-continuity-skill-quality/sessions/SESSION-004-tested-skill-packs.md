---
id: SESSION-004
type: session-launch
status: prepared-awaiting-owner-approval
source_artifact: ../04-ROADMAP-021-session-continuity-skill-quality.md
session_context: .session-context/eif-021-session-004.md
depends_on: [SESSION-001]
---

# Session 004: контракт tested skill pack

## Мета

Додати model-free contract tests для кожного current EIF skill і зберегти professional profile як canonical grouping unit.

## Обов'язковий порядок читання

1. Packet files і result Session 001.
2. `skills/README.md`, усі current core skills і starter-profile skills.
3. Чинна implementation playbook/schema/materialization/sync для professional profile.
4. Existing tests для sync/profile/package.
5. External patterns із Facts лише як architecture references.

## Experience Retrieval Preflight

Знайти skill discovery failures, duplicate playbook content, stale loader incidents, profile collisions, unsafe scripts та evaluation guidance.

## У межах session

- Compact fixture schema для skill test/eval.
- Local fixtures поруч із 12 core і 3 starter skills.
- Model-free command `eifctl skills check`.
- Materialization supporting files і tests для loader isolation.
- External admission metadata policy без imports.

## Поза межами та no-touch zone

- Без universal plugin manifest.
- Без vendor plugin export.
- Без third-party skill install/copy.
- Без model-based eval у цій session.
- Без rewrite canonical playbooks у skill files.
- Без automatic loading tests у model context.

## Кроки

1. Створити inventory кожного skill і його canonical source.
2. Визначити positive/negative triggers, evidence, stop/forbidden behavior і deterministic assertions.
3. Додати fixtures з мінімумом duplicated prose.
4. Реалізувати checker для frontmatter, contained paths, references, script declarations, fixtures і provenance fields.
5. Перевірити, що workspace materialization переносить supporting files, а sync loaders лишаються compact.
6. Додати negative security/path/duplicate fixtures.
7. Оновити docs/capability claims лише після passing tests.

## Перевірка

```text
rtk python scripts/tests/test_sync_skills.py
rtk python scripts/tests/test_workspace_profiles.py
rtk python scripts/tests/test_package_smoke.py
rtk python scripts/eif_check_links.py
rtk python scripts/eif_privacy_scan.py
rtk git diff --check
```

Використати actual current profile test filenames і запустити кожний new skill-check test.

## Контракт bounded loop

- `success_evidence`: усі 15 current skills pass; malformed/reference-escape/unsafe fixtures fail; loaders не inject tests automatically.
- `evaluator`: checker tests і package journey.
- `max_iterations`: 4.
- `remote_run_budget`: 0.
- Stop, якщо fixture design дублює workflow source або потребує new plugin architecture.

## Критерії виходу

- [ ] Усі current skills мають valid local fixtures.
- [ ] Checker model-free та installable.
- [ ] Negative fixtures доводять effective checks.
- [ ] Profile grouping лишається canonical.
- [ ] Supporting files не збільшують normal skill context.
- [ ] External content не imported.

## Closeout та Knowledge Delta

Записати contract version, migration rule для future skills, checker coverage і known limits для Session 005.
