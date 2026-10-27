---
id: SESSION-005
logical_session: SESSION-005
type: session-launch
status: completed
source_artifact: ../04-ROADMAP-022-eif-mcp.md
session_context: .session-context/eif-022-session-005.md
continuation_mode: same_chat
depends_on: [SESSION-004]
---

# SESSION-005: ворота G1, canary клієнтів, вимір "після"

## Goal

Незалежно перевірити фазу 1, виміряти footprint "після" тим самим скриптом, що й B0, зібрати canary реальних клієнтів в межах дозволеного бюджету, обчислити вердикти G1, G1c, G2 за D-017 і вибрати гілку виконання (A, B, C) за D-019.

## Required reading order

1. Файли пакета 00-04 і closeout SESSION-004.
2. [03-DECISIONS](../03-DECISIONS-022-eif-mcp.md) D-010, D-014, D-015, D-016, D-017, D-019 і Open O-1, O-3, O-6.
3. `docs/benchmarks/context-footprint/` (B0), `docs/guides/eif-mcp.md`, `integrations/eif-mcp/`.
4. `adapters/README.md` і `adapters/*/README.md` про версії клієнтів та спосіб виявлення інструкцій.

## Experience retrieval preflight

Пошук за "canary", "elicitation", "client version", "configured-not-verified" у `docs/`, `adapters/`, `planning/`. Записати, що знайдено.

## Scope

- Повторний повний прогін тестів фази 1 і оцінка власних findings за каталогом P0..P3. Відкриті P0/P1 виправляти до трьох ітерацій (кожне виправлення з тестом, що падає без нього).
- Режим `--mcp-after` у `scripts/eif_context_footprint.py`: скрипт керує in-memory клієнтом на синтетичному інстансі й вимірює `tools/list`, типові відповіді `eif_brief` та секційні читання `eif_artifact_get` для читань, потрібних сценарію. Компактний блок до SESSION-007 рахується як бюджет і чесно позначається `INFERRED`.
- Canary клієнтів (Claude Code, Codex, Cursor, Hermes): версія, форма конфігурації, перевірка з'єднання без ходу моделі там, де клієнт має таку команду; виклик інструмента й elicitation-цикл через тестовий probe-сервер лише в межах дозволеного O-6. Журнали санітувати й зберегти в `docs/benchmarks/eif-mcp-canary/`.
- Тестовий probe-сервер `scripts/tests/fixtures/eif_mcp/elicit_probe_server.py` (не постачається).
- Вердикти G1, G1c, G2 та вибір гілки, записані в `docs/benchmarks/context-footprint/` і checkpoint.

## Out of scope / do not touch

- Живі конфігураційні файли клієнтів у домашньому каталозі користувача. Canary виконувати лише через одноразову конфігурацію на виклик, тимчасовий домашній каталог або перемикач клієнта. Якщо клієнта неможливо перевірити без редагування живої конфігурації, записати `configured-not-verified` і причину, не редагувати.
- Інструменти запису (SESSION-006), компактний блок (SESSION-007).
- Платні виклики моделі понад дозволене O-6. Типове O-6 = 0: тоді виклик інструмента й elicitation-цикл не запускаються, статуси `configured-not-verified`, G2 не пройдено.
- Computer Use без попереднього питання власнику.
- Зміни README-статусу вище `Experimental`.

## Verification

```text
python scripts/tests/run_all.py
python scripts/eif_context_footprint.py --mcp-after --no-latency --check docs/benchmarks/context-footprint/after.json
python scripts/eif_privacy_scan.py
python scripts/eif_check_links.py
python scripts/eif_validate_frontmatter.py
git diff --check
```

## Bounded loop contract

- `success_evidence`: усі тести фази 1 зелені; "після" відтворюється двічі побайтово; вердикти G1, G1c, G2 записані з командами або `NOT RUN` з причиною.
- `evaluator`: команди вище плюс розрахунок критеріїв D-017 скриптом, а не вручну.
- `max_iterations`: 3.
- `remote_run_budget`: 0 (canary-ходи моделі лише в межах O-6).
- Стоп: у журналі canary виявлено секрет або приватні дані без безпечного виправлення; для canary потрібне редагування живої конфігурації; після трьох ітерацій лишається відкритий P0/P1 (гілка C).
- Checkpoint: `.session-context/eif-022-session-005.md`.

## Exit criteria

- [x] Вердикт G1 записаний (команди, числа). Якщо не пройдено після трьох ітерацій, обрано гілку C і повернено звіт з відкритими питаннями.
- [x] Вердикт G1c записаний із числами "до" (B0) і "після" та обліком найгіршого випадку; регрес `light` названо.
- [x] Вердикт G2 записаний (доказ elicitation або `NOT RUN`/не пройдено з причиною).
- [x] Статус кожного клієнта один із `verified`, `configured-not-verified`, `not-available` з версією клієнта.
- [x] Гілку (A, B, C) обрано й записано; інструкція наступної сесії відповідає гілці.
- [x] Санітовані журнали не містять шляхів машини, секретів, приватних даних; privacy-скан чистий; закомічено локально.

## Closeout / Knowledge Delta

Записати: чи хост відкладає схеми інструментів (O-3) і як це спостережено, реальну підтримку elicitation по клієнтах, виміряну різницю "до і після", і чесний висновок, чи підтверджена гіпотеза про секційні читання. Якщо ні, сказати прямо.

## Execution record

G1 PASS: 52/52 suites, 2031/2031 checks; the newly registered structured
design-guard suite passes 4/4 independently. Core41/41, in-memory55/55,
stdio27/27, original CLI goldens26/26. Before/after reproduction3/3 confirms
Git-include rejection, non-string status handling and diagnostic redaction.
G1c candidate PASS with the 2400-byte entrypoint budget; protocol measurements
including outline discovery repeat byte-for-byte. G2 NOT PASSED: O-6=0.
Branch B; SESSION-006 and render work defer to EIF-022b. Client versions and
NOT RUN statuses are in docs/benchmarks/eif-mcp-canary/clients.json.
