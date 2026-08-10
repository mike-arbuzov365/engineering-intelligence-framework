# Model-versus-script audit для current skills

## Межа рішення

Audit охоплює 12 core і 3 starter-profile skills. Він не оцінює якість
моделі й не рекомендує замінити semantic judgment regex або static rule.
`replace_with_script` означає лише deterministic substep із observable input
та fail-closed output.

| Skill | Keep with model | Replace or support with script | Owner gate | Decision |
|---|---|---|---|---|
| `create-professional-profile` | Визначити recurring professional gap і smallest reusable artifact set. | Profile schema, contained paths, catalog collision, `eifctl skills check`, workspace doctor. | Install/activation scope і project connection. | `keep_with_model` плюс existing deterministic validation. |
| `plan-idea` | Problem, user, observations/inference/assumptions, minimum useful scope. | Template/fixture structure, reference existence, approval-state field presence. | Idea approval і external commitment. | `keep_with_model`; structure script-backed. |
| `plan-prd` | User flows, requirements, trade-offs, acceptance semantics. | Durable artifact shape, traceability/reference checks, approval-state presence. | PRD approval і rollout commitment. | `keep_with_model`; deterministic checks only. |
| `plan-execution-packet` | Scope decomposition, risk, decisions, session boundaries. | Existing knowledge search, packet reference/link checks, skill contract. Structural packet checker лишається B-10. | Material scope/architecture/external action. | `keep_with_model`; B-10 deferred. |
| `run-execution-packet` | Реалізація semantic work і adaptation за evidence. | `projects resolve`, `session checkpoint/validate/resume-audit/handoff`, budgets, tests, `skills check`. | Destructive, monetary, publication і unresolved scope decisions. | High-value deterministic state work already replaced by scripts. |
| `review-execution-packet` | Severity, architecture quality, plan-vs-done interpretation. | Fresh Git/hosted state collection, test execution, evidence matrix structure. | Merge, publication і accepted residual risk. | `keep_with_model`; collection scriptable, merge owner-gated. |
| `run-bounded-evidence-loop` | Вибір adaptation і оцінка semantic quality. | Iteration/budget counters, evaluator execution, terminal status, retained failures. | Additional remote spend або unsafe action. | Mixed: deterministic loop state, model adaptation. |
| `run-retro` | Визначити genuinely recurring pattern і prevention value. | Git/activity collection, occurrence counts, link/schema/privacy checks. | Promotion за межі project і new policy. | `keep_with_model`; collectors лишаються B-11. |
| `knowledge-search` | Сформулювати query і застосувати relevant lesson до plan. | `eif_search_knowledge.py`, index freshness, lifecycle filtering, result paths. | Немає для read-only search; decision change лишається owner-gated. | Retrieval already `replace_with_script`; interpretation лишається model. |
| `knowledge-ingest` | Evidence label, artifact type, durable wording, contradiction handling. | Frontmatter/schema, index generation, links і privacy scan. | Shared promotion або policy change. | `keep_with_model` плюс deterministic validators. |
| `knowledge-lint` | Severity, semantic duplication, promotion readiness. | Schema, status, links, index, privacy і fixture checks. | Promotion decision. | Mixed; static checks already scripted. |
| `knowledge-curator` | Ranking, routing, recurrence interpretation, prevention proposal. | Existing signal collection, ledger diff, freshness/schema/link/privacy checks. | Class A apply/PR opt-in; merge forbidden. | `keep_with_model`; broader collector automation B-11. |
| `run-graphic-design-project` | Brief interpretation, direction, visual quality, task sizing. | Skill/profile contracts; SESSION-006 package approval guard; future technical render checks B-12. | Direction approval, final delivery/package approval. | Visual judgment stays model/owner; deterministic guard bounded. |
| `review-graphic-design-delivery` | Brief alignment, readability, series consistency, defects vs taste. | Contract checks; file metadata/render/link checks лише після verified toolpack B-12. | Final approval та delivery. | `keep_with_model`; technical QA deferred, no visual automation claim. |
| `onboard-software-project` | Architecture landmarks, ownership boundaries, stable instructions. | Repository/file discovery, verified build/test execution, profile/skill checks. | Repository adoption, persistent instruction changes, external connection. | Mixed; evidence collection scriptable, synthesis stays model. |

## Implemented у EIF-021

1. Project/session identity, checkpoint rendering, drift audit і handoff strategy
   moved from repeated model formatting to deterministic commands.
2. Skill inventory, local contract structure, references, script declarations,
   trigger fixtures та exact grounding moved to `eifctl skills check`.
3. Eval plan expansion, matched prompt digests, sequential ordering, integrity,
   null metrics і claim boundaries moved to `eif_benchmark.py
   skill-eval-dry-run`.

Ці replacements мають local tests. Вони не доводять lower model quality risk,
бо behavioral comparison не запускався.

## Deferred

- B-08: repeated multi-model eval program.
- B-11: broader deterministic collectors та packet/closeout routing.
- B-12/B-14: graphic toolpack і dependency-aware changed-only QA.
- B-17: quality-per-token benchmark extension після approved budget.

Жоден deferred пункт не є implicit improvement claim.
