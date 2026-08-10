---
packet: EIF-021-session-continuity-skill-quality
type: detailed_backlog
status: prepared
created: 2026-08-09
---

# Детальний backlog після EIF-021

Цей backlog є частиною carry-over contract. Кожен пункт має solution shape, причину defer, prerequisites та acceptance evidence. Короткий title без цих полів не вважається достатнім перенесенням.

## B-01: Повністю автоматичне створення chat через host APIs

**Пріоритет:** P1 після evidence з first package.

**Запропоноване рішення:**

- Додати adapter-specific host connectors замість одного fake universal API.
- Codex connector використовує App Server `thread/start`, `thread/resume` і authenticated local transport.
- Hermes connector використовує programmatic `session.create` та attach/open surface Desktop/TUI.
- Claude Code і Cursor connectors з'являються лише після documented host API або safe deep link.
- Handoff є sequential ownership transfer: current agent створює checkpoint, new session отримує pointer, current execution завершується. Parallel worker не створюється.
- Connector має health check, version range, explicit permissions і rollback.

**Чому deferred:** deep App Server/Desktop coupling роздуває first vertical slice та створює authentication/process risks. Codex deep-link auto-open дає дешевший pilot.

**Передумови:** checkpoint schema з EIF-021; adapter capability records; canaries; threat model; no-subagent compliance.

**Критерій приймання:** new chat visible у target UI; correct project/profile; prompt посилається на checkpoint; немає auto-send без documented permission; old execution stopped; failed create повертає same-chat/manual fallback без state loss.

## B-02: Інтеграція native compaction

**Пріоритет:** P1/P2, optional optimization.

**Запропоноване рішення:**

- Capability-specific `pre_compact` записує і validates checkpoint.
- `post_compact` запускає resume audit і reinjects лише missing canonical state.
- Compaction summary ніколи не overwrites launch, task, facts, decisions або checkpoint.
- Adapters без hooks використовують explicit checkpoint command перед manual compact.
- Записувати provider/version і чи enforcement має рівень `machine`, `adapter` або `instruction_only`.

**Чому deferred:** current hook parity не verified; compaction не потрібна для core continuation через new chat.

**Передумови:** checkpoint/resume audit з EIF-021; per-adapter canaries; regression fixtures для lossy summaries.

**Критерій приймання:** deliberate loss fixtures detected; state fields survive або restore; disabling hooks не ламає core continuation.

## B-03: Розширений lifecycle `eifctl session`

**Пріоритет:** P2.

**Запропоноване рішення:** розширити file-based commands через `list`, `show`, `resume`, `archive`, `close`, stale-checkpoint cleanup і optional local SQLite index. Files лишаються canonical, а DB є rebuildable index.

**Чому deferred:** first package потребує одного current checkpoint, а не session-management product.

**Передумови:** stable schema/lifecycle після real packet use; migration contract; privacy policy для local metadata.

**Критерій приймання:** index можна delete/rebuild; archive не комітить transcript; stale cleanup не видаляє active session; migration і recovery tests проходять.

## B-04: Global project selector

**Пріоритет:** P1 після `projects resolve`.

**Запропоноване рішення:** додати consistent `--project <id-or-name>` і `--workspace <path>` до project-sensitive commands. Resolution використовує registry v2 плюс gitignored locations, verifies EIF identity і показує exact target до write.

**Чому deferred:** зміна всіх command parsers і journey tests ширша за continuity resolver.

**Передумови:** proven resolver behavior; command inventory; backward compatibility policy.

**Критерій приймання:** усі project-sensitive commands приймають однаковий selector; ambiguity blocks; dry-run друкує identity/path; synthetic multi-project journeys проходять на Windows і Linux.

## B-05: Загальний policy engine для guarded actions

**Пріоритет:** P1/P2.

**Запропоноване рішення:**

- Machine-readable guarded actions: `package`, `publish`, `deploy`, `delete`, `external_message`, `payment`.
- Required approvals зберігають owner, scope, expiry і evidence reference.
- `eifctl guard check --action ...` працює fail-closed для EIF-managed actions.
- Verified adapter hooks можуть блокувати equivalent shell/tool actions, але docs називають coverage gaps.
- LLM не може auto-approve owner-only action.

**Чому deferred:** generic policy semantics потребують separate architecture/security review; first package застосовує один bounded graphic-design guard.

**Передумови:** enforcement taxonomy, approval schema, adapter capability matrix, audit-log retention decision.

**Критерій приймання:** negative fixtures не обходять EIF-managed actions; expired/out-of-scope approval fails; hook absence reported, а не hidden; owner може revoke безпечно.

## B-06: Adapter-specific exporters для plugins

**Пріоритет:** P2.

**Запропоноване рішення:** professional profile лишається canonical. Generated exporters створюють target packages:

