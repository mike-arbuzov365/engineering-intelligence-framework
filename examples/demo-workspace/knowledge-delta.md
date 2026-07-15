## Дельта знань
<!-- Knowledge Delta -->

### Нові факти
<!-- type: fact | confidence: high/medium/low | validated: yes/no -->
- `knowledge/facts/FACT-0001-gregorian-leap-year-rule.md` - правило Gregorian calendar для leap year (confidence: high, validated: yes).

### Нові правила
<!-- type: rule | scope: global/local | застосовується: де саме -->
-

### Нові рішення / ADR
<!-- Посилання на ADR або чернетку -->
-

### Нові ризики
<!-- probability: H/M/L | impact: H/M/L | trigger: коли реалізується -->
-

### Нові edge cases
<!-- Конкретний сценарій + як обробляти -->
- Century-роки, не кратні 400 (1900, 2100) - naive `year % 4 == 0` перевірка дає невірний результат. Оброблено у `PATTERN-0001` і в реалізації `is_leap_year`.

### Відхилені гіпотези
<!-- Що спробували і чому не підійшло -->
-

### Deprecated / застаріла настанова
-

### Інциденти
- **[framework tooling]** Windows console codepage (cp1252) не міг вивести кириличний `print()` у bootstrap/пошукових скриптах - `UnicodeEncodeError` при першому non-ASCII повідомленні. Виправлено `sys.stdout.reconfigure(encoding="utf-8")`.
- **[framework tooling]** Пошук по знаннях не матчив кириличні запити (токенайзер приймав лише `[A-Za-z0-9_-]`), тож україномовний instance генерував українські доки, але не міг retrieve україномовне знання. Виправлено на Unicode-aware токенайзер (`\w[\w-]*`).
- **[framework tooling, round 2]** Bootstrap генерував не той adapter entrypoint (`AGENTS.md` замість `CLAUDE.md`, який Claude Code реально завантажує - підтверджено офіційною документацією через Context7); генерований runtime не був відтворюваним поза framework-checkout (шляхи вели на `scripts/`, яких немає в окремому проєкті); upgrade через `--force` міг мовчки затерти user-owned config settings; provenance записувала placeholder SHA, а не реальний git ref; render-команди у CLAUDE.md лише друкували у stdout, не створювали файли. Усі виправлено: config/lock split, transactional bundle staging+swap з sha256-manifest, dirty-checked provenance, config-driven render-to-file, adapter registry, `.gitignore` management для окремого instance.

### Промоутити у спільну базу знань?
Маршрутизація за scope (не все "корисне" йде у framework core):
- [ ] `PATTERN-0001` (naive leap-year check) - це **domain/project-level** урок (алгоритм календаря), а не про сам фреймворк. **Залишається project-level** у цьому instance. Те, що урок крос-мовний, саме по собі не робить його framework-рівневим.
- [x] **framework-level кандидати** (потребують owner ratification, промоція вручну): усі інциденти tooling вище - non-English console encoding, non-ASCII retrieval, wrong adapter entrypoint, non-transactional upgrade, placeholder provenance - стосуються самих скриптів EIF і повторяться у будь-якому новому instance. Не промоутовано автоматично - лише позначено як кандидати.

### Оновлені файли знань
- `knowledge/facts/FACT-0001-gregorian-leap-year-rule.md` (новий)
- `knowledge/failure-patterns/PATTERN-0001-naive-leap-year-check.md` (новий)
- `knowledge/index.md` (згенеровано `.eif/runtime/eif_generate_index.py`, тепер зі schema-aware класифікацією)
