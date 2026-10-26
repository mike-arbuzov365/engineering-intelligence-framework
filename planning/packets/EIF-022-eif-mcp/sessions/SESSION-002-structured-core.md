---
id: SESSION-002
logical_session: SESSION-002
type: session-launch
status: completed
source_artifact: ../04-ROADMAP-022-eif-mcp.md
session_context: .session-context/eif-022-session-002.md
continuation_mode: same_chat
depends_on: [SESSION-001]
---

# SESSION-002: структурований core і нові детерміновані функції

## Goal

Дати MCP-шару публічні функції зі структурованими результатами для всіх операцій D-005 і D-009, не змінивши жодного байта виводу наявних CLI-команд, і додати три відсутні детерміновані функції (статус пакета, brief, доступ до артефакту) та capabilities.

## Required reading order

1. Файли пакета 00-04, [02-FACTS](../02-FACTS-022-eif-mcp.md) розділ 3, [03-DECISIONS](../03-DECISIONS-022-eif-mcp.md) D-003, D-004, D-007, D-008, D-012.
2. Чекпойнт і closeout SESSION-001.
3. Код: `src/engineering_intelligence_framework/commands/{session,delivery,doctor,search,render}.py`, `workspace_contract.py`, `workspace_materialization.py`, `scripts/eif_verify_runtime.py`, `scripts/eif_search_knowledge.py`, `scripts/eif_render.py`.
4. `templates/session-launch.md`, `playbooks/execution-packet-execution.md`, `skills/run-execution-packet/SKILL.md`.

## Experience retrieval preflight

Пошук у `docs/` і `planning/` за "golden", "characterization", "frontmatter status", "checkpoint"; у тестах `scripts/tests/test_session_commands.py`, `test_delivery_guard.py`, `test_verify_runtime.py` знайти наявні знімки й фікстури, які можна повторно використати. Записати знайдене.

## Scope

- Golden-знімки stdout, stderr і коду виходу до рефакторингу (`scripts/tests/fixtures/service_golden/`, шляхи нормалізуються).
- `src/engineering_intelligence_framework/service/`: `doctor`, `session`, `render`, `packets`, `artifacts`, `brief`, `capabilities`, ресурс `task_kinds.json`.
- Виокремлення збору звіту з `main` у `scripts/eif_verify_runtime.py` (джерело істини) з наступним `python scripts/sync_package_sources.py`.
- Перебудова CLI-команд так, щоб друкувати з service-функцій.
- Конвенція статусів D-008: мінімальні правки `templates/session-launch.md`, `playbooks/execution-packet-execution.md`, `skills/run-execution-packet/SKILL.md`, дзеркала мов, sync.
- Тести: `scripts/tests/test_service_golden.py`, `scripts/tests/test_service_core.py`, запис у `run_all.py`.

## Out of scope / do not touch

- Пакет `eif_mcp`, імпорти `mcp`, `pyproject.toml`, нові підкоманди в `cli.py`.
- Семантика `session handoff` (лишається поза каталогом).
- Генерація entrypoint-блока (`scripts/eif_init.py`), `adapters/`, `integrations/`.
- Класифікація задач, структурний валідатор пакетів (B-10, B-19).
- Зміна вмісту playbooks понад словник статусів.

## Verification

```text
python scripts/tests/test_service_golden.py
python scripts/tests/test_service_core.py
python scripts/tests/test_session_commands.py
python scripts/tests/test_delivery_guard.py
python scripts/tests/test_verify_runtime.py
python scripts/tests/test_search_knowledge.py
python scripts/tests/test_render.py
python scripts/tests/test_locale.py
python scripts/tests/test_operating_layer.py
python scripts/tests/test_sync_skills.py
python scripts/sync_package_sources.py --check
python scripts/eif_validate_frontmatter.py
python scripts/eif_privacy_scan.py
python scripts/eif_check_links.py
```

## Bounded loop contract

- `success_evidence`: golden-знімки, записані до рефакторингу, проходять після нього без змін; нові функції повертають очікувані dict у позитивних і негативних тестах.
- `evaluator`: команди вище.
- `max_iterations`: 4.
- `remote_run_budget`: 0.
- Стоп: golden-знімок можна зберегти лише зі зміною виводу CLI (тоді зупинитись, записати розбіжність і не "виправляти" знімок), або вимога словника D-008 суперечить наявному тесту дрейфу локалей без безпечної правки.
- Checkpoint: `.session-context/eif-022-session-002.md`.

## Exit criteria

- [ ] Вивід наявних CLI-команд побайтово незмінний (golden зелений).
- [ ] Усі service-функції D-005/D-009 повертають типізовані dict; нова логіка не друкує в stdout.
- [ ] `capabilities`, `brief`, `artifact_get`, `packet_status` мають позитивні й негативні тести (невідомий артефакт, невідповідність хеша, шляхові атаки, symlink, відсутній runtime, `legacy`-статуси, цикл `depends_on`, обрізання).
- [ ] Тест дрейфу `task_kinds.json` проти skills установленого пакета проходить.
- [ ] Словник D-008 застосовано в трьох артефактах, мовні дзеркала та sync чисті.
- [ ] У коді немає імпорту `mcp`; `sync_package_sources.py --check` чистий; закомічено локально.

## Closeout / Knowledge Delta

Записати: список витягнутих функцій із їхніми сигнатурами (вхід для SESSION-003), будь-яку розбіжність між CLI-виводом і структурою, що знайшлась під час рефакторингу, та чи словник D-008 вимагає пропозиції `provisional` рішення.
