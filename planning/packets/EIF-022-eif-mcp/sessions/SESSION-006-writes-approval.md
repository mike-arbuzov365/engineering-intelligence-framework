---
id: SESSION-006
logical_session: SESSION-006
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-022-eif-mcp.md
session_context: .session-context/eif-022-session-006.md
continuation_mode: same_chat
depends_on: [SESSION-005]
---

# SESSION-006: фаза 2, протокол схвалення, checkpoint і evidence

## Goal

Реалізувати режим `--writes` із п'ятьма інструментами D-009 і протоколом схвалення D-010 так, щоб модель не могла схвалити власний запис, кожен запис був одноразовим, прив'язаним до subject, ідемпотентним і мав receipt.

## Умова початку

Виконується лише у гілці A (G1 і G2 пройдені, записано в SESSION-005). У гілках B і C сесію не виконувати: записати у checkpoint `deferred` із причиною, перейти до SESSION-007 за її умовами гілки.

## Required reading order

1. Файли пакета 00-04 і closeout SESSION-005 (вердикти воріт, поведінка elicitation по клієнтах).
2. [03-DECISIONS](../03-DECISIONS-022-eif-mcp.md) D-009, D-010, D-011, D-012, D-018.
3. `commands/session.py` (атомарний запис, регулярний вираз `session_id`), `service/session.py`, `scripts/eif_render.py`.
4. Довідка SDK v2 про elicitation з боку сервера (форма запиту, результат `accept`/`decline`/`cancel`, таймаут).
5. `playbooks/execution-packet-execution.md` Step 4 і правило делегування воркспейса, якщо воно відображене в проєкті.

## Experience retrieval preflight

Пошук за "approval", "owner_gate", "idempotency", "receipt", "atomic" у `docs/`, `planning/`, `core/policies/`, і в чекпойнтах SESSION-005. Записати, що знайдено.

## Scope

- `eif_mcp/{subjects,approval,receipts,tools_write}.py`, оновлення `catalog.json`, опису режимів reader/writer.
- Prepared-subject у пам'яті: канонічний JSON, `subject_sha256`, `subject_id`, TTL 600 с, одноразовість.
- `eif_commit`: перечитування стану, `version_conflict`, `stale`, запит elicitation з таймаутом 120 с, `requires_host_action`, `approval_declined`.
- Intent, атомарний запис цілі, receipt, `audit.jsonl` без вмісту, `eif_operation_get`, ідемпотентність.
- `eif_checkpoint_prepare`, `eif_evidence_prepare` над `session_checkpoint_plan/apply`.
- Тести `scripts/tests/test_eif_mcp_writes.py` (in-memory і stdio із SDK-клієнтом, що реалізує callback elicitation).
- Оновлення `docs/guides/eif-mcp.md` для режиму writer (без тверджень про enforcement понад `owner_gate` з обмеженнями).

## Out of scope / do not touch

- `eif_render_prepare` і render-запис (SESSION-007).
- Будь-який запасний "файловий" шлях схвалення (відхилено в D-010 п. 4).
- Читальні інструменти (лише виправлення дефектів із тестом).
- `adapters/`, компактний блок, схема конфігурації.
- Запис у будь-яку ціль, окрім `.session-context/<session_id>.md`.
- Живі конфігурації клієнтів, виклики моделі понад O-6.

## Verification

```text
python scripts/tests/test_eif_mcp_writes.py
python scripts/tests/test_eif_mcp_stdio.py
python scripts/tests/test_eif_mcp_inmemory.py
python scripts/tests/test_session_commands.py
python scripts/tests/test_service_golden.py
python scripts/sync_package_sources.py --check
python scripts/eif_privacy_scan.py
python scripts/eif_check_links.py
git diff --check
```

## Bounded loop contract

- `success_evidence`: усі негативні сценарії D-016/D-010 зелені; повтор того самого запиту не дає другого запису; інжекція збою на кожному з трьох кроків запису дає однозначний результат `eif_operation_get`.
- `evaluator`: команди вище.
- `max_iterations`: 4.
- `remote_run_budget`: 0.
- Стоп: SDK не дає серверу надійного способу очікувати elicitation з таймаутом (тоді гілка B і повернення звіту); виявлено шлях, яким модель може викликати commit без схвалення людини (це P0, зупинитись і записати, не маскувати).
- Checkpoint: `.session-context/eif-022-session-006.md`.

## Exit criteria

- [ ] Вхідні схеми не містять жодних полів схвалення, а зайві поля дають `validation_failed` (тест).
- [ ] Повтор, підроблений чи протермінований `subject_id`, дрейф цілі й інстанса, паралельні commit, відсутність elicitation, decline, cancel, таймаут, `idempotency_conflict`, траверсал у `session_id`, збої між кроками запису: усе покрито негативними тестами.
- [ ] Для кожного дефекту, виправленого в сесії, є тест, що падає без виправлення.
- [ ] Без `--writes` каталог містить лише 9 інструментів і запис неможливий (тест).
- [ ] `tools/list` режиму writer ≤ 9 216 байт або рішення.
- [ ] `eif_capabilities` повертає чесні мітки: `owner_gate` із залежністю від клієнта, межа делегата `instruction_only`.
- [ ] Закомічено локально.

## Closeout / Knowledge Delta

Записати: фактичні відмінності поведінки elicitation від очікуваних, довгі виклики або таймаути, які спостерігались, виявлені слабкі місця протоколу, і прямо сказати, якщо довговічного уроку немає.
