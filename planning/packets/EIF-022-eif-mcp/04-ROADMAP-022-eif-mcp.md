---
packet: EIF-022-eif-mcp
type: roadmap
status: executed-branch-B
execution: single-agent-sequential
created: 2026-10-26
---

# Дорожня карта: eif-mcp

## Глобальні обмеження виконання

- Один відповідальний агент, сесії строго послідовні. Сесію не делегують і пакет не ділять між паралельними агентами. Обмежену роботу всередині сесії (широкий пошук лише читання, незалежне друге читання diff, обмежена генерація) можна делегувати, якщо результат повертається на перевірку, а запис сесії називає, що делеговано і чим перевірено. Checkpoint, evidence, closeout і Knowledge Delta пише лише відповідальний агент.
- Кожна сесія працює у власному git worktree від свіжого `origin/main`, гілка `wm/eif-022-<slug>`. Основну робочу копію репозиторію не змінювати: вона може мати чужу незавершену роботу, її читати як evidence, а не як базу для reset.
- Лише локальні commit. Без push, PR, merge, tag, release, зміни видимості, зміни hosted CI, зміни живої конфігурації клієнтів.
- Бюджет зовнішніх платних викликів і ходів моделі: 0, доки власник не задасть число (Open O-6). Це стосується canary-ходів, поведінкового порівняння D-19 і скриптів `mcp-builder`.
- Перед commit у кожній сесії: `python scripts/eif_privacy_scan.py` (після `git add`, бо скан читає tracked-файли) і `python scripts/eif_check_links.py`. Для змін у `core/schemas/`, `core/ontology/`, `docs/architecture/`, `docs/product/`, `docs/research/`, `locales/`, `templates/`, `playbooks/`, `skills/`, `integrations/`, `scripts/` ще й `python scripts/sync_package_sources.py`, і синхронізовані копії комітяться разом зі зміною.
- Реліз 0.2.9 може потрапити в `main` між сесіями: перед кожною сесією `git fetch --all --prune` і rebase (D-020, O-5).
- Приватних даних і приватних інстансів немає. Усі вибірки синтетичні, створені `eifctl new`.
- Контур перевірки відомих багів: для кожного виправленого дефекту записати вхід, очікуваний інваріант, фактичний результат, вплив, `файл:рядок` і тест, що падає без виправлення.

## Ворота

- **G1** (кінець SESSION-005): тести фази 1 зелені, `tools/list` у бюджеті або порушення зафіксоване рішенням, немає відкритих P0/P1.
- **G1c** (SESSION-005, повторно в SESSION-007): footprint-критерій для компактного блока (D-017).
- **G2** (початок SESSION-006): збережений доказ elicitation принаймні в одного клієнта.
- Гілки: A (G1 і G2), B (G2 не пройдено), C (G1 не пройдено після трьох ітерацій). Деталі в [D-019](03-DECISIONS-022-eif-mcp.md).

## Session 001 - Базова лінія, бюджети, життєздатність залежності

Залежності: немає.

1. `git fetch --all --prune`, `git worktree list`, rebase на `origin/main`. Записати SHA і чи реліз 0.2.9 уже в `main`.
2. Перевимірити B0 скриптом з [evidence/](evidence/measure_baseline.py) на актуальному `main`. Порівняти з [записаним результатом](evidence/baseline-2026-10-26.json), записати різницю (D-017).
3. Підняти скрипт у `scripts/eif_context_footprint.py`: детермінований вивід (режим `--no-latency`), відносні шляхи, перевірка `--check` проти закоміченої лінії. Тест `scripts/tests/test_context_footprint.py`, інвентар `run_all.py`.
4. Написати `docs/benchmarks/context-footprint/README.md` (метод, обмеження, таблиця сценаріїв) і закомітити лінію B0 у JSON; додати посилання з `docs/benchmarks/README.md`.
5. Перевірка залежності: чисте віртуальне середовище, `pip install` бази плюс `mcp` v2, `pip check`; потім одноразовий сервер-проба поза репозиторієм (не комітиться): `MCPServer`, явні annotations, структурований вихід, stdio, in-memory `Client` і підпроцес-клієнт, розмір `tools/list` на інструмент. Прочитати поверхню elicitation в SDK без запуску клієнта.
6. Закріпити версію SDK для D-013. Якщо поверхня API відхиляється від припущень пакета, дописати нове рішення пакета з наступним вільним номером, яке вказує замінюване, а не змінювати ratified.

