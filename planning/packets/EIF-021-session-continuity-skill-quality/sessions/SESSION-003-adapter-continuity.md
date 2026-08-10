---
id: SESSION-003
type: session-launch
status: prepared-awaiting-owner-approval
source_artifact: ../04-ROADMAP-021-session-continuity-skill-quality.md
session_context: .session-context/eif-021-session-003.md
depends_on: [SESSION-002]
---

# Session 003: стратегії continuation для adapters

## Мета

Додати truthful same-chat, resume і new-chat strategy selection для Claude Code, Codex, Cursor і Hermes.

## Обов'язковий порядок читання

1. Decisions/facts packet і результати Sessions 001-002.
2. `adapters/parity-matrix.json`, adapter overview і чотири READMEs.
3. `scripts/eif_adapters.py`, adapter tests і current vendor docs, наведені у Facts.
4. Current implementation команди session.

## Experience Retrieval Preflight

Знайти adapter evidence щодо hooks, active sources, capability canaries, version boundaries, deep links, resume та user-config mutation.

## У межах session

- Continuity capability records.
- Strategy resolver для `session handoff`.
- Same-chat і exact manual fallback для всіх four adapters.
- Local Codex deep-link open canary та opt-in support, якщо behavior verified.
- Bounded Hermes `session.create` inspection без parallel work.
- Regression tests і компактні generated instructions.

## Поза межами та no-touch zone

- Без Codex App Server integration.
- Без undocumented UI automation.
- Без automatic prompt submission.
- Без hook installation або user-config mutation.
- Без spawned implementation agents.
- Без capability claim лише на основі vendor prose, якщо потрібен local behavior proof.

## Кроки

1. Розширити matrix independent lifecycle capabilities та evidence status.
2. Додати strategy selection tests для всіх modes/capabilities.
3. Генерувати safe encoded Codex link із validated checkpoint і project root.
4. Виконати disposable target-host canary; записати факт open і відсутність prompt send.
5. Перевірити Hermes programmatic create у disposable session лише якщо це не вплине на current work. Застосувати gates P21-10.
6. Залишити Claude Code і Cursor manual, якщо fresh evidence не змінить classification.
7. Перевірити fallback, коли capability absent, stale або canary-failed.

## Перевірка

```text
rtk python scripts/tests/test_adapters.py
rtk python scripts/tests/test_codex_adapter.py
rtk python scripts/tests/test_hermes_adapter.py
rtk python scripts/tests/test_cursor_adapter.py
rtk python scripts/eif_privacy_scan.py
rtk git diff --check
```

Запустити current Claude adapter test filename, якщо він інший, і всі focused continuity tests, додані цією session.

## Контракт bounded loop

- `success_evidence`: strategy matrix дає truthful action для 12 mode/adapter combinations; deep-link parameters мають safe round-trip.
- `evaluator`: tests плюс bounded manual canary evidence.
- `max_iterations`: 3.
- `remote_run_budget`: 0.
- Stop до credential handling, background agent creation, user-config mutation або auto-submit.

## Критерії виходу

- [ ] Same-chat працює для всіх adapters.
- [ ] Manual new-chat action точна для unsupported automation.
- [ ] Codex classification відповідає local canary.
- [ ] Hermes classification називає verified limit.
- [ ] Немає false hook/API parity claim.
- [ ] Adapter і privacy tests проходять.

## Closeout та Knowledge Delta

Записати кожну capability з provider/version/source/live evidence і fallback. Unverified behavior позначити explicitly.
