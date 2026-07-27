# Terminology and translation contract

English is the canonical language of the framework. Ukrainian is a supported
project locale. This document keeps the two languages aligned without
translating schema keys, command names, file paths, product names, or named EIF
artifacts.

The terminology has three classes:

- **Standards-aligned.** The concept has an established meaning in an
  international standard or another primary technical source.
- **Industry-established.** The term is common in software engineering, but its
  exact scope depends on context.
- **EIF-defined.** EIF assigns a precise local meaning. The term must be
  introduced as an EIF term, not presented as a universal standard.

## Preferred terms

| Canonical English | Preferred Ukrainian | Class | Usage in EIF |
|---|---|---|---|
| AI system | система ШІ | Standards-aligned | Use for the larger engineered system. A model is only one component of that system. |
| AI agent | агент ШІ | Standards-aligned | Use for software that receives information from its environment and takes actions toward an externally specified goal. |
| AI coding agent | агент ШІ для розробки | Industry-established | Contextual subtype used when the agent works on software. Avoid `ШІ-агент` and `AI-агент` in Ukrainian prose. |
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
| capability | спроможність | Industry-established | A system ability that can be demonstrated. Use `можливість` only in general, non-technical prose. |
| lifecycle | життєвий цикл | Standards-aligned | The states and transitions an artifact passes through. |
| runtime | середовище виконання | Industry-established | Keep `runtime` in code, paths, command output, and named contracts. |
| fallback | базовий шлях | Industry-established | The explicit route used when an optional integration is unavailable. Avoid the calque `фолбек`. |
| session | сесія | EIF-defined scope | One bounded unit of agent work with preparation, execution, verification, and closeout. |
| closeout | закриття сесії | EIF-defined scope | The explicit end of a session, including evidence, open work, and Knowledge Delta. |
| promotion | підвищення рівня | EIF-defined scope | Moving validated knowledge to a broader layer by an explicit decision. Avoid `промоція` and `промоутити`. |
| retrospective | ретроспектива | Industry-established | The outer review across multiple sessions. `Ретро` is acceptable as a short UI label after the full term is introduced. |
| benchmark | бенчмарк | Industry-established | A reproducible evaluation with stated fixtures, modes, measures, and limits. Do not use it for an informal timing claim. |

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

## Reference basis

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
- [Kubernetes components](https://kubernetes.io/docs/concepts/overview/components/)
  provide the established architectural use of `control plane`.