Verification:

```text
python scripts/tests/test_context_footprint.py
python scripts/eif_context_footprint.py --check docs/benchmarks/context-footprint/baseline.json
python scripts/eif_check_links.py
python scripts/eif_privacy_scan.py
python scripts/sync_package_sources.py --check
git diff --check
```

Exit: скрипт у `scripts/` двічі підряд дає ідентичний вивід у режимі `--no-latency`, тест проходить, B0 записано з SHA джерела й різницею до лінії 2026-10-26; `pip check` чистий у чистому venv, версія SDK закріплена; проба на stdio проходить круговий виклик SDK-клієнтом; бюджети D-006 підтверджені або записане нове рішення про їх зміну.

## Session 002 - Структурований core і нові детерміновані функції

Залежності: SESSION-001.

1. Спершу golden-знімки (stdout, stderr, код виходу) для матриці фікстур: doctor ok/fail, session validate pass/fail, resume-audit по кожній категорії розбіжності, delivery pass/blocked, search (є результати, немає, malformed), render `--stdout` для обох артефактів.
2. Пакет `src/engineering_intelligence_framework/service/`: функції `doctor_report`, `session_validate`, `session_resume_audit`, `session_checkpoint_plan/apply`, `render_preview/apply`, адаптери до `search` і `check_delivery`. Зміни в `scripts/eif_verify_runtime.py` (виокремити збір звіту з `main`) і синхронізація в `_impl`.
3. Перебудувати CLI так, щоб друкувати з цих функцій. Golden-знімки лишаються зеленими.
4. Нові функції: `capabilities`, `brief` (ресурс `task_kinds.json` + тест дрейфу), `artifact_get` (маніфест, хеші, секції, курсори), `packet_status` (словник D-008, `legacy`, `partial`).
5. Мінімальна правка `templates/session-launch.md`, `playbooks/execution-packet-execution.md`, `skills/run-execution-packet/SKILL.md` під словник статусів D-008; дзеркала мов і sync.
6. Негативні тести нових функцій: невідомий артефакт, невідповідність хеша, `..` та абсолютні шляхи в `name`/`section`, symlink, відсутній runtime, `legacy`-статуси, цикл у `depends_on`, надвелика секція.

Verification:

```text
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
```

Додати й запустити нові тести service-шару. Exit: golden-знімки CLI зелені (вивід наявних команд побайтово незмінний), усі service-функції повертають типізовані dict з юніт-тестами, включно з негативними; у коді немає імпорту `mcp`; `sync_package_sources.py --check` чистий.

## Session 003 - Сервер фази 1

Залежності: SESSION-002.

1. Пакет `engineering_intelligence_framework/eif_mcp/`: сервер, конверт відповіді, статуси, помилки, межі, containment, перевірка drift, реєстрація 9 інструментів D-005 з явними annotations і описами ≤ 280 символів, без шляхових аргументів, `additionalProperties: false`.
2. `commands/mcp_cmd.py` і реєстрація `mcp` у `cli.py`. `serve` з `--instance-path`/`EIF_INSTANCE_PATH`, `--packets-root`, `--self-test`, коди виходу 0/2/3. Ліниве імпортування SDK і повідомлення без traceback за відсутнього extra.
3. Optional extra `mcp` у `pyproject.toml` за пінам з S1. Статичний каталог інструментів у JSON.
4. Одночасність, дедлайни, журнал у stderr (D-018). Обробники нічого не пишуть у stdout.
5. In-memory тести через `Client(server)`: всі 9 інструментів, позитивні й негативні, обрізання, `stale`, `partial`, `unavailable`, `unknown`.
6. Виміряти `tools/list` і записати розмір.

Verification:

```text
python scripts/tests/test_eif_mcp_inmemory.py
python scripts/tests/test_package_smoke.py
python scripts/sync_package_sources.py --check
python scripts/eif_privacy_scan.py
```

