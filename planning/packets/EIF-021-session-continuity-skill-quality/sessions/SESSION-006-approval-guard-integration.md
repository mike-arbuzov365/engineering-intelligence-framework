---
id: SESSION-006
type: session-launch
status: prepared-awaiting-owner-approval
source_artifact: ../04-ROADMAP-021-session-continuity-skill-quality.md
session_context: .session-context/eif-021-session-006.md
depends_on: [SESSION-002, SESSION-003, SESSION-004, SESSION-005]
---

# Session 006: approval guard та local closeout інтеграції

## Мета

Застосувати одну real required prohibition до graphic-design delivery, синхронізувати package resources і перевірити complete packet locally.

## Обов'язковий порядок читання

1. Packet files і всі prior session closeouts/checkpoints.
2. Profile, playbook, skills і templates для graphic design.
3. Поведінка required/default/override для workspace.
4. Claims ledger, capability matrix у README, package sync та release tests.

## Experience Retrieval Preflight

Знайти evidence щодо approval, packaging, delivery, changed-only QA, profile override, package-source drift і release smoke.

## У межах session

- Required rule для graphic-design delivery.
- `package_allowed: false` default і approval evidence.
- Guard для EIF-managed package/delivery із negative tests.
- Honest changed-only проти full-QA contract.
- Sync package resources, update docs/claims і повна local verification.
- Packet closeout.

## Поза межами та no-touch zone

- Без claim про arbitrary shell-hook prohibition.
- Без renderer/Poppler або preview workspace.
- Без designer-machine run.
- Без external repository, push, PR, merge, tag або release.
- Без paid eval понад Session 005 approval.

## Кроки

1. Додати required profile rule і approval state fields через existing pack contract.
2. Реалізувати fail-closed guard для EIF-managed package/delivery action.
3. Додати approved, missing, expired і wrong-scope fixtures.
4. Додати changed-only/global-impact routing wording і tests без dependency-engine claim.
5. Синхронізувати package resources, required by `AGENTS.md`.
6. Запустити focused tests, full suite, links, privacy, schema/frontmatter, wheel smoke і local release build.
7. Перевірити current capability wording і заповнити `07-CLOSEOUT`.

## Перевірка

```text
rtk python scripts/sync_package_sources.py
rtk python scripts/tests/run_all.py
rtk python scripts/eif_check_links.py
rtk python scripts/eif_privacy_scan.py
rtk python scripts/eif_validate_frontmatter.py
rtk python scripts/eif_release.py
rtk git diff --check
rtk git status --short
```

## Контракт bounded loop

- `success_evidence`: negative approval fixtures fail; усі local package/runtime gates pass; closeout називає кожний defer.
- `evaluator`: commands вище плюс installed-wheel journey.
- `max_iterations`: 3.
- `remote_run_budget`: 0.
- Stop за privacy finding, release-only requirement, unavailable required local evaluator або false enforcement claim.

## Критерії виходу

- [ ] Required rule materializes і не може бути silently overridden.
- [ ] EIF-managed package/delivery blocks без valid approval.
- [ ] External shell limitation описано explicitly.
- [ ] Package mirrors current.
- [ ] Повна local suite і release build check мають PASS.
- [ ] Designer-machine/release лишаються deferred.
- [ ] `07-CLOSEOUT` містить exact results, errors і next action.

## Closeout та Knowledge Delta

Заповнити `../07-CLOSEOUT-021-session-continuity-skill-quality.md`. Кожний residual item направити до exact backlog ID. Нічого не publish.
