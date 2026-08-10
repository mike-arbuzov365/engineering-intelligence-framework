---
id: SESSION-005
type: session-launch
status: prepared-awaiting-owner-budget-approval
source_artifact: ../04-ROADMAP-021-session-continuity-skill-quality.md
session_context: .session-context/eif-021-session-005.md
depends_on: [SESSION-003, SESSION-004]
---

# Session 005: обмежений skill eval і script-first pilot

## Мета

Виконати малий comparative skill eval і реалізувати лише deterministic replacements для model work із clear value.

## Owner gate

До provider call записати:

- approved provider/model/version;
- максимум 12 sequential runs;
- exact currency або credit ceiling;
- чи дозволений rubric judging;
- stop action, якщо budget telemetry unavailable.

Без approval виконати лише dry-run і deterministic tests, позначити behavioral evidence як `DEFERRED` і не робити skill-improvement claim.

## Обов'язковий порядок читання

1. Packet і results Sessions 003-004.
2. Current `eif_benchmark.py` і docs/tests для benchmark integrity.
3. Fixtures для `run-execution-packet` і `knowledge-search`.
4. OpenAI, dotnet, Dash0 та AWS eval patterns із Facts.

## Experience Retrieval Preflight

Знайти benchmark failures, token claims, evaluator leakage, baseline reuse і model-run cost incidents.

## У межах session

- Два representative skills, до three scenarios для кожного.
- Baseline проти treatment, максимум 12 sequential runs.
- Deterministic graders first.
- Повна model-versus-script audit table.
- Лише low-effort replacements, які прямо підтримують continuity/skill validation.

## Поза межами та no-touch zone

- Без parallel runs або delegated agents.
- Без multi-model matrix.
- Без hosted CI eval.
- Без broad skill rewrite.
- Без unapproved cost.
- Без quality/token claim за межами measured fixtures.

## Кроки

1. Зафіксувати model/settings/prompts/evaluator і repository state.
2. Перевірити positive та negative trigger scenarios.
3. За можливості розширити current benchmark harness, а не створювати another framework.
4. Запустити або dry-run baseline/treatment послідовно.
5. Записати outcome, trigger, commands, tokens, time, failures і artifacts.
6. Використати deterministic grader там, де можливо; isolate rubric-only checks.
7. Створити audit table: keep with model, replace with script, owner gate або defer.
8. Реалізувати і test лише selected script-first changes.

## Перевірка

```text
rtk python scripts/tests/test_benchmark.py
rtk python scripts/eif_benchmark.py --help
rtk python scripts/eif_privacy_scan.py
rtk git diff --check
```

Запустити exact eval commands з approved manifest і зберегти redacted, integrity-bound results.

## Контракт bounded loop

- `success_evidence`: valid A/B records для approved runs або complete dry-run плюс explicit budget defer; evaluator leakage відсутній.
- `evaluator`: спочатку deterministic assertions, потім approved rubric.
- `max_iterations`: 2 на scenario.
- `remote_run_budget`: максимум 12 model runs після owner approval; hosted CI budget 0.
- Stop за budget telemetry absence, credential exposure, provider drift або integrity mismatch.

## Критерії виходу

- [ ] Owner budget decision recorded.
- [ ] Fixtures і dry-run pass.
- [ ] Approved runs послідовні та в межах budget, або result чесно deferred.
- [ ] Tokens/time/quality claims відповідають evidence.
- [ ] Model-versus-script audit охоплює всі current skills.
- [ ] Implemented replacements мають tests і не показують lower quality.

## Closeout та Knowledge Delta

Записати exact measured limits, useful/rejected skill changes, selected script replacements і remaining items у B-08/B-11/B-17.
