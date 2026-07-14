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
- Windows console codepage (cp1252) не міг вивести кириличний `print()` у `scripts/eif_init.py` і `scripts/eif_search_knowledge.py` - `UnicodeEncodeError` при першому non-ASCII повідомленні. Виправлено `sys.stdout.reconfigure(encoding="utf-8")` на старті обох скриптів. Це справжній knowledge gap для будь-якого не-English locale на Windows, не лише для цього demo.

### Промоутити у спільну базу знань?
[x] так - `PATTERN-0001` (naive leap-year check) - загальновідомий, cross-language failure pattern, корисний за межами цього demo-instance. Кандидат для `core/` framework-level knowledge, не лише project-scope; owner ratification потрібен перед промоцією (не виконано автоматично).
[ ] ні - залишається локально

### Оновлені файли знань
- `knowledge/facts/FACT-0001-gregorian-leap-year-rule.md` (новий)
- `knowledge/failure-patterns/PATTERN-0001-naive-leap-year-check.md` (новий)
- `knowledge/index.md` (згенеровано `scripts/eif_generate_index.py`)
