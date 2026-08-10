# Terminology and translation contract

English is the canonical language of the framework. Ukrainian is a supported
project locale. This document keeps the two languages aligned without
translating schema keys, command names, file paths, product names, or named EIF
artifacts.

The terminology has five classes:

- **Standards-aligned.** The concept has an established meaning in an
  international standard or another primary technical source.
- **Open specification or format.** The term names a published, interoperable
  protocol or repository format. Preserve the name used by that specification.
- **Industry-established.** The term is common in software engineering, but its
  exact scope depends on context.
- **Emerging industry usage.** The term is useful and increasingly common, but
  its boundaries are not settled. Introduce it with a concrete definition and
  do not present it as a standard.
- **EIF-defined.** EIF assigns a precise local meaning. The term must be
  introduced as an EIF term, not presented as a universal standard.

## Concept boundaries

Keep the actor, reasoning component, runtime infrastructure, and governance
method distinct:

| Concept | Responsibility |
|---|---|
| Human | Sets intent, grants authority, accepts risk, and remains accountable for the outcome. |
| AI agent | Plans and executes work toward a goal by using a model, tools, context, and feedback. |
| Large language model | Produces inferences and generated output inside the agent loop. It does not hold project authority or durable project knowledge by itself. |
| Agent harness | Connects the agent loop to model access, tools, state, instructions, policies, permissions, isolation, and verification feedback. |
| EIF | Governs how engineering work retrieves experience, receives authority, produces evidence, and retains validated learning. It does not replace the agent, model, or harness. |

In normal prose, write that the **agent** plans, edits, calls tools, and runs
checks. Name the **model** when the sentence is specifically about inference,
model capability, training-data recall, a context window, or a benchmarked
model configuration. Name the **harness** when the sentence is about the
runtime loop and its connected tools, policies, state, or feedback.

## Preferred terms

### Actors and runtime

| Canonical English | Preferred Ukrainian | Class | Usage in EIF |
|---|---|---|---|
| AI system | система ШІ | Standards-aligned | Use for the larger engineered system. A model is only one component of that system. |
| generative AI | генеративний ШІ | Industry-established | Use for the class of systems that generate content. Do not use it as a synonym for an agent. |
| large language model (LLM) | велика мовна модель (LLM) | Industry-established | Expand on first mention. Use `LLM` thereafter. Name the model only when model behavior is the subject. |
| AI agent | агент ШІ | Standards-aligned | Use for software that receives information from its environment and takes actions toward an externally specified goal. |
| AI coding agent | агент ШІ для розробки | Industry-established | Contextual subtype used when the agent works on software. Avoid `ШІ-агент` and `AI-агент` in Ukrainian prose. |
| agentic AI system | агентна система ШІ | Emerging industry usage | A system organized around one or more agents that pursue goals through iterative reasoning, actions, and feedback. Define the scope when first used. |
| agentic software development | агентна розробка програмного забезпечення | Emerging industry usage | Software development in which agents execute substantial workflow steps under human intent, authority, and review. `Агентна розробка` is acceptable after the full form. |
| agent harness | агентний харнес | Emerging industry usage | The runtime infrastructure around an agent loop: model access, tools, context and state, instructions, policies, permissions, isolation, and verification feedback. On first Ukrainian mention, add `інфраструктура виконання агента`. |
| agent loop | цикл роботи агента | Industry-established | The repeated observe, reason, act, and evaluate cycle. Do not use it for the whole governed development method. |
| autonomy | автономність | Industry-established | The degree of independent action allowed inside declared authority and stop conditions. Autonomy is bounded, not equivalent to absence of oversight. |

### Context and memory

