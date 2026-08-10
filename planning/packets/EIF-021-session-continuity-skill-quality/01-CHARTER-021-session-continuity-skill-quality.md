---
packet: EIF-021-session-continuity-skill-quality
type: charter
status: prepared-awaiting-owner-approval
created: 2026-08-09
---

# Статут: продовження сесій і протестовані пакети skills

## Формулювання проблеми

EIF уже вміє виконувати prepared sessions із launch files, зберігати ephemeral checkpoints у `.session-context/`, відновлювати перервану роботу та завершувати session через closeout. Але контракт неповний:

- logical session і physical chat не розділені явно;
- `session-launch.md` посилається на `.session-context/<session-id>.md`, але public template або schema такого checkpoint відсутні;
- adapter parity matrix не описує створення нового chat, manual fallback, same-chat continuation або resume capability;
- native compaction може втрачати деталі і не повинна бути єдиним continuation state;
- 12 core skills і 3 starter-profile skills не мають власних test/eval fixtures;
- professional profiles уже групують skills, playbooks, templates і rules, але quality gate для такого пакета відсутній;
- частина constraints існує лише як текстова інструкція без чесного позначення, що є machine-enforced, adapter-enforced, owner-gated або advisory;
- модель виконує форматування і structural checks, які дешевше й надійніше виконувати scripts.

## Мета

Додати органічний continuity та skill-quality vertical slice (вертикальний зріз), який повторно використовує чинні session files, profiles, runtime bundling, adapter registry, tests і benchmark primitives. Не створювати нову intelligence layer, паралельний `CURRENT.md`, універсальну plugin abstraction або удавану adapter parity.

## У межах пакета

### Продовження роботи

- Визначити `logical_session` окремо від `physical_chat`.
- Додати canonical `templates/session-context.md` та machine-readable schema.
- Зберігати checkpoint до logical session closeout незалежно від кількості physical chats.
- Додати `continuation_mode: same_chat | new_chat | auto`.
- Для `auto` створювати новий chat лише через verified adapter capability; інакше пропонувати користувачу manual new chat або продовження в поточному chat.
- Залишити native compaction optional optimization після checkpoint, а не source of truth.
- Додати resume audit, який перевіряє project identity, objective, scope, no-touch zone, approvals, decisions, Git state, verification і exact next action.

### Детерміновані інструменти

- Додати `eifctl session checkpoint`, `validate`, `handoff` і `resume-audit` як file-based commands без LLM calls.
- Додати `eifctl projects resolve <id-or-name>` поверх наявного registry v2 і local-state contract.
- Автоматично збирати project identity, path, Git branch/status і changed files там, де це можна перевірити.
- Не дозволяти `handoff`, якщо checkpoint structurally invalid або project identity суперечить active project.

### Стратегії адаптерів

- Розширити `adapters/parity-matrix.json` continuity capabilities.
- Codex: виконати canary і підтримати documented `codex://threads/new?prompt=...&path=...`; link відкриває chat, але не надсилає prompt автоматично.
- Hermes: зафіксувати `/new`, `/branch` і programmatic `session.create`; automatic Desktop handoff активувати лише після окремого canary, який доведе послідовне передавання керування без parallel agent.
- Claude Code і Cursor: підтримати documented same-session resume та manual new-session actions; не заявляти self-creation без verified host surface.
- Для кожного adapter мати точну supported action і fallback.

### Протестовані пакети skills

- Зберегти professional profile як canonical EIF grouping unit.
- Дозволити skill directory містити `scripts/`, `references/`, `tests/` та `evals/` без дублювання canonical playbook.
- Додати детермінований `eifctl skills check` для structure, references, scripts, fixtures, license/provenance metadata і forbidden behavior assertions.
- Додати мінімальні positive/negative trigger fixtures для всіх current core і starter-profile skills.
- Провести обмежений behavioral A/B pilot лише на двох representative skills, послідовно, з максимум 12 model runs та explicit budget approval.
- Не запускати model eval у default CI.

### Обмеження і погодження

- Визначити enforcement levels: `machine`, `adapter`, `owner_gate`, `instruction_only`.
- Нові claims завжди називають свій реальний enforcement level.
- Додати required graphic-design delivery rule: package/final delivery заборонені до explicit approval.
- Додати machine check для EIF-managed `package`/`delivery` guard, не стверджуючи, що EIF може заблокувати довільний зовнішній `zip` без adapter hook.
- Changed-only QA застосовується до bounded local changes; global-impact change вимагає full QA.

### Дослідження і admission policy

- Зафіксувати external sources із реальними tests/evals та корисні patterns.
- Не імпортувати жоден external skill у цьому packet.
- Майбутній import дозволяти лише з pinned revision, compatible license, code review, security/privacy scan, tests/evals і local comparative evidence.

## Поза межами пакета

- Нова fourth layer або зміна authority model.
- Новий `CURRENT.md` чи committed transcript summary.
- Обов'язкова зміна chat після кожної session.
- Обов'язковий native compaction або pre/post compact hooks.
- Повна автономна інтеграція Codex App Server, Hermes Desktop API, Claude UI або Cursor UI без окремих canaries.
- Universal plugin marketplace чи один manifest для несумісних vendor plugin systems.
- Автоматичне встановлення community skills.
- Масове переписування всіх playbooks або skills.
- Model-based routing classifier для light, structured і packet tasks.
- Повна action-policy engine для будь-якої shell command.
- Toolchain Renderer/Poppler, redesign робочого простору artifacts або dependency-aware engine для visual QA.
- Перевірка install/deploy на комп'ютері дизайнерки до нового release.
- Push, PR, merge, tag, release, hosted CI або external publication.
- Subagents, delegation, teams або parallel execution.
- Firecrawl чи інша local Hermes configuration як EIF feature.

## Definition of Done

- [ ] `DD-01` Logical session і physical chat мають одне canonical definition, сумісне з three-layer model.
- [ ] `DD-02` `.session-context` має template, schema, lifecycle і не комітиться.
- [ ] `DD-03` Same-chat continuation лишається first-class option.
- [ ] `DD-04` `auto` використовує automatic new chat тільки для verified capability; manual fallback не приховується.
- [ ] `DD-05` Resume audit виявляє втрату project, goal, scope, approval, changed files, test state або next action.
- [ ] `DD-06` `eifctl projects resolve` працює fail-closed для unknown, ambiguous або incomplete EIF project.
- [ ] `DD-07` Усі чотири adapters мають tested і truthful continuity records.
- [ ] `DD-08` Existing professional profiles лишаються canonical grouping unit; дублюючої plugin system немає.
- [ ] `DD-09` Усі current core і starter skills мають valid local contract fixtures.
- [ ] `DD-10` Deterministic skill checks виконуються без model/token cost.
- [ ] `DD-11` Bounded A/B pilot має recorded quality, trigger, token, time та failure evidence або чесний `NOT VERIFIED` через owner-gated budget.
- [ ] `DD-12` Кожна нова prohibition має declared enforcement level і test.
- [ ] `DD-13` Graphic-design package/final delivery guard працює fail-closed у EIF-managed path.
- [ ] `DD-14` External skills не встановлені; admission gate і researched candidates задокументовані.
- [ ] `DD-15` Package/runtime mirrors, links, privacy, locale, tests і installed-wheel smoke проходять локально.
- [ ] `DD-16` Перевірка на комп'ютері дизайнерки, external publication та всі deferred рішення лишаються в detailed backlog.

## Межа погодження

Цей статут рекомендує scope, але не ратифікує framework decisions. Owner approval packet запускає Session 001. Будь-яке розширення за межі `У межах пакета` вимагає окремого decision update до code changes.
