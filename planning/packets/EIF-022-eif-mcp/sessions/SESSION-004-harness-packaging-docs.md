---
id: SESSION-004
logical_session: SESSION-004
type: session-launch
status: completed
source_artifact: ../04-ROADMAP-022-eif-mcp.md
session_context: .session-context/eif-022-session-004.md
continuation_mode: same_chat
depends_on: [SESSION-003]
---

# SESSION-004: харнес, пакування, документація фази 1

## Goal

Довести сервер фази 1 тестом через справжній SDK по stdio і тестом установленого wheel з extra і без, закрити ліцензійний контур і пакування, написати чесну документацію та шаблони конфігурації, підготувати 10 eval-питань `mcp-builder` без запуску моделі.

## Required reading order

1. Файли пакета 00-04 і closeout SESSION-003.
2. [03-DECISIONS](../03-DECISIONS-022-eif-mcp.md) D-013, D-015, D-016, D-017.
3. `scripts/eif_check_licenses.py`, `core/policies/license-policy.json`, `THIRD_PARTY_NOTICES.md`, `sbom.cdx.json`, `scripts/tests/test_package_build.py`, `test_package_smoke.py`, `test_check_licenses.py`.
4. `integrations/vendor-docs/` (зразок генерованих шаблонів `installed: false`), `scripts/eif_generate_vendor_docs_guidance.py`, `scripts/tests/test_vendor_docs_integration.py`.
5. `mcp-builder`: `reference/evaluation.md` для формату питань. Скрипти скіла не запускати.

## Experience retrieval preflight

Пошук за "wheel", "extra", "sbom", "license", "template drift", "vendor-docs" у `docs/` і `planning/`, чекпойнтах попередніх сесій. Записати, що знайдено.

## Scope

- Stdio-харнес: `scripts/tests/test_eif_mcp_stdio.py` (підпроцес `eifctl mcp serve`, справжній SDK-клієнт, негативна матриця D-016 п. 3, тиша stdout, kill, EOF).
- Тести установленого wheel з extra і без; регресія бази.
- Ліцензійний контур extra: `sbom-mcp.cdx.json`, розділ у `THIRD_PARTY_NOTICES.md`, тести контуру, запуск `eif_check_licenses.py --environment` у чистому venv з extra.
- `integrations/eif-mcp/` (README, manifest, `generated/<adapter>.json` у режимах reader і writer), генератор за зразком vendor-docs і тест дрейфу. Формат конфігурації Hermes перевірити довідкою його CLI.
- `docs/guides/eif-mcp.md`, рядок у таблиці можливостей `README.md` (`Experimental`), точкові уточнення в `integrations/vendor-docs/README.md`, `integrations/README.md`, `docs/architecture/HOW-EIF-WORKS.md`, запис у `CHANGELOG.md` секції `Unreleased`; `python scripts/sync_package_sources.py`.
- `docs/benchmarks/mcp-eval/`: 10 питань XML, README зі статусом `NOT RUN`, детермінований скрипт перевірки відповідей через in-memory клієнт.

## Out of scope / do not touch

- Інструменти запису (SESSION-006), компактний блок (SESSION-007), `adapters/parity-matrix.json` (SESSION-007).
- Зміна семантики сервера, окрім виправлення дефектів із тестом, що падає без виправлення.
- Версія пакета, дата релізу, tag, PyPI, hosted CI.
- Запуск скриптів `mcp-builder`, виклики моделі, зміна живої конфігурації клієнтів.
- Твердження про економію токенів у будь-якому тексті.

## Verification

```text
python scripts/tests/test_eif_mcp_stdio.py
python scripts/tests/test_eif_mcp_inmemory.py
python scripts/tests/test_package_build.py
python scripts/tests/test_package_smoke.py
python scripts/tests/test_check_licenses.py
python scripts/eif_check_licenses.py --environment
python scripts/sync_package_sources.py --check
python scripts/eif_check_links.py
python scripts/eif_validate_frontmatter.py
python scripts/eif_privacy_scan.py
git diff --check
```

## Bounded loop contract

- `success_evidence`: stdio-харнес і тест wheel зелені з extra і без; ліцензійний контур проходить; усі нові посилання валідні.
- `evaluator`: команди вище.
- `max_iterations`: 4.
- `remote_run_budget`: 0.
- Стоп: залежність extra має ліцензію поза політикою (записати, нічого не додавати до SBOM, повернути власнику); чисте установлення з extra не складається на жодній підтримуваній версії Python.
- Checkpoint: `.session-context/eif-022-session-004.md`.

## Exit criteria

- [x] Stdio-харнес зелений, включно з усією негативною матрицею.
- [x] Wheel з extra експонує `eifctl mcp serve`; wheel без extra працює як раніше, `mcp serve` дає код 2 і підказку.
- [x] Ліцензійний контур extra чистий; `sync --check`, links, frontmatter, privacy чисті.
- [x] Шаблони конфігурації проходять тест дрейфу й мають `installed: false`.
- [x] 10 eval-питань мають перевірені відповіді та явний статус `NOT RUN`.
- [x] Документація не містить тверджень про економію токенів чи enforcement без доказу.
- [x] Закомічено локально.

## Closeout / Knowledge Delta

Записати: що стояло на шляху пакування extra, формат конфігурації Hermes (або що він не підтверджений), які формулювання "EIF не говорить MCP" довелось уточнити, і прямо сказати, якщо довговічного уроку немає.

## Execution record

Stdio27/27; isolated extra/base wheel12/12; exhaustive package79/79; isolated package smoke13/13; contracts29/29; expected answers10/10 without a model. License contour41runtime components, Python3.11 clean environment PASS. Hermes0.21.3 format is YAML/mcp_servers. Client canaries NOT RUN. No writer config entry is executable.