| Canonical English | Preferred Ukrainian | Class | Usage in EIF |
|---|---|---|---|
| system prompt | системний промпт | Industry-established | Instructions placed in the system role or equivalent highest-priority runtime layer. It is one source of context, not the whole context. |
| prompt engineering | проєктування промптів | Industry-established | Designing and refining instructions and examples in prompts. `Промпт-інженерія` may be included as a search synonym, not the preferred Ukrainian form. |
| context engineering | контекстна інженерія | Emerging industry usage | Curating and maintaining the information available to the model during inference, including instructions, tools, external data, retrieved knowledge, and message history. |
| context window | контекстне вікно | Industry-established | The bounded input and generated-token capacity available to a model invocation or model-specific interaction. Do not call it durable memory. |
| session context | контекст сесії | EIF-defined scope | The working state needed to continue one bounded session: current scope, evidence, decisions, dead ends, and next logical steps. |
| logical session | логічна сесія | EIF-defined scope | One bounded EIF work unit with a goal, scope, verification criteria and closeout. It may span one or more sequential physical chats. |
| physical chat | фізичний чат | EIF-defined scope | A runtime conversation container. It is not a methodology layer, durable project memory or a logical-session boundary by itself. |
| continuation mode | режим продовження | EIF-defined scope | The declared `same_chat`, `new_chat` or `auto` strategy for continuing one logical session. Automatic behavior still requires a verified adapter capability. |
| compaction | стискання контексту | Industry-established mechanism | Reducing accumulated interaction history into a smaller continuation state. Use the full Ukrainian phrase, not `компактація`. |
| agent memory | пам'ять агента | Emerging industry usage | An umbrella term for mechanisms that retain or retrieve information across steps or sessions. Always name the actual store and lifecycle when making a technical claim. |
| retrieval | пошук і підвантаження знань | Industry-established | Finding relevant information and bringing it into the working context before a decision or implementation. Use `пошук` when the shorter form is unambiguous. |
| retrieval-augmented generation (RAG) | генерація з доповненням пошуком (RAG) | Industry-established | Generation grounded with retrieved material. RAG is one retrieval pattern, not a synonym for all agent memory or project knowledge. |

### Agent interfaces and repository guidance

| Canonical English | Preferred Ukrainian | Class | Usage in EIF |
|---|---|---|---|
| tool | інструмент | Industry-established | A callable capability exposed to an agent. Name the concrete operation when it matters. |
| tool call | виклик інструмента | Industry-established | One structured request from an agent to an exposed tool. |
| Model Context Protocol (MCP) | Model Context Protocol (MCP) | Open specification or format | Preserve the official name and acronym. Describe it as a protocol for connecting AI applications to external tools and context, not as agent memory. |
| AGENTS.md | AGENTS.md | Open specification or format | Preserve the filename. It is a dedicated repository instruction file for coding agents, not a general name for all project knowledge. |
| agent skill | навичка агента | Industry-established | A reusable capability or instruction package an agent can invoke. Use `скіл` only in code identifiers, direct quotations, or an established product UI label. |
| Agent Skills | Agent Skills | Open specification or format | Preserve the name when referring to the open `SKILL.md` directory format. Do not use it as a generic name for every agent capability. |
| hook | програмний хук | Industry-established | A callback triggered at a declared lifecycle point. `Хук` is acceptable after the full form. Do not call every policy or gate a hook. |
| sandbox | ізольоване середовище | Industry-established | The constrained environment in which code or tools execute. Keep `sandbox` in configuration keys, commands, and product labels. |

### Development workflow

