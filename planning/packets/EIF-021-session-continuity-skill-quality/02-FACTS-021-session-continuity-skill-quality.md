---
packet: EIF-021-session-continuity-skill-quality
type: facts
status: verified-for-planning
created: 2026-08-09
evidence_cutoff: 2026-08-09
---

# Факти: продовження сесій і протестовані пакети skills

## Позначення доказів

- `OBSERVED`: підтверджено current source, tests, installed CLI або authoritative vendor documentation.
- `INFERRED`: найкращий висновок із observed facts, але ще не behavior proof.
- `ASSUMED`: умова, яку implementation session має перевірити canary.

Firecrawl Cloud використано для повторного extraction authoritative pages. Це planning tool, а не EIF dependency. Після 10 успішних extracts free-tier rate limit повернув `429` для 3 додаткових GitHub pages. Для них використано GitHub API/raw evidence, зібране раніше. Жодна capability claim не базується на failed extract.

## Чинний session contract EIF

1. `OBSERVED` [`templates/session-launch.md`](../../../templates/session-launch.md) уже містить `session_context: .session-context/<session-id>.md`.
2. `OBSERVED` [`playbooks/session-execution.md`](../../../playbooks/session-execution.md) вимагає читати prior session context і продовжувати progress замість restart.
3. `OBSERVED` [`playbooks/execution-packet-execution.md`](../../../playbooks/execution-packet-execution.md) називає checkpoint механізмом resume після interruption.
4. `OBSERVED` [`templates/session-closeout.md`](../../../templates/session-closeout.md) видаляє session-layer checkpoint після validated closeout.
5. `OBSERVED` `.gitignore` і `scripts/tests/test_operating_layer.py` вимагають, щоб `.session-context/` був gitignored і не tracked.
6. `OBSERVED` У repository немає `templates/session-context.md` або відповідної schema. Existing references ведуть до contract, який не має canonical file shape.
7. `OBSERVED` [`templates/session-launch.md`](../../../templates/session-launch.md) називає launch file джерелом правди, а chat history не є джерелом правди.
8. `INFERRED` Новий committed `CURRENT.md` дублював би task scope, launch file, packet facts/decisions і ephemeral checkpoint, порушуючи D-007 про одне canonical source.

## Чинні skills і групування profiles

1. `OBSERVED` [`skills/README.md`](../../../skills/README.md) визначає skills як thin `SKILL.md` pointers до canonical playbooks.
2. `OBSERVED` На дату зрізу є 12 core skill directories. Кожна містить лише `SKILL.md`; жодна не має local `tests/`, `evals/` або supporting script.
3. `OBSERVED` Starter profiles містять 3 additional skills: 2 у `graphic-design`, 1 у `software-development`.
4. `OBSERVED` [`core/schemas/workspace-profile.schema.json`](../../../core/schemas/workspace-profile.schema.json) групує `rule`, `skill`, `playbook`, `template`, `knowledge` artifacts із mode `required`, `default` або `optional`.
5. `OBSERVED` [`src/engineering_intelligence_framework/workspace_materialization.py`](../../../src/engineering_intelligence_framework/workspace_materialization.py) рекурсивно materializes profile artifact directories. Supporting files можуть жити всередині skill directory без нового artifact kind.
6. `OBSERVED` `eif_sync_skills.py` створює agent-visible loaders із pinned runtime manifest; `eifctl doctor` перевіряє loader drift.
7. `OBSERVED` [`playbooks/professional-profile-creation.md`](../../../playbooks/professional-profile-creation.md) забороняє profiles, які лише дублюють core planning/verification, і вже описує profile як найменший reusable artifact set.
8. `OBSERVED` D-20 у [`core/policies/decisions.md`](../../../core/policies/decisions.md) має статус provisional і дозволяє starter profiles, які копіюються в L2 private workspace без automatic activation.
9. `INFERRED` Professional profile уже виконує portable grouping role. Нова universal plugin model у першому packet створила б competing source of truth.

## Чинний розподіл між scripts і моделлю

1. `OBSERVED` Installable EIF package не має OpenAI, Anthropic або іншого LLM SDK dependency.
2. `OBSERVED` Runtime commands уже детерміновано виконують schema validation, link checks, privacy scan, knowledge index/search, render, adapter generation, workspace materialization, runtime verification, benchmark orchestration і release checks.
3. `OBSERVED` Model judgment лишається у task classification, evidence interpretation, decision trade-offs, semantic knowledge curation, architecture review та visual review.
4. `OBSERVED` Модель зараз вручну форматує checkpoint state, перевіряє наявність required skill sections і збирає project/session facts, хоча ці частини можуть бути script-backed.
5. `INFERRED` Найкраща script-first межа: scripts збирають observable state, validate structure і block invalid transitions; model або owner формує semantic fields та decisions.
6. `INFERRED` Повністю script-based task classifier недоцільний: hard conditions можна перевіряти кодом, але risk, ambiguity та decision impact потребують judgment.

