---
packet: EIF-021-session-continuity-skill-quality
type: decisions
status: recommended-awaiting-owner-approval
created: 2026-08-09
---

# Рекомендовані рішення

Ці decisions готують execution і не змінюють ratified framework policy до owner approval та Session 001. Session 001 має узгодити їх із [`core/policies/decisions.md`](../../../core/policies/decisions.md), а не тихо редагувати ratified entries.

## P21-01: Logical session не дорівнює physical chat

**Рекомендація:** logical session є bounded methodological unit із goal, scope, exit criteria та closeout. Physical chat є runtime container. Одна logical session може продовжитися в тому самому chat або в кількох послідовних chats через validated checkpoint.

**Чому:** це зберігає чинну session methodology і прибирає залежність від одного context window.

**Відхилено:** визначати кожен новий chat як нову EIF session. Це ламало б exit criteria, checkpoints і packet sequencing.

## P21-02: Не створювати `CURRENT.md`

**Рекомендація:** доповнити existing launch/task artifacts і `.session-context/<session-id>.md`.

**Чому:** launch/task file зберігає approved contract, packet files зберігають durable facts/decisions, `.session-context` зберігає mutable runtime progress.

**Відхилено:** ще один committed current-state file, який drift-ить від canonical packet/session artifacts.

## P21-03: Три continuation modes

**Рекомендація:** `same_chat`, `new_chat`, `auto`.

- `same_chat`: validate checkpoint, виконати resume audit і продовжити тут.
- `new_chat`: automatic create/open, якщо capability має статус `verified`; інакше показати точну manual action.
- `auto`: automatic new chat для verified capability. Якщо capability manual-only, agent коротко пропонує дві дії: продовжити тут або створити новий chat вручну. Без user choice нічого не створюється.

**Чому:** це виконує owner requirement без примусової зміни chat.

**Відхилено:** завжди просити новий chat; завжди лишатися в одному chat; вважати unsupported automation підтриманою.

## P21-04: Checkpoint перед compaction або handoff

**Рекомендація:** будь-який planned chat transition або manual compaction спочатку створює validated checkpoint. Native compressed context може допомогти, але не є authority.

**Відхилено:** post-hoc summary після втрати context або reliance на provider transcript.

## P21-05: Canonical checkpoint shape

**Рекомендація:** checkpoint містить:

- ID/name/root project і source artifact завдання або session;
- ID логічної session, adapter і continuation mode;
- goal, in-scope та no-touch constraints;
- decisions та approval state;
- виконану роботу і changed artifacts;
- verification commands/results;
- blockers, невдалі підходи й unresolved risks;
- exact next action;
- observed fingerprint для Git branch/status;
- prior physical chat references лише як optional metadata.

Semantic fields заповнює agent/owner; observable fields збирає script.

## P21-06: File-based `eifctl session` vertical slice

**Рекомендація:** перша версія має `checkpoint`, `validate`, `handoff`, `resume-audit`. Вона не створює session database і не зберігає transcript.

**Чому:** це найменша зміна, сумісна з existing `.session-context` lifecycle.

## P21-07: Project resolution працює fail-closed

**Рекомендація:** `eifctl projects resolve <id-or-name>` повертає один registry v2 identity і local path лише коли `.eif/config.yaml` та framework lock узгоджені. Unknown, duplicate, missing path або wrong active project завершуються nonzero до write/handoff.

## P21-08: Capability records замість adapter tiers

**Рекомендація:** parity matrix отримує окремі fields для `same_chat`, `resume`, `create_new_chat`, `open_new_chat`, `auto_submit`, `pre_compact`, `post_compact` і evidence status.

**Чому:** чотири adapters підтримуються на однаковому product level, але їхні механіки різні.

## P21-09: Codex deep link є першим automatic-open pilot

**Рекомендація:** після local canary `eifctl session handoff --open` може відкрити URL із encoded prompt pointer і absolute project path. Prompt не надсилається автоматично, користувач підтверджує send.

**Відхилено:** App Server integration у першому packet. Вона додає authentication, process lifecycle і host coupling.

## P21-10: Hermes programmatic create лишається canary-gated