| Canonical English | Preferred Ukrainian | Class | Usage in EIF |
|---|---|---|---|
| workflow | робочий процес | Industry-established | A defined sequence of work states or activities. Prefer the concrete sequence when it is short enough to name. |
| orchestration | оркестрація | Industry-established | Coordination of agents, tools, tasks, or services. Do not use it for a single agent following one instruction. |
| specification | специфікація | Standards-aligned concept | A documented statement of requirements, behavior, or constraints. Name its authority and scope. |
| Specification-Driven Development (SDD) | розробка, керована специфікаціями (Specification-Driven Development, SDD) | Emerging industry usage | A development approach in which specification artifacts drive planning, tasks, implementation, and review. Introduce the English name and acronym on first mention. |
| acceptance criteria | критерії приймання | Industry-established | Observable conditions used to decide whether a result satisfies the declared scope. |
| evaluation | оцінювання | Industry-established | A structured assessment against declared criteria. Use `eval` only in code, dataset names, or after introducing it as shorthand. |
| evaluator | засіб оцінювання | Industry-established | The test, check, rubric, or human review that produces evidence for an evaluation. Name it before an iterative run starts. |
| checkpoint | контрольна точка | Industry-established | A saved continuation state with completed work, evidence, decisions, open risks, and next steps. It is not automatically validated project knowledge. |
| handoff | передавання роботи | Industry-established | Transfer of work and its continuation state between people, agents, or sessions. `Передача` is acceptable in general prose; prefer `передавання роботи` in contracts. |
| long-horizon task | довготривале завдання | Emerging industry usage | Work that spans many agent turns, context compactions, or sessions and therefore needs explicit continuation state and verification. |
| enforcement level | рівень забезпечення виконання | EIF-defined scope | The declared source of a prohibition: `machine`, `adapter`, `owner_gate` or `instruction_only`. The label limits the claim to the mechanism actually verified. |

### Governance, evidence, and durable knowledge

| Canonical English | Preferred Ukrainian | Class | Usage in EIF |
|---|---|---|---|
| governance | керування та нагляд | Standards-aligned concept | Use `керований` for *governed*. In running Ukrainian prose, prefer the concrete phrase `правила, повноваження й нагляд` when it is clearer than the abstract noun. |
| control plane | площина керування | Industry-established | EIF uses the established architecture metaphor for the layer that coordinates knowledge, authority, execution, and evidence. It is not a Kubernetes component. |
| authority to act | повноваження діяти | Industry-established | Concerns permission to perform an action. |
| source authority | авторитетність джерела | Industry-established | Concerns how strongly a source can support a claim. Do not translate this as `повноваження джерела`. |
| source of truth | джерело істини | Industry-established | Use only when one source is canonical for a specific state. Do not use it as a synonym for every authoritative source. |
| evidence | доказ, докази | Standards-aligned | Observable support for a claim, such as test output, a source reference, or a recorded decision. |
| verification | перевірка відповідності | Standards-aligned | Confirms with objective evidence that specified requirements were fulfilled. The short form `перевірка` is acceptable when the object is clear. |
| validation | підтвердження придатності | Standards-aligned | Confirms that the result meets its intended use. Use `валідація` only for a named technical operation such as schema validation. |
| provenance | походження | Standards-aligned | Information about the entities, activities, and people involved in producing an artifact. Keep the schema key `provenance` in English. |
| ontology | онтологія | Standards-aligned | A formalized vocabulary whose terms are defined through their relationships. |
| knowledge base | база знань | Industry-established | The maintained collection of knowledge artifacts. |
| knowledge graph | граф знань | Industry-established | A graph representation of entities and their relationships. A folder of linked Markdown files is graph-shaped knowledge, but it is not automatically an RDF or OWL knowledge graph. |
| project knowledge | знання проєкту | EIF-defined scope | Durable decisions, constraints, facts, risks, and lessons for one project. `Project memory` is acceptable in explanatory product copy only as shorthand for this governed store. |
| capability | спроможність | Industry-established | A system ability that can be demonstrated. Use `можливість` only in general, non-technical prose. |
| lifecycle | життєвий цикл | Standards-aligned | The states and transitions an artifact passes through. |
| runtime | середовище виконання | Industry-established | Keep `runtime` in code, paths, command output, and named contracts. |
| fallback | базовий шлях | Industry-established | The explicit route used when an optional integration is unavailable. Avoid the calque `фолбек`. |
| session | сесія | EIF-defined scope | One bounded unit of agent work with preparation, execution, verification, and closeout. |
| closeout | закриття сесії | EIF-defined scope | The explicit end of a session, including evidence, open work, and Knowledge Delta. |
| promotion | підвищення рівня | EIF-defined scope | Moving validated knowledge to a broader layer by an explicit decision. Avoid `промоція` and `промоутити`. |
| retrospective | ретроспектива | Industry-established | The outer review across multiple sessions. `Ретро` is acceptable as a short UI label after the full term is introduced. |
| benchmark | бенчмарк | Industry-established | A reproducible evaluation with stated fixtures, modes, measures, and limits. Do not use it for an informal timing claim. |
| private workspace | приватний робочий простір | EIF-defined scope | Optional user-owned durable scope inside L2. Keep `workspace` in commands, schema keys, and paths. It is not a private EIF distribution. |
| project registry | реєстр проєктів | Industry-established | The committed logical inventory of connected projects. In v2 it contains no machine-local path. |
| workspace profile | профіль робочого простору | EIF-defined scope | A deterministic selection policy for required, default, optional, and overridden workspace artifacts. |
| workspace materialization | матеріалізація робочого простору | Industry-established mechanism | Staging, hashing, verifying, and pinning selected workspace artifacts into a project. In explanatory prose, prefer `підготувати й зафіксувати вибрані файли` when the mechanism itself is not the topic. |

