---
packet: EIF-021-session-continuity-skill-quality
type: autonomous-entrypoint
status: blocked-awaiting-owner-approval
---

# Почати тут

## Approval gate

Не виконувати цей packet, доки owner явно не погодить:

1. recommended decisions і scope із six sessions;
2. чи може Session 005 використати до 12 sequential model eval runs, а також exact cost ceiling.

Planning approval не є implementation approval.

## Canonical execution prompt

```text
Виконай погоджений EIF packet за адресою:
planning/packets/EIF-021-session-continuity-skill-quality/

Entry point:
06-START-HERE-session-continuity-skill-quality.md

Мета:
Додати checkpoint-first session continuity і quality gates для tested skill
packs без зміни three-layer model EIF, примусового створення нових chats,
parallel plugin system або claims про unsupported adapter enforcement.

Порядок:
1. Прочитай files 00-05 і detailed backlog.
2. Повторно перевір кожен OBSERVED fact за current source та official docs.
3. Виконай SESSION-001 - SESSION-006 послідовно одним agent.
4. Перед діями прочитай launch file кожної session і підтримуй її
   .session-context checkpoint до logical closeout.
5. Не використовуй old chat history як source of truth.
6. Зупинися до scope expansion, owner-only action або unapproved model cost.

Продовження:
- same chat завжди дозволений, якщо context і user choice це підтримують;
- new chat можна відкрити автоматично лише після verified adapter capability;
- інакше покажи exact manual action та option продовжити тут;
- створи checkpoint перед chat transition або compaction.

Global limits:
- без subagents, delegation, teams або parallel evals;
- без push, PR, merge, tag, release, hosted CI або remote publication;
- без designer-machine validation;
- без third-party skill installation;
- без automatic user-config або hook mutation;
- без model eval понад окремо погоджений budget;
- Firecrawl є research tooling, а не EIF dependency.

Обов'язкові tools:
- Graphify, Context7 і RTK є mandatory default tools для цієї роботи;
- перед broad repository navigation спочатку query raw knowledge graph через
  Graphify, а потім verify findings за current source і tests;
- для vendor/package contracts і current technical documentation спочатку
  використовуй Context7, а за відсутності coverage переходь до official source;
- кожну shell command запускай через RTK; raw command дозволена лише як
  documented argv-safe exception через verified `rtk proxy ... # rtk-raw-ok`;
- якщо Graphify, Context7 або RTK unavailable чи stale, запиши issue та
  disposition, застосуй bounded fallback і не приховуй зниження evidence quality.

Source authority:
current owner instruction і ratified decisions > fresh source/tool state >
validated knowledge > approved packet decisions > inference/chat memory.

Closeout:
Заповни 07-CLOSEOUT-021-session-continuity-skill-quality.md точними evidence,
errors і deferred items. Заверши на locally verified candidate.
```

## Умови зупинки

Зупинитися і запросити owner decision, якщо:

- recommended decision суперечить ratified policy і narrow supersession не погоджено;
- auto-new-chat потребує undocumented API, credential або user-config mutation;
- для scope потрібно імпортувати external skill content;
- model eval потребує cost вище approved ceiling;
- prohibition можна назвати machine-enforced лише через false capability claim;
- target files мають incompatible concurrent edits;
- action може publish, release, expose private data або спричинити hard-to-reverse loss.
