---
id: SESSION-003
logical_session: SESSION-003
type: session-launch
status: completed
source_artifact: ../04-ROADMAP-022-eif-mcp.md
session_context: .session-context/eif-022-session-003.md
continuation_mode: same_chat
depends_on: [SESSION-002]
---

# SESSION-003: MCP-сервер фази 1

## Goal

Реалізувати `eifctl mcp serve` з дев'ятьма інструментами лише читання як тонким транспортним шаром над service-функціями SESSION-002, з конвертом відповіді, статусами, помилками, межами, дедлайнами й перевіркою drift за D-002, D-003, D-005, D-006, D-018.

## Required reading order

1. Файли пакета 00-04 і closeout SESSION-002 (список функцій і сигнатур).
2. [03-DECISIONS](../03-DECISIONS-022-eif-mcp.md) D-001, D-002, D-003, D-005, D-006, D-012, D-013, D-018.
3. `AGENTS.md` і код `cli.py`, `commands/__init__.py`.
4. Довідка MCP Python SDK v2 (Context7): `MCPServer`, `ToolAnnotations`, structured output, `Client`, `stdio_server`. Довідник скіла `mcp-builder` (`reference/python_mcp_server.md`, `reference/mcp_best_practices.md`) лише як приклад проєктування; його приклади написані під v1 (`FastMCP`), їх перекладати, а не копіювати. Скрипти скіла не запускати.

## Experience retrieval preflight

Пошук за "mcp", "stdout", "stdio", "annotations", "lock", "drift" у `docs/` і `planning/`, а також у чекпойнтах SESSION-001/002. Записати, що знайдено.

## Scope

- `src/engineering_intelligence_framework/eif_mcp/`: `server`, `envelope`, `limits`, `errors`, `containment`, `drift`, `tools_read`, `catalog.json`, журнал у stderr.
- `src/engineering_intelligence_framework/commands/mcp_cmd.py`; реєстрація `mcp` у `cli.py` та її згадка в docstring.
- `pyproject.toml`: optional extra `mcp` за закріпленою в SESSION-001 версією.
- 9 інструментів D-005: явні annotations, описи ≤ 280 символів, без шляхових аргументів, `additionalProperties: false`, повні схеми без зайвих полів `title`, якщо це можливо.
- `--instance-path`, `EIF_INSTANCE_PATH`, `--packets-root`, `--self-test`; коди виходу 0, 2, 3.
- Тести: `scripts/tests/test_eif_mcp_inmemory.py` (in-memory `Client`), побудовник синтетичного інстанса `scripts/tests/fixtures/eif_mcp/`, запис у `run_all.py`.
- Вимір розміру `tools/list`.

## Out of scope / do not touch

- Інструменти запису й `--writes` (SESSION-006).
- Зміни service-логіки, окрім виправлення дефектів із тестом, що падає без виправлення.
- Документація, шаблони конфігурації, README (SESSION-004).
- Компактний блок, `adapters/`, `integrations/`.
- Будь-який імпорт SDK поза пакетом `eif_mcp`.
- Мережеві слухачі, HTTP, OAuth.

## Verification

```text
python scripts/tests/test_eif_mcp_inmemory.py
python scripts/tests/test_package_smoke.py
python scripts/tests/test_service_golden.py
python scripts/sync_package_sources.py --check
python scripts/eif_privacy_scan.py
python scripts/eif_check_links.py
git diff --check
```

Додатково: запуск `eifctl mcp serve` без аргументів і з каталогом без `.eif/` (очікується код 3), у середовищі без SDK (очікується код 2 і підказка без traceback), `eifctl --help` та `eifctl doctor` без SDK як раніше.

## Bounded loop contract

- `success_evidence`: усі in-memory тести 9 інструментів зелені; `tools/list` режиму reader виміряно; поведінка старту за D-002 і D-013 підтверджена.
- `evaluator`: команди вище.
- `max_iterations`: 4.
- `remote_run_budget`: 0.
- Стоп: SDK не дозволяє виразити annotations чи strict-схеми так, як вимагає D-005 (записати, зупинитись і запропонувати нове рішення); `tools/list` перевищує бюджет після двох спроб скорочення описів і схем (записати порушення новим рішенням, а не підвищувати межу мовчки).
- Checkpoint: `.session-context/eif-022-session-003.md`.

## Exit criteria

- [ ] Усі 9 інструментів проходять позитивні й негативні in-memory тести (статуси `ok`, `partial`, `unavailable`, `stale`, `unknown`, `truncated`; `not_found`; `validation_failed` на зайвих полях).
- [ ] Жоден інструмент не приймає шлях; каталог проходить тест проти заборонених імен і полів.
- [ ] `tools/list` reader ≤ 6 144 байти або порушення записане рішенням.
- [ ] Старт без кореня, зі зламаним lock і без SDK поводиться за D-002 і D-013; база без extra працює як раніше.
- [ ] Обробники нічого не пишуть у stdout (перевіряє тест).
- [ ] Закомічено локально; основна копія репозиторію не змінена.

## Closeout / Knowledge Delta

Записати: виміряний `tools/list` у байтах і на інструмент, будь-яку несподіванку API SDK, відмінність дедлайну від фактичного блокування, і прямо сказати, якщо довговічного уроку немає.