## EIF-defined terms

### Engineering Intelligence

The phrase is established in industry and often refers to analytics about
software delivery, team performance, or engineering data. EIF keeps its
ratified product name and applies the term to a complementary concern: making
engineering experience reusable in work with AI agents.

> **Engineering Intelligence in EIF** is versioned engineering experience plus
> the methods that govern how an AI agent retrieves, applies, verifies, and
> retains that experience.

Use `Engineering Intelligence` for the named concept and product identity.
`Інженерний інтелект` is the explanatory Ukrainian form. Do not imply that the
EIF definition is an ISO definition or the only industry meaning. This
definition clarifies the product. It does not propose a rename.

### Knowledge Delta

`Knowledge Delta` is a named EIF artifact. It records the validated learning,
evidence, rejected approaches, open questions, and knowledge changes produced
by a session. Keep the English name in both languages. Do not use `Дельта
знань`.

### execution packet

`execution packet` is an EIF work unit for an effort that needs several
sessions. It carries scope, evidence requirements, budgets, decisions, and a
roadmap across those sessions. The phrase is not a settled software-engineering
standard and has other emerging meanings outside EIF. Keep the English name on
first mention. In Ukrainian explanatory prose, follow it with `пакет роботи на
кілька сесій`.

### Bounded Evidence Loop

`Bounded Evidence Loop` is the EIF name for an iterative workflow with an
observable goal, declared evaluator, iteration and remote-run budgets, and
explicit stop conditions. The Ukrainian explanatory form is `обмежений цикл
доказів`. It is a methodology contract, not a claim of autonomous convergence.

### private workspace

`private workspace` is an EIF scope term. It names an optional user-owned
repository that coordinates project identities, local profiles, and selected
operating artifacts across independent projects. It is an EIF project
instance inside L2, not a fourth layer and not a private copy of the public
framework. In Ukrainian prose, use `приватний робочий простір`. Keep
`workspace` unchanged in commands, schema keys, and paths.

## Translation rules

1. Preserve product names, schema keys, command names, file paths, status
   literals, and named EIF artifacts.
2. Translate the surrounding explanation, not the identifier itself.
3. Prefer one clear sentence over a colon followed by a dense list.
4. Use punctuation to show structure, not to carry structure that the wording
   should express.
5. Do not use an em dash in Ukrainian project copy. Rewrite the sentence or use
   a full stop.
6. When an English term has several Ukrainian equivalents, choose by meaning,
   not by surface similarity.
7. Expand an acronym on first mention unless the artifact itself is known
   primarily by that acronym. Preserve canonical acronyms in both locales.
