---
packet: EIF-021-session-continuity-skill-quality
type: roadmap
status: prepared-awaiting-owner-approval
created: 2026-08-09
---

# Дорожня карта

Execution відбувається послідовно одним agent. Кожна session завершується або записує explicit blocked/deferred state до початку наступної. Subagents і parallel eval runs заборонені.

## Session 001: контракт continuation та enforcement

**Залежності:** немає.

**Мета:** визначити logical session, physical chat, checkpoint lifecycle, continuation modes і enforcement levels без зміни three-layer model.

**Ймовірні джерела змін:**

- `core/policies/decisions.md`
- `docs/architecture/HOW-EIF-WORKS.md`
- `docs/reference/terminology.md`
- `playbooks/session-preparation.md`
- `playbooks/session-execution.md`
- `playbooks/session-closeout.md`
- `templates/session-launch.md`
- `templates/task-scope.md`
- `templates/session-closeout.md`
- відповідні locale/resources mirrors і operating-layer tests

**Кроки:**

1. Повторно перевірити P21 decisions проти current ratified/provisional register.
2. Додати одне explicit decision або supersession лише там, де це потрібно.
3. Визначити logical session окремо від physical chat та `same_chat | new_chat | auto`.
4. Визначити checkpoint-first compaction/handoff і enforcement labels.
5. Зберегти light tasks без обов'язкових files, якщо роботу не перервано і checkpoint явно не потрібен.
6. Додати structural tests проти fourth layer, mandatory new chat і compaction authority claims.

**Перевірка:** link check, privacy scan, locale/terminology tests, operating-layer tests.

**Вихід:** `DD-01`, `DD-03`, architecture portion of `DD-04` та `DD-12` мають mapping на passing tests.

## Session 002: інструменти session state і project resolver

**Залежності:** SESSION-001.

**Мета:** реалізувати найменший deterministic file-based continuation surface.

**Ймовірні джерела змін:**

- новий `templates/session-context.md`
- нова session-context schema у `core/schemas/`
- `src/engineering_intelligence_framework/commands/session.py`
- `src/engineering_intelligence_framework/commands/projects.py`
- parser/dispatch CLI і resources для package
- `scripts/eif_render.py`, лише якщо existing render path можна розширити без duplication
- focused unit, journey та installed-wheel tests

**Кроки:**

1. Визначити schema fields із P21-05 зі strict required/optional boundaries.
2. Додати locale-aware template без копіювання task/launch content.
3. Реалізувати `checkpoint`, який збирає observable project/Git fields і приймає semantic fields explicitly.
4. Реалізувати `validate` та `resume-audit` із nonzero result для mismatch.
5. Реалізувати `handoff` strategy output без adapter automation.
6. Реалізувати `projects resolve` через registry v2 і local-state path.
7. Додати negative fixtures для wrong project, missing approvals, missing next action, stale changed files та invalid source artifact.

**Перевірка:** focused tests, journey, runtime/package smoke, schema validation.

**Вихід:** `DD-02`, `DD-05`, `DD-06` мають PASS.

## Session 003: стратегії continuation для adapters

**Залежності:** SESSION-002.

**Мета:** обирати handoff за real capability для всіх чотирьох adapters.

**Ймовірні джерела змін:**

- `adapters/parity-matrix.json`
- `adapters/README.md`
- чотири adapter READMEs
- `scripts/eif_adapters.py` і package mirror
- реалізація session handoff та adapter tests

**Кроки:**

1. Додати continuity capability fields і evidence metadata.
2. Додати explicit same-chat і manual fallback для кожного adapter.
3. Виконати local Codex deep-link canary без автоматичного надсилання task.
4. Якщо canary проходить, реалізувати opt-in `--open`; інакше класифікувати capability як manual і записати evidence.
5. Перевірити Hermes `session.create` у disposable context. Automatic Desktop transfer дозволити лише якщо всі P21-10 gates проходять; інакше залишити `/new` fallback.
6. Зберегти Claude Code і Cursor у manual mode, якщо fresh evidence не доведе self-open.
7. Переконатися, що generated instructions компактні та не створюють враження, ніби hooks встановлено.

**Перевірка:** adapter tests, parity schema/checks, synthetic handoff URL escaping tests, відсутність user-config mutation.

**Вихід:** `DD-04`, `DD-07` мають PASS із truthful per-capability statuses.

## Session 004: контракт протестованого пакета skills

**Залежності:** SESSION-001.

**Мета:** додати model-free quality gates навколо existing skills і professional profiles без parallel plugin system.