- Codex `.codex-plugin/plugin.json`, `skills/`, optional hooks/MCP metadata;
- Claude plugin/marketplace shape лише за current official contract;
- Cursor/Hermes packages лише для supported native plugin surfaces;
- generated files містять provenance, source digest і compatibility range;
- workflow content не копіюється вручну.

**Чому deferred:** plugin formats vendor-specific і uneven. Universal manifest створив би false parity.

**Передумови:** tested skill-pack contract; official schemas; licensing; generated-output policy.

**Критерій приймання:** source profile round-trips до target package; native validator/install canary проходить; package drift detected; unsupported adapters повертають explicit `NOT SUPPORTED`.

## B-07: Catalog і admission pipeline для external skills

**Пріоритет:** P2.

**Запропоноване рішення:** curated registry зберігає source URL, pinned commit, license, test/eval evidence, permissions, network/install surfaces, local review і compatibility. `inspect` працює read-only; `admit` потребує owner approval та installs у private L2 workspace, а не public EIF by default.

**Чому deferred:** first package визначає gate, але навмисно нічого не imports.

**Передумови:** skill checker; provenance schema; license checker integration; sandbox policy; update/rollback workflow.

**Критерій приймання:** unpinned, unlicensed, untested або unsafe candidates rejected; approved skill можна cleanly remove; upstream updates потребують re-evaluation.

## B-08: Повна multi-model skill eval program

**Пріоритет:** P2.

**Запропоноване рішення:** scheduled або release-gated A/B evals для supported models/adapters. Вимірювати trigger precision/recall, task correctness, forbidden behavior, tool calls, tokens, latency, retries і reviewer findings. Reuse valid baselines лише коли model/settings/prompt/fixtures збігаються точно.

**Чому deferred:** це дорожче і статистично складніше за pilot із двох skills.

**Передумови:** stable fixtures, cost accounting, provider budget, deterministic graders, model-version capture.

**Критерій приймання:** repeat counts і confidence intervals сформульовано чесно; regression threshold blocks release; unsupported cross-model generalization відсутня.

## B-09: Розвиток, deprecation і retirement skills

**Пріоритет:** P2/P3.

**Запропоноване рішення:** findings ledger відстежує trigger misses, unnecessary token use, repeated corrections і model drift. Changes потребують tests first, bounded eval, owner review і version bump. Skills без verified benefit мають deprecate/archive, а не лишатися silently.

**Чому deferred:** потрібні longitudinal evidence з B-08 і real usage.

**Передумови:** usage telemetry без prompt content; eval history; curator policy; rollback.

**Критерій приймання:** кожна automatic recommendation посилається на evidence; self-modification без approval немає; removal improves або preserves verified outcomes.

## B-10: Scaffold для packet і structural validator

**Пріоритет:** P2.

**Запропоноване рішення:** `eifctl packet new` renders 00-07 плюс session files; `packet check` validates anatomy, IDs, `depends_on` graph, DoD mapping, concrete verification, no-touch zones, carry-over dispositions і closeout status.

**Чому deferred:** корисно, але не потрібно для закриття current continuity/skill-quality gaps.

**Передумови:** packet schema decision; compatibility з existing packets; localized templates.

**Критерій приймання:** broken fixtures для missing DoD mapping, cycles, vague checks і lost deferred items мають deterministic fail.

## B-11: Друга хвиля script-first automation

**Пріоритет:** P2.

**Запропоноване рішення:** класифікувати кожний playbook step як `deterministic`, `semantic`, `owner_gate` або `external`. Автоматизувати лише deterministic data collection/render/validation. Candidates: packet structure, closeout evidence collection, curator signal collection, changed-file QA routing і release evidence aggregation.

**Чому deferred:** first packet реалізує три highest-value replacements; broad automation потребує measured benefit і не повинна перетворитися на ritual.

**Передумови:** first audit report; token/time baseline; stable CLI UX.

**Критерій приймання:** кожен new script прибирає repeated model work, має tests і показує lower time/token use без lower quality.

## B-12: Graphic-design runtime toolpack

**Пріоритет:** P2 після release.

**Запропоноване рішення:** optional profile toolpack із pinned, health-checked renderers і analyzers: PDF rendering, image metadata, dimensions/color profile, font/link checks і preview generation. Dependencies explicit і removable; їх відсутність degrades до manual checks.

**Чому deferred:** cross-platform binaries, package size і license/security потребують separate work. Designer-machine test відкладено.

**Передумови:** supported formats; Windows/Linux install strategy; provenance; sample assets safe для public repo.

**Критерій приймання:** clean-machine install, real render canaries, uninstall/rollback, без claims для unsupported formats.

## B-13: Робочий простір artifacts і preview pipeline

**Пріоритет:** P3.

**Запропоноване рішення:** standard task-local directory для editable sources, derived previews, QA reports, delivery manifest і approval state. Derived files reproducible та separated від canonical source. Retention policy запобігає repo bloat.

