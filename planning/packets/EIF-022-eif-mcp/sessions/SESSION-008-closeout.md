---
id: SESSION-008
logical_session: SESSION-008
type: session-launch
status: completed
source_artifact: ../04-ROADMAP-022-eif-mcp.md
session_context: .session-context/eif-022-session-008.md
continuation_mode: same_chat
depends_on: [SESSION-007]
---

# SESSION-008: closeout

## Goal

Незалежно перевірити весь результат пакета свіжими запусками, виправити твердження, що перевищують докази, записати Knowledge Delta і пропозиції `provisional` рішень, заповнити `07-CLOSEOUT` чесним статусом. Остання сесія пакета.

## Required reading order

1. Усі файли пакета 00-06 і чекпойнти та closeout-нотатки сесій 001-007.
2. [07-CLOSEOUT](../07-CLOSEOUT-022-eif-mcp.md) (шаблон) і `templates/packet-closeout.md`, `templates/knowledge-delta.md`, `playbooks/execution-packet-review.md`, `playbooks/session-closeout.md`.
3. `core/policies/decisions.md` на актуальному `origin/main` (для номерів нових записів).

## Experience retrieval preflight

Пошук за "closeout", "knowledge delta", "mcp", "footprint", "canary" у `docs/`, `planning/`, `adapters/`. Записати, що знайдено.

## Scope

- `git fetch --all --prune`, rebase на `origin/main`, перегляд D-22/D-23 релізу 0.2.9, якщо вже злиті (D-020).
- Повна локальна перевірка, кожна команда з результатом PASS/FAIL.
- Аудит тверджень: пошук у `README.md`, `docs/`, `integrations/`, `adapters/`, `CHANGELOG.md` слів про економію, "дешевше", "швидше", "Available", "enforced"; кожне має доказ у виводі команди або видаляється.
- Фінальна таблиця footprint і вердикти G1, G1c, G2; статус eval-питань; статус canary по клієнтах.
- Knowledge Delta (за `templates/knowledge-delta.md`).
- Пропозиції `provisional` записів у `core/policies/decisions.md` (D-020): eif-mcp як необов'язковий адаптер на інстанс і словник статусів файла запуску. Номери беруться з актуального `main`.
- `07-CLOSEOUT-022-eif-mcp.md`, `CHANGELOG.md` секція `Unreleased`.

## Out of scope / do not touch

- Редагування ratified записів реєстру.
- Версія пакета, дата релізу, tag, PyPI, publish.
- Push, PR, merge, зміна видимості, hosted CI.
- Нова функціональність. Якщо перевірка знаходить дефект, виправити його з тестом, що падає без виправлення, або записати `deferred` із причиною.
- Живі конфігурації клієнтів, виклики моделі понад O-6.

## Verification

```text
python scripts/tests/run_all.py
python scripts/eif_check_licenses.py --environment
python scripts/sync_package_sources.py --check
python scripts/eif_privacy_scan.py
python scripts/eif_check_links.py
python scripts/eif_validate_frontmatter.py
python scripts/eif_context_footprint.py --mcp-after --no-latency --check docs/benchmarks/context-footprint/after.json
git diff --check
git status --short
```

Додатково: тест установленого wheel з extra і без (команди з SESSION-004), повторений на фінальному дереві.

## Bounded loop contract

not needed - завершальна перевірка без ітеративного циклу. Якщо перевірка дає FAIL, виправити й повторити не більше трьох разів, потім повернути звіт із відкритими питаннями.

## Exit criteria

- [x] `07-CLOSEOUT-022-eif-mcp.md` заповнено: план проти факту по сесіях, таблиця команд PASS/FAIL, `deferred` із причинами, дії власника.
- [x] Фінальний статус чесний: `completed-local`, або `implementation-complete-integration-deferred` (гілка B), або `blocked` (гілка C).
- [x] Кожне твердження в документації має доказ; токенових тверджень про економію немає.
- [x] Knowledge Delta заповнено; довговічний урок про MCP-адаптери або записано, або прямо сказано, що його немає.
- [x] `provisional` пропозиції додано без редагування ratified записів.
- [x] Жодного push, PR, merge, release; `git status` чистий після commit; основну копію репозиторію не змінено.

## Closeout / Knowledge Delta

Це і є closeout. Окремо в Next action вказати власнику: рішення про публікацію гілки, бюджет на поведінкове порівняння D-19 і на canary-ходи (O-6), ратифікацію `provisional` записів.

## Execution record

Final canonical inventory54/54 and2130/2130, no unknown/mismatched suites.
Installed base/extra wheel14/14, exhaustive packaging79/79, package smoke13/13,
main smoke49/49. License contours,203synced sources, links, frontmatter and
final byte-identical footprint PASS. New prose/proposal claims were checked
through JEV before acceptance (3auto); broad earlier patch review was resolved
manually with boundary regressions. Final status is implementation-complete-
integration-deferred, branchB. No host model canary or evaluation ran.
