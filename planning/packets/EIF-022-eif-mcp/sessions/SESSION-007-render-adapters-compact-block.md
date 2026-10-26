---
id: SESSION-007
logical_session: SESSION-007
type: session-launch
status: prepared
source_artifact: ../04-ROADMAP-022-eif-mcp.md
session_context: .session-context/eif-022-session-007.md
continuation_mode: same_chat
depends_on: [SESSION-006]
---

# SESSION-007: render, адаптери, компактний блок

## Goal

Завершити інтеграцію: render-інструменти (гілка A), записи `mcp_client` у parity-matrix для чотирьох адаптерів і, якщо пройдено G1c, опційний компактний блок entrypoint із робочим запасним шляхом та виміряним footprint "після".

## Умова початку

Гілка A: після SESSION-006. Гілка B: SESSION-006 пропущено, залежність фактично SESSION-005; render-інструменти не робляться. Гілка C: сесія не виконується.

## Required reading order

1. Файли пакета 00-04 і closeout SESSION-005 та SESSION-006 (якщо виконувалась).
2. [03-DECISIONS](../03-DECISIONS-022-eif-mcp.md) D-009, D-014, D-015, D-017.
3. `scripts/eif_init.py` (генерація блока, marker-логіка), `scripts/eif_adapters.py`, `scripts/eif_markers.py`, `core/schemas/eif-config.schema.json`, `scripts/eif_verify_runtime.py` (перевірка block drift), `locales/`.
4. `adapters/parity-matrix.json`, `adapters/README.md`, чотири adapter README.
5. Перелік тестів адаптерів: `test_init.py`, `test_journey.py`, `test_codex_adapter.py`, `test_cursor_adapter.py`, `test_hermes_adapter.py`, `test_parity_matrix.py`, `test_verify_runtime.py`, `test_locale.py`.

## Experience retrieval preflight

Пошук за "marker", "generated block", "drift", "entrypoint size budget", "locale invariant" у `docs/`, `planning/`, `adapters/`. Записати, що знайдено.

## Scope

- Гілка A: `eif_render_prepare` (knowledge-delta, session-closeout) і шлях commit, тести перегляду, перезапису (прапорець `force` видно в preview) та відмови.
- Завжди: запис `mcp_client` у `adapters/parity-matrix.json` (статус, версія клієнта, `evidence_status`, дія) зі статусами SESSION-005; оновлення тесту парності та README адаптерів.
- Якщо G1c пройдено: слот `integrations.eif_mcp` у схемі конфігу (типово вимкнений, відсутній дорівнює вимкненому), генерація компактного блока ≤ 2 400 байт для чотирьох адаптерів і двох мов із запасним шляхом, marker і drift тести, перемикання `enabled` через `eifctl upgrade` і відкат, стан слота в doctor, `eifctl mcp serve --self-test`.
- Вимір "після" скриптом footprint і заміна оцінок `INFERRED` виміряними значеннями.
- Рядок статусу eif-mcp у README за станом доказів.

## Out of scope / do not touch

- Зміна поведінки згенерованих блоків, коли слот вимкнений або відсутній: вони мають лишитись побайтово тими самими (golden-тест).
- Ratified рішення реєстру; нові framework-рішення лише як пропозиції в SESSION-008.
- Висновок про економію токенів. Тільки статичний footprint з методом.
- Зміни живих конфігурацій клієнтів і hooks.
- Версія пакета, release, tag, PyPI.

## Verification

```text
python scripts/tests/test_parity_matrix.py
python scripts/tests/test_init.py
python scripts/tests/test_journey.py
python scripts/tests/test_verify_runtime.py
python scripts/tests/test_locale.py
python scripts/tests/test_codex_adapter.py
python scripts/tests/test_cursor_adapter.py
python scripts/tests/test_hermes_adapter.py
python scripts/tests/test_eif_mcp_writes.py
python scripts/eif_context_footprint.py --mcp-after --no-latency --check docs/benchmarks/context-footprint/after.json
python scripts/sync_package_sources.py --check
python scripts/eif_privacy_scan.py
python scripts/eif_check_links.py
python scripts/eif_validate_frontmatter.py
git diff --check
```

## Bounded loop contract

- `success_evidence`: golden-тест незмінного блока при вимкненому слоті; компактний блок проходить marker/drift перевірки в чотирьох адаптерах і двох мовах; "після" виміряно.
- `evaluator`: команди вище.
- `max_iterations`: 4.
- `remote_run_budget`: 0.
- Стоп: компактний блок не вкладається в 2 400 байт зі збереженням запасного шляху (записати, не постачати блок, продовжити без нього); зміна схеми конфігу ламає наявні інстанси без безпечної міграції.
- Checkpoint: `.session-context/eif-022-session-007.md`.

## Exit criteria

- [ ] Тести адаптерів і мов зелені з вимкненим і з увімкненим слотом.
- [ ] При вимкненому слоті вивід генерації блоків побайтово незмінний (golden).
- [ ] Компактний блок (якщо постачається) ≤ 2 400 байт, має працюючий запасний шлях, відкат перевірено.
- [ ] Виміряне "після" замінило оцінку в таблиці; регрес `light` названо.
- [ ] Render-інструменти (гілка A) проходять негативні тести.
- [ ] `mcp_client` записи відповідають доказам SESSION-005; жодне `verified` без збереженого журналу.
- [ ] Закомічено локально.

## Closeout / Knowledge Delta

Записати: фактичний розмір компактного блока, чи довелось залишити запасний шлях довшим за прогноз, вплив на `eifctl upgrade`, і прямо сказати, якщо довговічного уроку немає.
