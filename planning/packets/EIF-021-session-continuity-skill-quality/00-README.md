---
packet: EIF-021-session-continuity-skill-quality
type: packet_index
status: prepared-awaiting-owner-approval
created: 2026-08-09
execution_approval: required
---

# EIF: продовження сесій і протестовані пакети skills v1

Цей execution packet (пакет виконання) планує найменший цілісний набір змін, який:

1. робить продовження роботи між physical chats (фізичними чатами) надійним без залежності від native compaction (вбудованого стискання контексту);
2. зберігає можливість працювати в одному chat;
3. використовує автоматичне створення нового chat лише там, де capability (можливість) підтверджена документацією і canary (контрольною перевіркою);
4. доповнює наявні professional profiles як протестовані пакети skills, а не створює паралельну plugin system;
5. переносить детерміновані перевірки з моделі у scripts і додає fail-closed constraints (обмеження з блокуванням за невизначеності) для нового workflow.

Packet не змінює тришарову модель EIF. Logical session (логічна сесія) лишається одиницею методології, а physical chat є лише runtime container (середовищем виконання).

## Порядок читання

1. `01-CHARTER-021-session-continuity-skill-quality.md`
2. `02-FACTS-021-session-continuity-skill-quality.md`
3. `03-DECISIONS-021-session-continuity-skill-quality.md`
4. `BACKLOG-021-session-continuity-skill-quality.md`
5. `04-ROADMAP-021-session-continuity-skill-quality.md`
6. `05-SELF-REVIEW-021-session-continuity-skill-quality.md`
7. `06-START-HERE-session-continuity-skill-quality.md`

## Карта сесій

| Сесія | Результат |
|---|---|
| 001 | Сумісний із чинною методологією continuity contract і класифікація enforcement |
| 002 | Canonical `.session-context`, schema, `eifctl session` і точний project resolver |
| 003 | Capability-based continuation для Claude Code, Codex, Cursor і Hermes |
| 004 | Контракт протестованого пакета skills поверх наявних skills і professional profiles |
| 005 | Обмежений behavioral eval і реалізація найцінніших script-first replacements |
| 006 | Graphic-design approval guard, локальна інтеграція, повна verification і closeout |

## Межа виконання

Поточна вказівка власника дозволяє planning. Implementation не починається без окремого owner approval цього packet.

Packet не включає push, PR, merge, release, hosted CI, перевірку на комп'ютері дизайнерки, автоматичний import сторонніх skills, платні model runs без окремого budget approval або зміну active Hermes configuration. Firecrawl використано лише як локальний research provider під час planning. Він не є частиною EIF scope.