Тести репозиторію це самостійні скрипти, що друкують рівно один рядок `EIF-RESULT: passed=<P> total=<T>` (pytest не використовується). Новий файл `scripts/tests/test_eif_mcp_inmemory.py` додається в список `SUITES` у `scripts/tests/run_all.py`; без встановленого SDK він друкує `SKIPPED: mcp extra not installed` і `EIF-RESULT: passed=0 total=0`. Exit: усі 9 інструментів проходять in-memory тести; `tools/list` режиму reader ≤ 6 144 байти або порушення записане рішенням; старт без кореня, з не-EIF каталогом і без extra поводиться за D-002 і D-013; `eifctl --help` та `eifctl doctor` без extra працюють як раніше.

## Session 004 - Харнес, пакування, документація фази 1

Залежності: SESSION-003.

1. Харнес по stdio: підпроцес `eifctl mcp serve`, справжній SDK-клієнт, повна негативна матриця D-016 п. 3, тест тиші stdout, kill посеред виклику, EOF stdin.
2. Тест установленого wheel у чистому venv з extra і без нього; регресія бази.
3. Ліцензійний контур extra: `sbom-mcp.cdx.json`, розділ у `THIRD_PARTY_NOTICES.md`, `eif_check_licenses.py --environment` у чистому venv з extra, тести цього контуру.
4. Шаблони конфігурації для чотирьох клієнтів (reader і writer) у `integrations/eif-mcp/generated/` з `installed: false`; тест дрейфу; формат Hermes перевірити довідкою CLI.
5. Документація: `docs/guides/eif-mcp.md`, рядок у таблиці можливостей README (`Experimental`), точкове уточнення "EIF не говорить MCP" у `integrations/vendor-docs/README.md`, `integrations/README.md`, `docs/architecture/HOW-EIF-WORKS.md`; запис у `CHANGELOG.md` секції `Unreleased`.
6. 10 eval-питань за `mcp-builder` на синтетичній фікстурі (`docs/benchmarks/mcp-eval/`), відповіді перевірені детермінованим скриптом через in-memory клієнт, статус `NOT RUN`.

Verification:

```text
python scripts/tests/test_eif_mcp_stdio.py
python scripts/tests/test_package_build.py
python scripts/tests/test_package_smoke.py
python scripts/tests/test_check_licenses.py
python scripts/eif_check_licenses.py --environment
python scripts/sync_package_sources.py --check
python scripts/eif_check_links.py
python scripts/eif_validate_frontmatter.py
python scripts/eif_privacy_scan.py
```

Нові файли тестів назвати за конвенцією. Exit: stdio-харнес і тест wheel (з extra і без) зелені; ліцензійний контур extra проходить; шаблони конфігурації проходять тест дрейфу; посилання, frontmatter і privacy-скан чисті; 10 питань мають перевірені відповіді й явне `NOT RUN`; жодного твердження про економію токенів у документації.

## Session 005 - Ворота G1, canary клієнтів, вимір "після"

Залежності: SESSION-004.

1. Повторно прогнати всі тести фази 1, оцінити власні findings за каталогом серйозності P0..P3. Відкриті P0/P1 виправити (до трьох ітерацій), інакше гілка C.
2. Розширити `eif_context_footprint.py` режимом "після": скрипт керує in-memory клієнтом на синтетичному інстансі, вимірює `tools/list`, типові відповіді `eif_brief` і секційні читання `eif_artifact_get` для читань, які потрібні кожному сценарію. Компактний блок до SESSION-007 рахується як бюджет і чесно позначається `INFERRED`.
3. Canary по кожному встановленому клієнту (Claude Code, Codex, Cursor, Hermes): версія, форма конфігурації, перевірка з'єднання без ходу моделі, якщо клієнт має таку команду. Виклик інструмента й elicitation-цикл через тестовий probe-сервер (`scripts/tests/fixtures/eif_mcp/`, не постачається) лише в межах дозволених ходів (O-6). Журнали санітувати й зберегти в `docs/benchmarks/eif-mcp-canary/`. Недоступне, що не виконано, записати як `not-available` або `configured-not-verified` із причиною.
4. Обчислити G1, G1c, G2 за D-017 і записати вердикти з доказом.
5. Вибрати гілку (A, B, C) і записати в checkpoint та у `docs/benchmarks/context-footprint/`.

Verification:

```text
python scripts/eif_context_footprint.py --mcp-after --check docs/benchmarks/context-footprint/after.json
python scripts/tests/run_all.py
python scripts/eif_privacy_scan.py
python scripts/eif_check_links.py
```

Exit: вердикти G1, G1c, G2 записані (кожний із командами й числами, або `NOT RUN` з причиною); статус кожного клієнта один із `verified`, `configured-not-verified`, `not-available`; гілку вибрано; жодне твердження не перевищує докази.

## Session 006 - Фаза 2: протокол схвалення, checkpoint і evidence

Залежності: SESSION-005, гілка A. Якщо гілка B або C, сесія не виконується, а її обсяг переходить у closeout як `deferred` із причиною.

1. Сховище prepared-subject у пам'яті, канонічний JSON і хеш, TTL, одноразовість (D-010).
2. `--writes` і реєстрація п'яти інструментів D-009; опис кожного каже "лише активний агент".
3. `eif_commit`: повторне зчитування стану, `version_conflict`/`stale`, запит elicitation з таймаутом, `requires_host_action` для клієнта без можливості, `approval_declined`.
4. Intent, атомарний запис цілі, receipt, audit-журнал без вмісту, `eif_operation_get`, ідемпотентність.
5. `eif_checkpoint_prepare` і `eif_evidence_prepare` над `session_checkpoint_plan`.
6. Тести: вхідні поля схвалення, повтор, підроблений `subject_id`, протермінований, дрейф цілі, дрейф інстанса, паралельні commit, клієнт без elicitation, decline, cancel, таймаут, ін'єкція збоїв між intent, ціллю і receipt, traversal у `session_id`, `idempotency_conflict`, зайвий розмір preview, відсутність вмісту в audit, режим без `--writes`. Stdio-тест із SDK-клієнтом, що реалізує callback elicitation.

Verification:

```text
python scripts/tests/test_eif_mcp_writes.py
python scripts/tests/test_eif_mcp_stdio.py
python scripts/tests/test_session_commands.py
python scripts/eif_privacy_scan.py
```

Нові файли тестів назвати за конвенцією. Exit: усі негативні сценарії зелені; кожен виправлений під час сесії дефект має тест, що падає без виправлення; `tools/list` режиму writer ≤ 9 216 байт або рішення; `eif_capabilities` повертає чесні мітки enforcement (`owner_gate`, `instruction_only` для межі делегата).

## Session 007 - Render, адаптери, компактний блок

Залежності: SESSION-006 (гілка A) або SESSION-005 (гілка B).

1. Гілка A: `eif_render_prepare` і шлях commit для `knowledge-delta.md` та `session-closeout.md`, тести перегляду, перезапису (`force` видно в preview) і відмови.
2. Завжди: записи `mcp_client` у `adapters/parity-matrix.json` зі статусами S5, оновлення чотирьох adapter README і `adapters/README.md`, тест парності.
3. Якщо G1c пройдено: слот `integrations.eif_mcp` у схемі конфігу (типово вимкнений), генератор компактного блока для чотирьох адаптерів і двох мов, запасний шлях, marker і drift тести, перемикання `enabled` через `eifctl upgrade` і відкат, стан слота в doctor, `eifctl mcp serve --self-test`.
4. Виміряти фактичний footprint "після" скриптом і замінити `INFERRED` числа в таблиці виміряними.
5. Уточнити рядок README (`Experimental`/`Available`) за станом доказів.

Verification:

```text
python scripts/tests/test_parity_matrix.py
python scripts/tests/test_init.py
python scripts/tests/test_journey.py
python scripts/tests/test_verify_runtime.py
python scripts/tests/test_locale.py
python scripts/tests/test_codex_adapter.py
python scripts/tests/test_cursor_adapter.py
python scripts/tests/test_hermes_adapter.py
python scripts/eif_context_footprint.py --mcp-after --check docs/benchmarks/context-footprint/after.json
python scripts/sync_package_sources.py --check
python scripts/eif_privacy_scan.py
```

Exit: тести адаптерів і мов зелені з вимкненим і з увімкненим слотом; компактний блок (якщо постачається) ≤ 2 400 байт і має працюючий запасний шлях; "після" виміряно, а не оцінено; render-інструменти (гілка A) проходять негативні тести; статус у README відповідає доказам.