**Чому deferred:** workflow redesign не є quick continuity fix.

**Передумови:** toolpack, task-state schema, user research, project-specific overrides.

**Критерій приймання:** один real design journey можна resume, review і package без ambiguous files або accidental stale preview delivery.

## B-14: Dependency-aware engine для changed-only QA

**Пріоритет:** P2/P3.

**Запропоноване рішення:** map changed source/assets/templates до impacted outputs і checks. Local leaf change запускає bounded QA; shared token/font/layout/export setting triggers full QA. Agent може propose impact, а script verifies dependency graph там, де це observable.

**Чому deferred:** reliable dependency model відсутня; heuristic automation може пропустити global impact.

**Передумови:** artifact workspace, explicit dependency metadata, real failure fixtures.

**Критерій приймання:** known global-change fixtures завжди escalate; local fixtures уникають unrelated checks; false-negative rate measured.

## B-15: Binary-aware privacy scanner

**Пріоритет:** P2.

**Запропоноване рішення:** safe text/binary classification, scan filenames/metadata/archive manifests без decode arbitrary binaries як text, bounded extractors для supported containers. Unknown binary повертає `NOT SCANNED`, а не PASS.

**Чому deferred:** earlier claimed crash не reproduced на current `0.2.7`; root cause треба isolate до change.

**Передумови:** minimal failing fixture, supported-format list, resource limits, archive-bomb protections.

**Критерій приймання:** original failure спочатку reproduced, потім fixed; text coverage unchanged; malformed/bomb fixtures fail safely.

## B-16: Post-release acceptance на комп'ютері дизайнерки

**Пріоритет:** release gate, навмисно postponed.

**Запропоноване рішення:** після нового release виконати sanitized clean install, profile install, project connection, fresh-session skill discovery, real light task, structured task, approval guard, package smoke і rollback на комп'ютері дизайнерки.

**Чому deferred:** explicit owner instruction забороняє фокус до нового release.

**Передумови:** released artifact і checklist з local candidate; private identities не потрапляють у public repo.

**Критерій приймання:** captured PASS/FAIL для кожного step, version/provenance, discovered defects і rollback result. Retrospective claim із попереднього `0.2.6` run заборонений.

## B-17: Розширений quality-per-token benchmark

**Пріоритет:** P2/P3.

**Запропоноване рішення:** розширити current A/B/C/D benchmark continuity і skill modes. Порівняти no EIF, base EIF, script-first EIF і tested skill pack за fixed task/model/settings/evaluator. Quality вимірюється до cost.

**Чому deferred:** first package дає лише bounded existence evidence.

**Передумови:** stable tasks, repeated runs, budget, model/version pinning, integrity contracts.

**Критерій приймання:** reproducible commands/data, без fabricated confidence interval, з explicit межами generalization.

## B-18: Adapter lifecycle canary suite

**Пріоритет:** P2.

**Запропоноване рішення:** version-bounded disposable canaries для context discovery, skill discovery, same-chat resume, new-chat create/open, hook behavior і checkpoint bootstrap. Canaries не mutate user config automatically.

**Чому deferred:** first packet додає continuity fields і focused tests; full live matrix більша, а деякі UI surfaces потребують human action.

**Передумови:** adapter test harness, disposable projects, provider credentials policy.

**Критерій приймання:** кожна capability claim посилається на source плюс live result; version change invalidates stale evidence.

## B-19: Decision support для task routing

**Пріоритет:** P3.

**Запропоноване рішення:** deterministic hard gates для obvious packet conditions, destructive actions, unresolved approval і multi-session dependencies, зі збереженням agent/owner judgment для ambiguity та risk. Output має explanation, а не opaque score.

**Чому deferred:** heuristic classifier може збільшити process overhead для light tasks.

**Передумови:** real misrouting dataset; cost/quality baseline; override UX.

**Критерій приймання:** відомі under-planning cases detected без примусу trivial fixtures до packet; кожен route explainable і overridable.

## B-20: Sandbox і permission manifest для executable skills

**Пріоритет:** P2 до broad script-backed imports.

**Запропоноване рішення:** кожен executable skill declares commands, network domains, filesystem scope, credentials, dependencies і side effects. Third-party scripts виконуються у bounded environment, де це можливо. Permission expansion потребує re-approval.

**Чому deferred:** current EIF skills instruction-only і first-party. First package додає local scripts/tests, але не external executable import.

**Передумови:** admission pipeline, cross-platform sandbox strategy, secret policy.

**Критерій приймання:** undeclared network/file access blocked або surfaced; dependency lock verified; uninstall видаляє executable payload.

## Пункт, який не входить у backlog EIF

Firecrawl Cloud setup є local Hermes tooling і вже завершений. Це не EIF feature, methodology change, release requirement або packet follow-up, якщо owner окремо не попросить documented optional integration.