**Рекомендація:** перевірити `session.create`, але не активувати automatic Desktop handoff, доки canary не доведе: new session visible, correct profile/project attached, no parallel worker, current session safely relinquishes control.

**Fallback:** `/new <name>` або same chat.

## P21-11: Professional profile є canonical протестованим пакетом skills

**Рекомендація:** не перейменовувати public concept і не створювати universal plugin manifest. Skills, rules, playbooks, templates, scripts, tests та evals групуються existing profile manifest.

**Чому:** profile уже pinned, materialized, override-aware і tested across projects.

**Надалі:** adapter exporters можуть генерувати Codex/Claude plugin packages із canonical profile source.

## P21-12: Tests поруч зі skills, а workflow source лишається playbook

**Рекомендація:** кожен current skill отримує local contract fixture. Fixture перевіряє trigger examples, non-trigger examples, canonical references, required commands/evidence, stop conditions і forbidden behavior. Він не копіює workflow prose.

**Обов'язково для new/changed skills:** static checks у CI. Behavioral eval потрібен для material semantic change, але не для typo-only change.

## P21-13: Static check перед model eval

**Рекомендація:** `eifctl skills check` виконує model-free validation. Behavioral A/B запускається окремо, послідовно і тільки з explicit budget.

**Чому:** більшість structural regressions не потребують tokens. Це відповідає patterns OpenAI, dotnet, Dash0 та AWS samples.

## P21-14: Script-first boundary

**Рекомендація:** script виконує лише deterministic work:

- project/session state discovery;
- schema/reference/path validation;
- checkpoint rendering і integrity;
- adapter strategy selection із capability data;
- skill fixture validation;
- deterministic grader assertions;
- approval state check для EIF-managed action.

Model/owner лишається responsible за semantic classification, trade-offs, visual quality і approval.

## P21-15: Enforcement level є обов'язковим для prohibition claims

**Рекомендація:** використовувати чотири labels:

- `machine`: core command/schema реально працює fail-closed;
- `adapter`: verified adapter/hook блокує action із named version/evidence;
- `owner_gate`: action потребує explicit human approval;
- `instruction_only`: model contract без технічного блокування.

Docs не можуть називати `instruction_only` guard enforcement.

## P21-16: Graphic-design package guard

**Рекомендація:** starter profile отримує `required` rule. `package_allowed` має default `false`; explicit approval записує decision owner, scope і timestamp/evidence reference. EIF-managed package/delivery validation повертає nonzero до approval.

**Обмеження:** довільну зовнішню ZIP command можна блокувати лише через verified adapter guard. Без нього це `instruction_only`, і docs мають це казати.

## P21-17: Admission зовнішніх skills

**Рекомендація:** у first packet немає imports. Future candidate допускається лише якщо:

1. source revision pinned;
2. license сумісна;
3. scripts/references reviewed;
4. поверхні secrets, network, install і permissions audited;
5. upstream має real tests/evals;
6. local EIF static check проходить;
7. local bounded comparative eval не показує regression або unjustified token cost;
8. owner явно погодив activation.

Popularity, stars або vendor name не замінюють ці gates.

## P21-18: Обмежений перший eval

**Рекомендація:** 2 representative skills, до 3 scenarios кожен, baseline/treatment, максимум 12 sequential model runs. Deterministic graders мають пріоритет; rubric judge використовується лише для semantic residue. Потрібно записувати model/version, settings, tokens, time, failures і artifacts.

**Budget gate:** exact provider/cost ceiling затверджує owner перед Session 005. Без approval code/fixtures можуть бути complete, behavioral result має статус `DEFERRED`, а packet не робить improvement claim.

## P21-19: Без subagents і parallel evals

**Рекомендація:** packet виконує один agent послідовно. Eval invocations є isolated test runs, а не delegated implementation, і також виконуються послідовно. Жодні delegation/team tools не використовуються.

## P21-20: Release і designer acceptance

**Рекомендація:** packet закінчується locally verified candidate. Перевірка на комп'ютері дизайнерки виконується лише після нового release окремим owner-approved run. Ні release, ні цей run не входять у packet.