## Session 008 - Closeout

Залежності: SESSION-007.

1. `git fetch`, rebase, перевірка записів D-22 і D-23 реєстру, якщо реліз 0.2.9 уже злито (D-020).
2. Повна локальна перевірка: `run_all.py`, тести wheel, ліцензійний контур, `sync --check`, privacy, links, frontmatter, line endings.
3. Аудит тверджень у документації: пошук слів про економію, "дешевше", "Available", enforcement; кожне має доказ або видаляється.
4. Фінальна таблиця footprint і вердикти G1, G1c, G2; статус eval-питань (`NOT RUN`); статус canary по клієнтах.
5. Knowledge Delta, пропозиції `provisional` рішень реєстру (D-020), `07-CLOSEOUT`, запис `CHANGELOG.md` `Unreleased`.
6. Чесний фінальний статус: `completed-local` або `implementation-complete-integration-deferred` (гілка B), перелік дій власника.

Verification:

```text
python scripts/tests/run_all.py
python scripts/eif_check_licenses.py --environment
python scripts/sync_package_sources.py --check
python scripts/eif_privacy_scan.py
python scripts/eif_check_links.py
python scripts/eif_validate_frontmatter.py
git diff --check
git status --short
```

Exit: `07-CLOSEOUT` заповнено з PASS/FAIL по кожній команді, фінальний статус чесний, перелічено `deferred` і дії власника, жодного push чи PR, `git status` чистий після commit.

## Відповідність правилам власника для MCP-серверів (чек-лист із 13 пунктів)

| # | Перевірка | Сесія і спосіб |
|---|---|---|
| C1 | Один явний корінь на процес | S3, S4: D-002, негативні тести старту |
| C2 | Класи ефекту й annotations | S3, S6: каталог JSON і тест на явні annotations |
| C3 | Немає generic execute/sql/write | S3, S6: тест каталогу проти забороненого списку імен і полів-шляхів |
| C4 | Brief за замовчуванням, деталі окремо | S3: `eif_brief` і `eif_artifact_get` |
| C5 | Явні межі, `truncated` не маскується | S3, S4: тести великого результату |
| C6 | Словник статусів, відсутність не плутається з partial | S3, S4: тести недоступного джерела |
| C7 | Типізовані помилки без витоку | S3, S4, S6: негативні тести |
| C8 | Ідемпотентність і receipt для кожного запису | S6 |
| C9 | Довгі задачі через start/status/result | Не застосовується: усі операції короткі (дедлайни D-006), довгих задач немає. Записано в closeout |
| C10 | Версія збірки і джерело коду видимі | S3: `eif_capabilities` (версії, drift) |
| C11 | Розмір `tools/list` виміряно | S1 (проба), S3, S5, S6 |
| C12 | Приклад конфігурації, резервна копія, відкат | S4: шаблони й guide (EIF не змінює конфіг; відкат це видалення запису користувачем) |
| C13 | Canary зі справжнього клієнта | S5, обмежено O-6 |

## Definition-of-done cross-check

| DoD | Сесія |
|---|---|
| DD-01 вимір footprint | S1 (скрипт, B0), S5, S7, S8 |
| DD-02 структурований шар, golden | S2 |
| DD-03 9 інструментів, annotations, бюджет `tools/list` | S3, S4 |
| DD-04 один явний корінь | S3, S4 |
| DD-05 статуси, помилки, межі | S3, S4 |
| DD-06 справжній SDK, wheel з extra і без | S4 |
| DD-07 пакування, ліцензії, sync, CHANGELOG | S4, S8 |
| DD-08 ворота G1, статуси клієнтів | S5 |
| DD-09 10 eval-питань | S4, S5 |
| DD-10 протокол схвалення (або гілка B) | S6, S5 (вибір гілки), S8 |
| DD-11 render через MCP | S7 |
| DD-12 компактний блок, виміряне "після" | S7, S8 |
| DD-13 чесність тверджень | S4, S7, S8 |
| DD-14 межі доведені | S3, S4, S6 |
| DD-15 Knowledge Delta, closeout | S8 |
| DD-16 жодної owner-only дії | усі, перевірка в S8 |