**Ймовірні джерела змін:**

- `skills/README.md`
- усі 12 core skill directories
- 3 skill directories зі starter profiles
- workspace profile schema/materialization, лише якщо це необхідно
- нова skill contract/eval fixture schema
- новий `eifctl skills check`
- profile і skill tests

**Кроки:**

1. Визначити компактну local fixture shape: trigger, non-trigger, references, evidence, commands, stop conditions, forbidden behavior, deterministic assertions.
2. Додати fixtures поруч із кожним current skill.
3. Реалізувати model-free checker для frontmatter, path containment, canonical reference existence, executable/script declarations і fixture validity.
4. Перевірити, що profile materialization переносить supporting files, а loader не додає test content у normal context.
5. Додати admission metadata rules без import external content.
6. Оновлювати capability claims лише після actual passing tests.

**Перевірка:** new checker tests, sync-skill tests, workspace profile journey, package smoke.

**Вихід:** `DD-08`, `DD-09`, `DD-10`, `DD-14` мають PASS.

## Session 005: обмежений behavioral eval і script-first pilot

**Залежності:** SESSION-003, SESSION-004.

**Мета:** отримати bounded evidence, що selected skills trigger correctly, та визначити лише high-value model work для заміни scripts.

**Owner gate перед model calls:** затвердити provider/model, максимум 12 sequential runs і exact cost ceiling.

**Кроки:**

1. Обрати два representative skills: `run-execution-packet` і `knowledge-search`, якщо current failures не обґрунтовують кращу пару.
2. Визначити до трьох scenarios для кожного, включно з positive і negative triggers.
3. По можливості розширити `eif_benchmark.py`, а не створювати unrelated harness.
4. Запустити baseline і treatment послідовно з deterministic graders first.
5. Записати tokens, time, tool calls, outcome, trigger behavior і failures.
6. Використовувати rubric judge лише для semantic checks, які deterministic assertions не можуть оцінити.
7. Створити model-vs-script audit table для всіх current skills/playbooks.
8. Реалізувати лише replacements, які low-effort, deterministic і прямо підтримують цей packet. Решту перенести у B-11.

**Перевірка:** fixture schema, dry-run без credentials, integrity-bound results, exact command і provider evidence.

**Вихід:** `DD-11` має PASS або explicit `DEFERRED`, якщо owner не погодив budget. Claims про improvement за deferred evidence заборонені.

## Session 006: approval guard та підсумок інтеграції

**Залежності:** SESSION-002, SESSION-003, SESSION-004, SESSION-005.

**Мета:** інтегрувати одну реальну required prohibition, синхронізувати package resources і перевірити complete local candidate.

**Ймовірні джерела змін:**

- `professional-profiles/graphic-design/profile.yaml`
- нове required rule у graphic-design profile
- fixtures для graphic-design skills і delivery template
- session guard command/tests
- README capability matrix, claims ledger і changelog лише після появи actual behavior
- package source mirrors

**Кроки:**

1. Додати `package_allowed: false` default та explicit approval evidence shape.
2. Додати EIF-managed package/delivery guard із negative tests.
3. Закодувати changed-only проти global-impact QA routing без dependency automation claim.
4. Синхронізувати package sources, як вимагає `AGENTS.md`.
5. Запустити focused і full local test suites, links, privacy, frontmatter, package smoke та release build check.
6. Перевірити docs на чесність enforcement-level claims і current capability status.
7. Заповнити packet closeout; release і designer-machine acceptance залишити deferred.

**Перевірка:**

```text
rtk python scripts/sync_package_sources.py
rtk python scripts/tests/run_all.py
rtk python scripts/eif_check_links.py
rtk python scripts/eif_privacy_scan.py
rtk python scripts/eif_validate_frontmatter.py
rtk python scripts/eif_release.py
```

Якщо current source змінив команди, використовувати actual repository commands і записати substitutions та причини.

**Вихід:** `DD-12`, `DD-13`, `DD-15`, `DD-16` мають PASS; `07-CLOSEOUT` заповнено; external action відсутня.

## Трасування Definition of Done

| DoD | Sessions |
|---|---|
| DD-01, DD-03 | 001 |
| DD-02, DD-05, DD-06 | 002 |
| DD-04, DD-07 | 001, 003 |
| DD-08, DD-09, DD-10, DD-14 | 004 |
| DD-11 | 005 |
| DD-12 | 001, 004, 006 |
| DD-13 | 006 |
| DD-15, DD-16 | 006 |
