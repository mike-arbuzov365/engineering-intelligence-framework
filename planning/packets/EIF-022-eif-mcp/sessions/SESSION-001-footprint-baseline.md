---
id: SESSION-001
logical_session: SESSION-001
type: session-launch
status: completed
source_artifact: ../04-ROADMAP-022-eif-mcp.md
session_context: .session-context/eif-022-session-001.md
continuation_mode: same_chat
depends_on: []
---

# SESSION-001: базова лінія footprint, бюджети, життєздатність залежності

## Goal

Зробити вимір статичного контекстного footprint частиною репозиторію (скрипт, тест, зафіксована лінія B0), підтвердити або виправити бюджети D-006 і D-017 на актуальному `origin/main` та довести в чистому середовищі, що залежність `mcp` v2 встановлюється поруч із базою EIF і поводиться так, як припускає пакет.

## Required reading order

1. Файли пакета 00-04 у числовому порядку. Особливо [02-FACTS](../02-FACTS-022-eif-mcp.md) розділ 2 і [03-DECISIONS](../03-DECISIONS-022-eif-mcp.md) D-006, D-013, D-017.
2. `AGENTS.md`, `docs/benchmarks/README.md`, `core/policies/decisions.md`.
3. [evidence/measure_baseline.py](../evidence/measure_baseline.py) і [evidence/baseline-2026-10-26.json](../evidence/baseline-2026-10-26.json).
4. Для довідки SDK: документація MCP Python SDK v2 (через Context7), розділи про `MCPServer`, annotations, structured output, `stdio_server`, elicitation.

Логічна сесія може тривати кілька фізичних чатів. Перед передачею керування оновити й провалідувати `session_context` (`python -m engineering_intelligence_framework.cli session checkpoint ...` або `eifctl session checkpoint ...`). Native-підсумок чату не є authority.

## Experience retrieval preflight

У репозиторії фреймворку немає каталогу `knowledge/`, тому `scripts/eif_search_knowledge.py` не має що індексувати. Виконати пошук за "token", "footprint", "benchmark", "mcp" у `docs/` і `planning/` (звичайним пошуком за текстом) і записати знайдене або що нічого релевантного немає. Не пропускати цей крок як рутинний.

## Scope

- `scripts/eif_context_footprint.py`: перенесення логіки з evidence-скрипта; детермінований вивід у режимі `--no-latency`; лише відносні шляхи; режим `--check <baseline.json>` порівнює байти з закоміченою лінією і повертає ненульовий код при розбіжності.
- `scripts/tests/test_context_footprint.py` за конвенцією репозиторію (один рядок `EIF-RESULT: passed=<P> total=<T>`) і запис у `SUITES` у `scripts/tests/run_all.py`.
- `docs/benchmarks/context-footprint/README.md` і `baseline.json` (B0 зі SHA джерела); посилання з `docs/benchmarks/README.md`.
- Перевимірювання B0 на актуальному `origin/main` і запис різниці до лінії 2026-10-26.
- Перевірка залежності в чистому venv (Python 3.11 і 3.12, якщо доступні, інакше записати, яких немає) і одноразова проба сервера поза репозиторієм.
- Закріплення версії SDK і, за потреби, новий запис у [03-DECISIONS](../03-DECISIONS-022-eif-mcp.md) (наступний вільний номер пакета, який посилається на замінюване рішення), якщо виявлено відхилення від припущень.

## Out of scope / do not touch

- `src/engineering_intelligence_framework/` (жодного нового коду продукту), `pyproject.toml`, `cli.py`.
- `adapters/`, `templates/`, `playbooks/`, `skills/`, `core/`, `integrations/`.
- Будь-яка зміна поведінки наявних команд.
- Проба сервера не комітиться й не потрапляє в репозиторій.
- Жодних запусків моделі, жодних зовнішніх викликів, окрім завантаження пакетів у тимчасове venv.

## Verification

```text
python scripts/tests/test_context_footprint.py
python scripts/eif_context_footprint.py --no-latency --check docs/benchmarks/context-footprint/baseline.json
python scripts/eif_check_links.py
python scripts/eif_privacy_scan.py
python scripts/sync_package_sources.py --check
git diff --check
```

Додатково у чистому venv: `pip install` бази і `mcp` v2, `pip check`, круговий виклик проби SDK-клієнтом по stdio. Команди й результати записати в checkpoint.

## Bounded loop contract

- `success_evidence`: скрипт двічі дає ідентичний вивід у режимі `--no-latency`; `--check` ловить штучно змінений байт у лінії; `pip check` чистий; проба проходить круговий виклик.
- `evaluator`: команди вище.
- `max_iterations`: 3.
- `remote_run_budget`: 0.
- Стоп: SDK не встановлюється поруч із базою EIF без конфлікту (записати конфлікт і повернути звіт власнику з варіантами), або вимір дає розбіжність понад 10 % з лінією 2026-10-26 без пояснення.
- Checkpoint: `.session-context/eif-022-session-001.md` (gitignored).

## Exit criteria

- [ ] Скрипт у `scripts/` детермінований, тест проходить, запис у `run_all.py`.
- [ ] B0 закомічено зі SHA джерела; різниця до 2026-10-26 записана (або "немає різниці").
- [ ] `pip check` чистий; версія SDK закріплена; поверхня API (annotations, structured output, stdio, elicitation) підтверджена пробою або відхилення записане рішенням.
- [ ] Бюджети D-006 і D-017 підтверджені або замінені новим рішенням із доказом.
- [ ] Privacy, links, sync, `git diff --check` чисті; закомічено локально; основну копію репозиторію не змінено.

## Closeout / Knowledge Delta

Записати: фактичну версію SDK і її API-поверхню, виміряний розмір `tools/list` на інструмент у пробі, чи реліз 0.2.9 змінив B0, і прямо сказати, якщо довговічного уроку немає.
