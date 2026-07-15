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
- **[framework tooling]** Пошук по знаннях не матчив кириличні запити (токенайзер приймав лише `[A-Za-z0-9_-]`), тож україномовний instance генерував українські доки, але не міг retrieve україномовне знання. Виправлено на Unicode-aware токенайзер.

### Промоутити у спільну базу знань?
Маршрутизація за scope (не все "корисне" йде у framework core):
- [ ] `PATTERN-0001` (naive leap-year check) - це **domain/project-level** урок (алгоритм календаря), а не про сам фреймворк. **Залишається project-level** у цьому instance. Те, що урок крос-мовний, саме по собі не робить його framework-рівневим.
- [x] **framework-level кандидати** (потребують owner ratification, промоція вручну): два інциденти tooling вище - non-English console encoding і non-ASCII retrieval - стосуються самих скриптів EIF і повторяться у будь-якому не-English instance. Це сильніший приклад framework-level знання, ніж сам алгоритм. Не промоутовано автоматично - лише позначено як кандидати.

### Оновлені файли знань
- `knowledge/facts/FACT-0001-gregorian-leap-year-rule.md` (новий)
- `knowledge/failure-patterns/PATTERN-0001-naive-leap-year-check.md` (новий)
- `knowledge/index.md` (згенеровано `.eif/runtime/eif_generate_index.py`)