8. Keep actor boundaries explicit. The agent performs the work, the model
   provides inference inside the loop, and the harness connects runtime
   capabilities.
9. Use the same preferred term for the same concept across a publication.
   Vary sentence structure, not technical labels.
10. In Ukrainian, do not insert a comma before a single coordinating `і`, `й`,
    or `та` that joins homogeneous sentence parts. Keep the comma when syntax
    requires it, including between independent clauses, around an inserted
    phrase, or with a repeated conjunction.

## Maintaining the contract

Treat each entry as a concept record, not a word list:

1. Define the concept and its boundary before choosing a label.
2. Keep one preferred label per locale. Record explanatory or search forms
   separately and record deprecated forms under `avoid`.
3. Preserve the exact name of an open specification, named artifact, command,
   path, or schema key.
4. Mark emerging usage honestly. Promotion to `industry-established` requires
   evidence that the meaning has stabilized across independent primary
   sources.
5. Keep `locales/en/terminology.yaml` and
   `locales/uk/terminology.yaml` structurally aligned. Publication tooling may
   consume `preferred`, `explanatory`, `short`, and `avoid` values, but the
   prose definition in this contract remains authoritative.
6. A project may add domain-specific terms, but it must not redefine a
   canonical EIF term. Proposed corrections move upstream into this contract.

## Reference basis

- [ISO 704:2022](https://www.iso.org/standard/79077.html) defines principles
  for linking objects, concepts, definitions, and designations in terminology
  work.
- [ISO/IEC 22989:2022](https://www.iso.org/standard/74296.html) establishes AI
  concepts and terminology.
- [ISO/IEC 42001:2023](https://www.iso.org/standard/42001) defines an AI
  management system and its governance context.
- [ISO/IEC/IEEE 24765:2017](https://www.iso.org/standard/71952.html) is the
  shared vocabulary for systems and software engineering. A third edition is
  under development.
- [IEEE 1012-2024](https://standards.ieee.org/ieee/1012/7324/) distinguishes
  verification against requirements from validation against intended use and
  user needs.
- [NIST AI 100-2e2025](https://csrc.nist.gov/glossary/term/agent) defines an
  agent as software that interacts with its environment and takes
  self-directed actions toward an externally specified goal.
- [W3C PROV](https://www.w3.org/TR/prov-overview/) defines provenance as
  information about how a piece of data or another entity was produced.
- [W3C OWL 2](https://www.w3.org/TR/owl-overview/) describes ontologies as
  formalized vocabularies whose terms are defined through relationships.
- [W3C SKOS](https://www.w3.org/TR/skos-reference/) distinguishes preferred,
  alternative, and hidden labels for multilingual concept schemes.
- [Kubernetes components](https://kubernetes.io/docs/concepts/overview/components/)
  provide the established architectural use of `control plane`.
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  distinguishes context engineering from prompt engineering and describes
  compaction and structured note-taking for longer work.
- [Harness engineering](https://openai.com/index/harness-engineering/)
  documents the emerging engineering practice of designing agent-readable
  repositories, tools, constraints, and feedback loops around coding agents.
- [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-11-25/)
  is the open protocol specification for connecting AI applications to tools
  and contextual data.
- [AGENTS.md](https://agents.md/) defines the open repository instruction
  format for coding agents.
- [Agent Skills specification](https://agentskills.io/specification) defines
  the `SKILL.md` directory format and its progressive-disclosure resources.
- [GitHub Spec Kit](https://github.github.com/spec-kit/) documents the
  specification, plan, tasks, and implementation flow used here as a primary
  example of Specification-Driven Development.
- [The official Ukrainian orthography](https://mon.gov.ua/static-objects/mon/sites/1/zagalna%20serednya/Pravopys.2019/ukrayinskii-pravopis-oficiine-vidannia-2026.pdf)
  governs Ukrainian spelling and punctuation.