## Чинні заборони та enforcement

1. `OBSERVED` EIF уже має fail-closed schema/path checks, marker safety, active-entrypoint ambiguity STOP, required profile artifacts, privacy scan і controlled merge entrypoint.
2. `OBSERVED` Adapter hooks не мають verified parity: Cursor не має equivalent tool-call hook; Codex і Hermes contracts історично block-only або version-bounded; Claude hooks є local machine state, якого CI не бачить.
3. `OBSERVED` Graphic-design playbook вимагає direction approval до final production, але starter profile не має `required` rule і machine-readable `package_allowed` state.
4. `INFERRED` EIF не може чесно заявляти universal shell prohibition без hook parity. Він може працювати fail-closed для EIF-managed commands і чітко маркувати instruction-only limits.

## Докази щодо continuation для adapters

Installed local versions на дату зрізу:

- Claude Code `2.1.169`.
- Codex CLI `0.144.5`.
- Cursor `3.15.6`.
- Hermes Agent `0.20.0`.

| Adapter | Same chat або resume | Докази щодо нового chat | Чесна поточна класифікація |
|---|---|---|---|
| Codex | Поточний chat продовжується звичайно; App Server документує thread lifecycle. | [Codex app commands](https://developers.openai.com/codex/app/commands) документують `codex://threads/new`, optional `prompt` і absolute `path`. Link відкриває новий local chat, але не надсилає prompt автоматично. [App Server](https://developers.openai.com/codex/app-server) надає programmatic `thread/start` і resume lifecycle. | `auto_open_verified` після local canary; `auto_submit_not_supported` у першому packet; App Server integration deferred. |
| Claude Code | [Sessions docs](https://code.claude.com/docs/en/sessions) документують `claude --continue`, `--resume` і resume за ID/name. | Clean CLI invocation створює session; немає current EIF adapter proof, що running model може відкрити і передати керування новому UI chat. | `manual_new_chat`, `resume_verified`; без self-create claim. |
| Cursor | [Cursor CLI docs](https://cursor.com/docs/cli/overview) документують `agent resume`, `agent --continue` і `agent --resume=<chat-id>`. | Користувач може відкрити нову Agent tab або invocation; EIF-accessible self-open API не підтверджено. | `manual_new_chat`, `resume_verified`; без self-create claim. |
| Hermes | [Slash command docs](https://hermes-agent.nousresearch.com/docs/reference/slash-commands) документують `/new`, `/reset`, `/branch` і `/fork`. [Programmatic integration](https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration) містить `session.create`. | Platform API може створити session, але current EIF adapter лише materializes project instructions і не має verified Desktop attachment/control transfer. | `/new` manual verified; programmatic auto-create має статус `canary_required`, а не Available. |

`INFERRED` Створення physical chat є adapter/host capability, а не framework-wide method. `auto` має вибирати дію за capability data у runtime і показувати manual fallback.

## Дослідження зовнішніх skills та evals

Спостереження щодо GitHub tree є point-in-time counts на дату зрізу, а не endorsement якості. Import у цьому packet заборонений.

### Сильні patterns для адаптації

1. [`dotnet/skills`](https://github.com/dotnet/skills)
   - `OBSERVED`: MIT, 104 файли `SKILL.md`, розвинені validator tests і CI на дату зрізу.
   - `OBSERVED`: `skill-validator` запускає baseline без skill і treatment зі skill, записує tokens, tool calls, time, errors і completion, а також розділяє model-free `check` і model-based `evaluate`.
   - Корисний pattern: спочатку static checker, потім A/B eval; baseline можна reuse лише за однакових умов; improvement threshold має бути explicit.

2. [`NVIDIA/skills`](https://github.com/NVIDIA/skills)
   - `OBSERVED`: Apache-2.0 плюс documented content licensing, сотні skills, per-skill `evals/` і `BENCHMARK.md` patterns.
   - Корисний pattern: evidence зберігається поруч зі skill; plugin directory групує skills без перенесення canonical source у prose docs.

3. [`GoogleChrome/modern-web-guidance-src`](https://github.com/GoogleChrome/modern-web-guidance-src)
   - `OBSERVED`: Apache-2.0, testable harness і CI; repository вказує, що evals допомагають прибирати guidance, який моделі вже знають.
   - Корисний pattern: token efficiency оцінюється через вилучення надлишкової guidance, а не за інтуїцією.

4. [`dash0hq/agent-skills`](https://github.com/dash0hq/agent-skills)
   - `OBSERVED`: Apache-2.0; Go harness запускає headless agent на fixtures і використовує deterministic telemetry assertions без LLM judge для pass/fail.
   - Корисний pattern: deterministic outcome assertions мають пріоритет; rubric judging потрібен лише для залишкової семантики.

5. [`aws-samples/sample-agent-skill-eval`](https://github.com/aws-samples/sample-agent-skill-eval)
   - `OBSERVED`: MIT-0, tests, CI і fixtures для safety, quality, trigger reliability та cost efficiency.
   - Корисний pattern: model-free security/structure audit перед будь-яким model run; relevant і irrelevant trigger queries.

6. [OpenAI eval guidance](https://developers.openai.com/blog/eval-skills)
   - `OBSERVED`: рекомендує визначений success, deterministic checks разом із rubric grading, trigger tests, малий початковий prompt set і efficiency evidence.
   - Корисний pattern: для першого bounded pilot не потрібен великий benchmark, але claims про якість потребують repeatable evidence.

### Відхилено для first-package adoption

- `anthropics/skills`: корисні приклади, але tree audit не знайшов repository-level tests/evals і чіткої root license metadata на дату зрізу. Лише research reference.
- `mgechev/skills-best-practices`: guidance згадує evals, але repository tree не містив actual eval fixtures і CI evidence.
- `hamelsmu/evals-skills`: content релевантний eval methodology, але repository tree не містив tests/evals за strict admission gate.
- Broad community catalogs: кількість або популярність не є доказом correctness, safety чи token benefit.

## Ledger перенесених рішень

| Попередній пункт | Розміщення |
|---|---|
| Надійне продовження без native compaction | First package: checkpoint-first continuity. |
| Можливість продовжити в одному chat | First package: explicit `same_chat`. |
| Agent створює новий chat, якщо capability є | First package: capability-based, Codex deep-link pilot; Hermes canary; інші manual. |
| Manual new chat, якщо agent не може створити | First package fallback із збереженим same-chat choice. |
| Canonical current-task state | First package через existing `.session-context`, без `CURRENT.md`. |
| Project memory, checkpoint і compressed context є окремими | First package architecture contract. |
| Resolver активного project | Перший пакет: `eifctl projects resolve`; global `--project` у backlog. |
| Graphic-design approval/package guard | First package через required rule та EIF-managed guard. |
| Changed-only проти full QA | First package contract і tests; advanced dependency engine deferred. |
| Групування skills у plugins | Reframed: professional profile є canonical pack; vendor exporters deferred. |
| Tests/evals усередині skills | First package: static fixtures для current skills і bounded behavioral pilot. |
| External skill research лише з tests/evals | Planning complete; import відсутній. Admission system у backlog. |
| Заміна model work scripts | First package для checkpoints, project resolution і skill checks; broad automation у backlog. |
| Заборони й обмеження | Перший пакет: enforcement taxonomy та протестовані нові guards; universal action engine у backlog. |
| Native compaction hooks і reinjection | Detailed backlog, ніколи не authority. |
| Full `eifctl session` lifecycle database | Спочатку file-based vertical slice; history/list/archive у backlog. |
| Universal plugin marketplace | Detailed backlog після adapter-specific evidence. |
| Toolpack Renderer/Poppler | Детальний backlog. |
| Binary-aware privacy scanner | Detailed backlog після reproduction. |
| Dependency-aware delta QA | Детальний backlog. |
| Token/time/quality benchmark expansion | Bounded pilot спочатку; multi-model program у backlog. |
| Перевірка на комп'ютері дизайнерки | Deferred до нового release, не current focus. |

## Припущення для перевірки під час execution

- `ASSUMED` Codex Desktop на target host обробляє `codex://threads/new` відповідно до current official docs.
- `ASSUMED` Existing workspace materialization переносить `tests/` і `evals/` без loader drift або неприйнятного runtime bloat.
- `ASSUMED` Compact session schema підтримує structured single tasks і packet sessions без примусу light tasks до files.
- `ASSUMED` Є щонайменше один approved local agent/model для максимум 12 sequential eval runs. Без owner budget approval behavioral claim лишається `NOT VERIFIED`, а не PASS.
