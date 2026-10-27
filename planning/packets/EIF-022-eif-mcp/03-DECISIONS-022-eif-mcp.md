---
packet: EIF-022-eif-mcp
type: decisions
status: execution-approved
created: 2026-10-26
---

# Рішення: eif-mcp

Номери `D-NNN` тут локальні для пакета і не збігаються з двозначними номерами `D-NN` реєстру [`core/policies/decisions.md`](../../../core/policies/decisions.md). Жодне рішення нижче не суперечить ratified записам реєстру (перевірено щодо D-06, D-10, D-12, D-14, D-16, D-17, D-18, D-19). Статус `ratified` у цьому файлі набуває чинності після схвалення пакета власником. Числа з міткою "бюджет" це рішення, а не виміри.

## D-001: Форма, ідентичність, обсяг

**Status: ratified.** eif-mcp це підкоманда `eifctl mcp serve`, код у пакеті `engineering_intelligence_framework.eif_mcp`. Один процес обслуговує один EIF-інстанс, транспорт лише stdio. `serverInfo.name` дорівнює `eif-mcp`, версія сервера дорівнює версії установленого пакета. Імена інструментів мають префікс `eif_` і дієслово. Сервер не залежить від інших MCP-серверів і не викликає їх. Фаза 1 лише читання, фаза 2 керовані записи (D-009, D-010). Немає `execute`, `shell`, `sql`, `write_file`.

**Evidence:** вхідне рішення власника (форма eif-mcp), [02-FACTS](02-FACTS-022-eif-mcp.md) розділ 1. Глобальний сервер і workflow-engine суперечать правилу "один корінь на процес" і не зменшують токени.

## D-002: Вибір інстанса і модель процесу

**Status: ratified.** Корінь задається аргументом `--instance-path` або змінною `EIF_INSTANCE_PATH`; аргумент має пріоритет. Мовчазного вибору немає: робочий каталог ніколи не використовується як запасний варіант. На старті сервер перевіряє, що корінь існує, містить `.eif/config.yaml` і `.eif/framework.lock.yaml`, які проходять схеми. Інакше процес завершується з кодом 3 і повідомленням без шляху за межами введеного значення. Якщо інстанс валідний, але є drift чи проблеми doctor, сервер стартує і повідомляє це через `eif_capabilities` та `eif_doctor` (статуси `stale`/`partial`), бо мертвий процес не пояснює агенту причину. Усі шляхи в запитах і відповідях відносні до кореня. Усі читання проходять containment-перевірку (resolve, без виходу поза корінь, без symlink, що виходить).

**Evidence:** `commands/session.py` уже працює з явним `--project-root` і відмовляє на неповному інстансі (`_load_project`); `delivery.check_delivery` робить containment для evidence. Конвенція "один явний корінь на процес".

## D-003: Джерело коду і policy

**Status: ratified.** Код виконується із установленого `eifctl`, імпортованого в процес один раз (без підпроцесів на виклик). Текст policy (skills, playbooks, templates, rules) читається лише з pinned-пакета інстанса: `.eif/runtime/` і `.eif/workspace-runtime/`, за маніфестом lock і з перевіркою хешів. Сервер порівнює версію установленого пакета і digest ресурсів із `framework.lock.yaml` (логіка `_check_installed_package_consistency`) і відображає результат в `drift` (`match`, `mismatch`, `unknown`). Правила за версіями:

- `match`: усе дозволено.
- `mismatch` або `unknown`: читання працюють зі статусом `stale` (або `unknown`) у відповіді, фаза 2 відмовляє з `stale` та вказівкою, що робити (`eifctl upgrade --instance-path .` або встановити пакет потрібної версії).
- Сервер ніколи не лагодить drift, не перегенеровує lock, не торкається `.eif/runtime`. Doctor PASS не досягається підганянням lock під випадково встановлений пакет.

**Evidence:** [02-FACTS](02-FACTS-022-eif-mcp.md) розділ 4: pinned-пакет не містить модулів session, delivery, projects, workspace, workspace_materialization; entrypoint вже комбінує установлений `eifctl` і pinned-скрипти; підпроцес коштує ≈ 1 с імпорту на виклик. `jev_decide`: `installed_inprocess_pinned_content` 0,86, а `pinned_runtime_only` суперечить усім трьом вимогам (поради, не доказ). Рішення D-23 у незлитому релізі 0.2.9 вимагає того ж принципу.

**Наслідки для версій:** інстанс, створений новішим пакетом, ніж встановлений, або навпаки, дає `mismatch`. Користувач бачить причину в `eif_capabilities`, а не помилку запуску. Пакет не підтримує запуск сервера зі "старого" `.eif/runtime` як джерела коду (відхилена альтернатива).

## D-004: Структурований шар замість парсингу тексту

**Status: ratified.** Сервер викликає публічні функції, що повертають типізовані dict. Парсинг stdout/stderr, `redirect_stdout` і підпроцеси `eifctl` заборонені як джерело результату. Для операцій без такої функції SESSION-002 витягує її з наявного коду (doctor, session validate/audit/checkpoint, render preview/apply) або додає нову (статус пакета, brief, capabilities, доступ до артефакту), а CLI перебудовується так, щоб друкувати з цих функцій. Вивід наявних команд лишається побайтово тим самим: перед рефакторингом знімаються golden-знімки stdout, stderr і кодів виходу на матриці фікстур, і вони перевіряються після. Нова логіка лежить у пакеті `src/engineering_intelligence_framework/`. Зміни в `scripts/eif_*.py` (джерело істини для `_impl`) супроводжуються `python scripts/sync_package_sources.py`.

**Evidence:** [02-FACTS](02-FACTS-022-eif-mcp.md) розділ 3: `session._audit_checkpoint` і `delivery.check_delivery` вже повертають дані, `Report` у verify_runtime будується всередині `main`, `render` має лише `main(argv)`. `jev_decide`: `extract_structured_service` 0,99. Відхилено: `capture_stdout_parse` (глобальний `sys.stdout`, крихкий текстовий контракт), `reimplement_in_mcp` (друга реалізація).

## D-005: Каталог фази 1 (лише читання)

**Status: ratified.** Дев'ять інструментів. Усі з annotations `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true`, `openWorldHint=false`, заданими явно (значення за замовчуванням SDK це `destructiveHint=true` і `openWorldHint=true`, тож пропуск annotations оголошував би небезпеку). Жодна схема не має поля-шляху, `additionalProperties: false` скрізь.

| Інструмент | Вхід | Core-функція | Статус функції | Вихід (brief) |
|---|---|---|---|---|
| `eif_capabilities` | немає | `capabilities()` над `version`, `_load_project`, перевіркою пакета | нова композиція | версії (сервер, eifctl, SDK), identity інстанса (id, name, adapter, profile, locale, 12 hex хешів config і lock), `drift`, режим `reader`/`writer`, чи клієнт оголосив elicitation, каталог (ім'я, effect), ліміти |
| `eif_brief` | `task_kind` | `brief(task_kind)` | нова | маршрут: skill, шлях runtime-джерела і розмір, read-list (шлях і байти, не вміст), інструменти воріт для цього виду задачі, стисла картина стану: verdict doctor, назви перевірок, що впали, лічильники відкритих checkpoint, активний пакет |
| `eif_artifact_get` | `kind` (`skill`/`playbook`/`template`/`rule`), `name`, `section?`, `max_chars?`, `cursor?` | `artifact_get(...)` | нова | текст секції (за slug заголовка) з `truncated`/`next_cursor` або список секцій і їхніх розмірів, якщо `section` не задано |
| `eif_knowledge_search` | `query`, `type?`, `top?`, `status?` | `eif_search_knowledge.search` | є | рядки (шлях, type, status, score, stale, excerpt ≤ 240 символів), `coverage` (індексовано, malformed, schema_invalid, skipped_by_status) |
| `eif_packet_status` | `packet?` (id каталогу) | `packet_status(...)` | нова | список пакетів або сесій одного: статус, `depends_on`, є checkpoint, статус closeout, `next_session` або причина, чому її не визначено |
| `eif_doctor` | `detail?` | `doctor_report()` | витягти з `eif_verify_runtime.main` і `commands/doctor` | verdict, назви перевірок, що впали, перші 5 проблем на перевірку |
| `eif_session_validate` | `session_id` | `session_validate()` | витягти з `_validate_checkpoint` | verdict, список помилок |
| `eif_session_resume_audit` | `session_id` | `session_resume_audit()` | витягти з `_audit_checkpoint` | verdict, розбіжності (категорія, expected, actual, обмежено), `next_action` з checkpoint |
| `eif_delivery_check` | `action` (`package`/`final_delivery`), `scope` | `delivery.check_delivery` | є | `pass`/`blocked`, причина, `enforcement=machine`, `external_shell_enforcement=instruction_only`; для не-design профілю `unavailable` з причиною |

Каталог статичний: список інструментів не залежить від профілю інстанса, застосовність повідомляється у відповіді. `session_id` це лише ім'я за регулярним виразом `session.py`, шлях `.session-context/<id>.md` будує сервер. `eifctl session handoff` не входить у каталог: він лише друкує стратегію, а виклик чату від імені агента заборонений у EIF-021.

**Evidence:** вхідна пропозиція власника для фази 1 покриває сім із дев'яти. `eif_capabilities` потрібен за правилом, що кожен сервер має інструмент стану. `eif_artifact_get` додано як уточнення вхідного рішення: без нього "brief плюс деталі окремим викликом" неможливий, а секційне читання це єдиний виміряний резерв (розділ 2 фактів: проходи по 15-16 KB). Якщо секційний доступ не дасть виграшу на G1, інструмент прибирається (Open O-3, D-017).

## D-006: Конверт відповіді, статуси, помилки, межі

**Status: ratified.** Кожна відповідь це структурований об'єкт: `status` (`ok`, `partial`, `unavailable`, `stale`, `unknown`, `truncated`), `request_id`, `data`, за потреби `next_action`, `truncated`, `next_cursor`. Поле `content` містить той самий об'єкт компактним JSON без відступів (хости показують моделі різні поля). Статуси `partial`, `unavailable`, `stale`, `unknown`, `truncated` не означають успіх і не означають "нічого немає". Твердження "артефакта немає" допустиме лише з відомим покриттям (`coverage` у пошуку). Помилки типізовані з `retryable` і підказкою наступної дії: `validation_failed`, `not_found`, `source_unavailable`, `result_truncated`, `version_conflict`, `idempotency_conflict`, `outcome_unknown`, `requires_host_action`, `approval_declined`, `dependency_unavailable`, `cancelled`. Чужий або неіснуючий об'єкт це `not_found`. Текст помилки не містить стек, абсолютні шляхи, значення змінних середовища, вміст файлів.

Межі (бюджет):

| Параметр | Значення |
|---|---|
| Жорстка межа відповіді | 24 576 байт |
| `eif_brief`, типова цільова | ≤ 1 536 байт, жорстка ≤ 4 096 |
| `eif_artifact_get` `max_chars` | типово 4 000, максимум 12 000 |
| `eif_knowledge_search` `top` | типово 5, максимум 20; excerpt ≤ 240 символів; переліки skipped/malformed ≤ 20 із лічильником |
| `eif_doctor` | перші 5 проблем на перевірку, кожна ≤ 240 символів; `detail=true` до жорсткої межі |
| Опис інструмента | ≤ 280 символів |
| `tools/list`, режим reader | ≤ 6 144 байти |
| `tools/list`, режим writer | ≤ 9 216 байт |
| Дедлайн читання / запису | 15 с / 30 с |

Курсори непрозорі, живуть 10 хвилин. Обрізання завжди явне. Збільшення будь-якої межі потребує нового рішення з доказом.

**Evidence:** правила власника для MCP-серверів (brief за замовчуванням, явні межі, виміряний `tools/list`, таймаути читання 15 с). Числа підібрано від виміру на синтетичному інстансі: прохід по skill до 15,9 KB, найбільший окремий playbook 9 462 байти (`knowledge-curator`), найбільший template 8 574 байти. Жорстка межа 24 KiB вміщує будь-який окремий артефакт цілком, `max_chars` 12 000 покриває найбільший playbook, а типове значення 4 000 розраховане на секцію, а не на файл. Це бюджет, а не вимір. SESSION-003 вимірює фактичний `tools/list`, і порушення бюджету потребує нового рішення, а не мовчазного підвищення.

## D-007: Brief і доступ до артефактів без дублювання policy

**Status: ratified.** Сервер не містить власного тексту методології. `eif_brief` будується лише з метаданих: `description` у frontmatter skill, маніфест lock, заголовки й розміри файлів, стан із функцій D-005. Відповідність `task_kind` до skill це один малий JSON-ресурс пакета (не більше десяти значень: `light`, `structured`, `idea`, `prd`, `packet_plan`, `packet_run`, `packet_review`, `knowledge_search`, `knowledge_ingest`, `retro`), що перевіряється тестом дрейфу проти skills установленого пакета. `light` не веде до skill: brief каже працювати напряму без файлів. `eif_artifact_get` читає лише ті артефакти, що перелічені в маніфесті lock інстанса (`.eif/framework.lock.yaml` і `.eif/workspace.lock.yaml`), перевіряє sha256 файла проти маніфесту (розбіжність дає `stale`), не приймає шлях, а секцію знаходить за заголовком Markdown. Класу "generic read file" не існує.

**Evidence:** D-007 реєстру (одне канонічне джерело на workflow). Генерований loader skill уже каже читати лише pinned-джерело. Дублювання тексту playbooks у сервері створило б другу політику.

## D-008: Конвенція прогресу сесій пакета

**Status: ratified.** `eif_packet_status` не виводить прогрес з історії Git і не вгадує. Канонічний словник `status` файла запуску сесії: `prepared`, `in_progress`, `completed`, `blocked`, `deferred`. Значення поза словником (історичні `prepared-awaiting-owner-approval` тощо) читаються як `legacy` із збереженим сирим текстом і ніколи не вважаються завершеними. Виконавець оновлює `status` файла запуску на початку й наприкінці сесії, а `07-CLOSEOUT` веде за шаблоном. `next_session` обчислюється як перша за порядком roadmap сесія зі статусом `prepared` або `in_progress`, усі `depends_on` якої `completed`. Якщо хоч одна сесія `legacy`/відсутня, відповідь `partial`, `next_session: null` з причиною. SESSION-002 вносить мінімальну правку шаблона `templates/session-launch.md`, playbook `execution-packet-execution.md` і skill `run-execution-packet` з цим словником. Це методологічна зміна, тож вона оформлюється як пропозиція `provisional` рішення (D-020).

**Evidence:** [02-FACTS](02-FACTS-022-eif-mcp.md) розділ 7: у пакетах EIF-020 і EIF-021 файли запуску після виконання лишаються `prepared*`, а `.session-context/` видаляється під час closeout. Без конвенції "наступна сесія" була б вигадкою.

## D-009: Фаза 2: вмикання і каталог

**Status: ratified.** Інструменти запису реєструються лише за явного прапорця запуску `--writes` (або `EIF_MCP_WRITES=1`), що задає власник у конфігурації клієнта. Без прапорця сервер має 9 інструментів і не може змінити файл. З прапорцем додаються п'ять:

| Інструмент | Клас | Вхід | Дія | Core |
|---|---|---|---|---|
| `eif_checkpoint_prepare` | `preview` | поля checkpoint (як у `session checkpoint`), типізовані списки | будує новий вміст `.session-context/<id>.md` і diff до наявного | `session_checkpoint_plan()` витягти з `_checkpoint` |
| `eif_evidence_prepare` | `preview` | `session_id`, `command`, `result` (`pass`/`fail`/`skipped`/`not_run`), `evidence?` | додає один запис до `verification.checks` наявного checkpoint (append-only) | той самий шар |
| `eif_render_prepare` | `preview` | `artifact` (`knowledge_delta`/`session_closeout`), `fields`, `force?` | рендерить текст (відповідає `--stdout`) і ціль запису | `render_preview()` витягти з `eif_render` |
| `eif_commit` | `controlled` | `subject_id`, `idempotency_key` | після схвалення атомарно записує prepared subject | `*_apply()` |
| `eif_operation_get` | `read` | `idempotency_key` | повертає receipt або стан за намірами | нова |

"Evidence" не є новим типом артефакту: це запис у `verification.checks` існуючої схеми checkpoint, лише додавання. Цілі запису лише `.session-context/<session_id>.md`, `knowledge-delta.md` і `session-closeout.md` у корені інстанса (типові шляхи `eif_render`). Інших цілей немає.

**Evidence:** `controlled` вимагає точного preview і схвалення (правила власника). Окремі prepare-інструменти дозволяють правильно оголосити `readOnlyHint=true` для preview і `false` для commit. Режим `--writes` тримає `tools/list` читача малим і робить запис рішенням власника, а не моделі.

## D-010: Протокол схвалення фази 2

**Status: ratified.** Модель не схвалює себе. Жодна вхідна схема не містить полів схвалення (`approved`, `confirm`, `explicit_user_intent` тощо), а зайве поле дає `validation_failed`.

1. **Prepare чистий.** Не пише файлів. Створює subject у пам'яті процесу: `kind`, identity інстанса, `config_sha256`, `lock_sha256`, відносна ціль, `base_sha256` (поточний вміст цілі або null), `new_sha256`. `subject_sha256` це sha256 канонічного JSON цього subject. `subject_id` це випадковий 128-бітний непрозорий ідентифікатор. TTL 600 с. Відповідь містить preview (≤ 4 096 байт: diff або голова тексту), перші 12 hex `subject_sha256`, ціль і `expires_in`. Subject не переживає перезапуск процесу.
2. **Commit бере лише `subject_id` та `idempotency_key`.** Сервер заново зчитує ціль і identity: розбіжність `base_sha256`, config чи lock це `version_conflict`, запису немає. `drift` версії пакета (D-003) це `stale`, запису немає.
3. **Схвалення дає людина через host.** Сервер надсилає клієнту запит elicitation (режим form) з точним підсумком: вид, ціль, перші 12 hex хеша, обсяг змін, булеве поле `approve`. Приймається лише `action=accept` і `approve=true`. Очікування 120 с, після цього `requires_host_action`, запису немає, subject лишається чинним до TTL. `decline`/`cancel` це `approval_declined`.
4. **Клієнт без elicitation.** Якщо в `initialize` клієнт не оголосив можливості elicitation, commit відмовляє з `requires_host_action` і повертає точну еквівалентну CLI-команду для людини. Запасного файлового "схвалення" у пакеті немає: його може підробити будь-який агент із shell у тому самому акаунті, тож позначка `owner_gate` для нього була б неправдою.
5. **Одноразовість.** Subject споживається першим схваленим commit (успішним чи ні). Відмова людини його не споживає. Минулий TTL знищує.
6. **Ідемпотентність і receipt.** Перед записом сервер зберігає `intent` (ключ, `request_sha256`, ціль, `new_sha256`, без вмісту) в `.eif/local-state/mcp/intents/`, потім атомарно записує ціль, потім receipt у `.eif/local-state/mcp/receipts/`. Повтор із тим самим ключем і тим самим запитом повертає первісний receipt без другого запису. Той самий ключ з іншим вмістом це `idempotency_conflict`. Після таймауту чи падіння `eif_operation_get` порівнює стан цілі з `new_sha256` і повідомляє `applied`, `applied_without_receipt` або `not_applied`. Сліпих повторів немає.
7. **Журнал** `.eif/local-state/mcp/audit.jsonl` містить час, інструмент, `request_id`, `subject_sha256`, результат і не містить вмісту.
8. **Позначка enforcement:** `owner_gate`, сила якого залежить від клієнта (UI справді показує людині запит). Хост, що автоприймає elicitation (є вторинні повідомлення про такі режими), знищує гарантію. Тому: `eif_capabilities` повертає `approval: owner_gate_via_host_elicitation` і попередження, що це `instruction_only` щодо shell-агента, а README не заявляє enforcement без canary кожного клієнта (G2).

**Evidence:** запит власника ("точний preview, host-схвалення, одноразовість, прив'язка до subject"). Прецедент у репозиторії: `delivery check` чесно друкує `approval_origin=owner_gate` і `external_shell_enforcement=instruction_only`. Розділ 6 фактів: підтримка elicitation нерівномірна (вторинні джерела: Claude Code з 2.1.76, умовна у Codex, з помилками в Cursor, Hermes невідомо), тому фазу 2 прив'язано до воріт G2 і гілки B, а не обіцяно безумовно. Відхилена альтернатива: файл схвалення в `local-state`, який записує окрема команда для людини. Агент із shell у тому самому акаунті може створити такий файл сам, тому гарантія `owner_gate` була б неправдивою. Це питання безпеки, тож вирішено за принципом "не заявляти зайвого".

## D-011: Межа делегування чесно позначена

**Status: ratified.** Правило воркспейса "checkpoint, closeout, evidence і Knowledge Delta пише активний агент, делегат не пише" лишається чинним, але сервер не може його забезпечити: MCP не повідомляє, чи викликає інструмент активний агент чи субагент, що успадкував підключення. Тому межа делегата позначається `instruction_only`; опис інструментів запису каже "лише активний агент"; схвалення людини на кожен commit лишається єдиним технічним бар'єром; audit-журнал дозволяє постфактум побачити, що писалось. Жодної перевірки "ідентичності викликача" сервер не вдає.

**Evidence:** розділ 7 фактів, пункти 4-5. Правило D-21: вимоги не можна подавати як enforcement без технічного блока.

## D-012: Межі: чого eif-mcp не робить

**Status: ratified.**

- Читає лише всередині кореня інстанса (D-002) і лише такі джерела: `.eif/config.yaml`, `.eif/framework.lock.yaml`, `.eif/workspace.lock.yaml`, артефакти з маніфесту в `.eif/runtime` та `.eif/workspace-runtime`, кореневий каталог knowledge з конфігу (лише якщо він усередині кореня, інакше `unavailable`), `planning/packets/` (змінюється `--packets-root`, відносно кореня), `.session-context/*.md`, `.eif/local-state/design-delivery-approval.yaml` (через delivery check), Git у режимі читання через наявний знімок session.
- Ніколи не читає `.env*`, `.git/` напряму, імена `credentials`/`secrets` (повторює `SECRET_SOURCE_NAMES`), інші інстанси, реєстр проєктів, checkout воркспейса, конфіг клієнтів у домашньому каталозі.
- Ніколи не виконує довільні команди й не відкриває мережу. Єдині підпроцеси це фіксований список `git`-викликів наявного знімка session без shell.
- Ніколи не змінює lock, config, runtime, entrypoint, реєстр і не ремонтує drift.
- У фазі 1 нічого не пише. У фазі 2 лише три види цілей з D-009.
- Не є authority для фактів поза репозиторієм інстанса. Відповіді про особисту пам'ять, дані клієнта чи tenant лежать в інших серверах, а eif-mcp їх не бачить, не кешує і не передає.
- Логи й повідомлення про помилки без вмісту документів, без значень середовища, зі шляхами лише відносними.

**Evidence:** конвенція "особисті дані не копіюються між серверами"; `SECRET_SOURCE_NAMES` у `commands/session.py`; правило "EIF не змінює user-level конфіг" з `integrations/vendor-docs/README.md`.

## D-013: Пакування

**Status: ratified.** `pyproject.toml` отримує optional extra `mcp` із залежністю `mcp` на мажор 2 (нижня межа дорівнює версії, перевіреній у SESSION-001, верхня `<3`; точний пін фіксується в S1). SDK v1 не підтримується: `FastMCP` у v2 видалено, а дві гілки подвоїли б матрицю тестів. Імпорт SDK лише всередині `eif_mcp`, ліниво. Без extra `eifctl mcp --help` працює, а `eifctl mcp serve` виходить з кодом 2 і підказкою `pip install "engineering-intelligence-framework[mcp]"`, без traceback. Ядро, bootstrap, адаптери і doctor не залежать від extra. Нові модулі живуть у пакеті, а не в `scripts/`; усе, що змінюється в `scripts/`, `docs/`, `core/schemas/`, `templates/`, `playbooks/`, `skills/`, `integrations/`, `adapters/`, `locales/`, супроводжується `python scripts/sync_package_sources.py`. Ліцензійний контур extra окремий: `sbom-mcp.cdx.json`, розділ у `THIRD_PARTY_NOTICES.md`, перевірка `eif_check_licenses.py --environment` у чистому venv з extra; невідома чи заборонена ліцензія залежності це fail-closed, виняток лише від власника. Тести з SDK не вимагають SDK у базовому smoke: вони пропускаються з явним повідомленням `SKIPPED: mcp extra not installed` і входять в інвентар `run_all.py`. Каталог інструментів лежить у JSON, який перевіряється проти документації без SDK. Зміна hosted CI це дія власника.

**Evidence:** розділ 5 фактів: 14 прямих залежностей `mcp 2.1.1` проти двох у бази, v2 прибрав `fastmcp`, SBOM покриває лише базове замикання, D-14 тримає рутинний CI в один job.

## D-014: Компактний блок entrypoint і слот інтеграції

**Status: ratified.** eif-mcp це необов'язкова інтеграція за зразком наявних (D-10): слот `integrations.eif_mcp` у `.eif/config.yaml`, за замовчуванням вимкнений, відсутність дорівнює вимкненню. Поки слот вимкнений, ні генерований блок, ні поведінка команд не змінюються. Коли `enabled: true`, `eifctl init/upgrade` генерує компактний варіант блока з бюджетом ≤ 2 400 байт: ідентичність, вказівка викликати `eif_brief(task_kind)` на початку, і запасний шлях на випадок, коли інструменти eif-mcp недоступні в сесії (три прямі команди: `eifctl doctor`, пошук knowledge, посилання на operating-protocol playbook). Запасний шлях не скорочується до нуля, бо сервер може бути не підключений в одній із сесій. Компактний варіант проходить marker-перевірки й drift-перевірку doctor, має тести для чотирьох адаптерів і двох мов, відкат це `enabled: false` плюс `eifctl upgrade`. Варіант постачається лише якщо пройдено G1c (D-017); інакше сервер лишається корисним як дисципліна, але блок не скорочується і про токени нічого не заявляється. Doctor не може перевірити клієнтський бік, тому слот має стан `configured`, а локальну перевірку працездатності дає окрема команда `eifctl mcp serve --self-test` (сервер запускає сам себе через SDK-клієнт по stdio і викликає `eif_capabilities`).

**Evidence:** розділ 2 фактів: блок уже 6,7 KB, а `tools/list` додає власну ціну, тож скорочення блока без виміру не є вигодою; D-10 і наявний прецедент слотів `integrations`.

## D-015: Інтеграція з адаптерами і чесність тверджень

**Status: ratified.** EIF не встановлює сервер і не змінює конфіг клієнта. Генерується лише перевірюваний шаблон для кожного з чотирьох клієнтів у `integrations/eif-mcp/generated/` із `installed: false` і `user_config_mutated_by_generator: false` (за зразком vendor-docs), у двох варіантах: reader і writer. Шаблони попереджають не додавати `eif_commit` до auto-allow і не вмикати автоприйом elicitation. Місця конфігурації беруться з таблиці vendor-docs; формат Hermes (`json` чи інший) перевіряється довідкою CLI у S4 і до цього позначений `unverified`. Для кожного клієнта в `adapters/parity-matrix.json` додається запис `mcp_client` зі статусом (`verified`, `configured-not-verified`, `not-available`), версією клієнта, `evidence_status` і дією. Це сила доказу, а не рівні підтримки (D-16 реєстру). Статус eif-mcp у таблиці можливостей README це `Experimental`, доки жоден клієнт не дав збереженого доказу canary. Enforcement через hook нікому не заявляється.

**Evidence:** розділ 6 фактів; `adapters/README.md` (hook-контракти різні й жоден не верифікований наскрізно для цієї мети); прецедент `parity-matrix.json` для continuity (`status`, `enforcement`, `evidence_status`, `action`).

## D-016: Тестування і приймання

**Status: ratified.** Рівні, жоден не замінює інші:

1. Юніт-тести core без моделі, golden-тести CLI (D-004).
2. In-memory `Client(server)` для протоколу, схем, annotations, обрізання.
3. Підпроцес `eifctl mcp serve` по stdio зі справжнім SDK-клієнтом. Негативна матриця (обов'язкова): відсутній або не-EIF корінь, шлях поза коренем, symlink назовні, `..` та абсолютні шляхи в аргументах, `.env` і `credentials` в імені, зайві поля у вхідних даних, надто великий результат, недоступне джерело (відсутній knowledge-каталог, відсутній runtime), drift версії, зламаний lock, дві одночасні виклики, відміна виклику, кінець stdin, kill посеред виклику.
4. Тест установленого wheel у чистому venv з extra і без нього (регресія бази).
5. Canary реальних клієнтів із збереженим журналом клієнта і версією. Синтетичний SDK-клієнт цього не замінює. Виклик моделі для canary це витрата, тож діє Open O-6: без дозволеного числа ходів canary-статуси лишаються `configured-not-verified`.
6. Для кожного виправленого дефекту тест, що падає без виправлення.
7. 10 eval-питань за `mcp-builder` (незалежні, лише читання, перевірні рядковим порівнянням, на синтетичній фікстурі), відповіді перевірені вручну через in-memory клієнт, статус прогону моделлю `NOT RUN`. Скрипти `mcp-builder` не запускаються.
8. Поведінкове порівняння за D-19 лишається `DEFERRED` без бюджету (D-017).

**Evidence:** правила власника для тестування MCP; прецедент EIF-021 (детермінований dry-run без моделі, поведінкове `DEFERRED`).

## D-017: Токенові твердження, ворота G1 і G2, перевимірювання

**Status: ratified.** Дозволені твердження: "статичний footprint сценарію X на старті на N байтів більший або менший за B0, метод такий-то". Заборонені: "економія токенів у використанні", "дешевше", будь-яке число без відтворюваного виміру (D-12) і без зіставного порівняння якості (D-19). Оцінка токенів `ceil(bytes / 4)` завжди позначається як оцінка.

**G1 (кінець фази 1)** вимагає всього:
- (a) усі тести DD-03..DD-09 зелені;
- (b) виміряний `tools/list` режиму reader ≤ 6 144 байти, або порушення зафіксоване новим рішенням;
- (c) жодного відкритого P0/P1 серед власних findings.

**G1c (лише для компактного блока і будь-якого твердження про footprint):** у найгіршому випадку (хост завантажує `tools/list` цілком) статичний footprint сценаріїв `packet_run` і `packet_plan` на ≥ 15 % менший за B0, де "після" = компактний блок (виміряний у S7, до того бюджет 2 400 байт) + frontmatter skills + виміряний `tools/list` + виміряні типові відповіді brief і секційних читань. Регрес сценарію `light` фіксується, і якщо він понад 15 %, README каже, що легкі задачі можуть коштувати більше, поки хост не відкладає схеми. Провал G1c не зупиняє пакет: компактний блок не постачається, токенових тверджень немає.

**G2 (початок фази 2):** принаймні один із чотирьох клієнтів показав збережений `OBSERVED` повний цикл elicitation (accept, decline, таймаут або cancel) на встановленій версії через тестовий probe-сервер, що не входить до постачання, і людина справді бачила запит. Якщо canary не можна виконати через бюджет O-6, G2 вважається не пройденим і пакет іде гілкою B без зупинки.

**Перевимірювання:** B0 перевимірюється першим кроком SESSION-001 на тодішньому `origin/main`. Якщо виміряні байти відрізняються від записаних у [evidence](evidence/baseline-2026-10-26.json) (наприклад, після злиття релізу 0.2.9), нова лінія замінює стару в фактах із записом причини, а порогові значення цього рішення застосовуються до нової лінії. Пороги змінюються лише новим рішенням.

**Evidence:** D-12, D-19 реєстру. Чесний висновок розділу 2 фактів: на легких задачах `tools/list` може перекрити виграш, на пакетних виграш можливий, але не доведений. Пороги 15 % і бюджети це рішення пакета для виключення "успіху через перевизначення", а не виміри.

## D-018: Одночасність, дедлайни, спостережуваність

**Status: ratified.** Виклики виконуються по одному (блокування), бо core використовує процес-глобальний стан (контекстний менеджер ресурсів, `cwd` в git-викликах). Кожен виклик має дедлайн із D-006. Запис, що перевищив дедлайн, повертає `outcome_unknown`, а не повторюється. Журнал йде лише в stderr як рядки JSON: час, `request_id`, інструмент, статус, тривалість, байти відповіді; значень аргументів не містить. `request_id` (uuid4 hex) повертається у відповіді. Процес завершується на EOF stdin без залишку. Коди виходу: 0 нормально, 2 помилка використання або відсутній extra, 3 недійсний корінь. Обробники нічого не друкують у stdout. Жоден обробник не читає змінні середовища, крім двох задокументованих.

**Evidence:** розділ 5 фактів (v1 не захищає stdout, тож надійність не спирається на поведінку v2); правило "логи без вмісту".

## D-019: Структура сесій і гілки

**Status: ratified.** Вісім сесій, послідовно, одним відповідальним агентом (не більше восьми, остання closeout). Фаза 1 це SESSION-001..005, ворота G1 у кінці SESSION-005. Фаза 2 це SESSION-006 і частина SESSION-007, ворота G2 на початку SESSION-006. Гілки виконання:

- **A:** G1 та G2 пройдені, повний обсяг.
- **B:** G2 не пройдено (немає elicitation чи немає бюджету canary). SESSION-006 не виконується, її обсяг лишається в closeout як `deferred` із причиною, SESSION-007 скорочується до адаптерів, документації та компактного блока (якщо G1c пройдено), render-інструменти не робляться. Остаточний статус пакета `implementation-complete-integration-deferred`.
- **C:** G1 (a) або (b) не пройдено після трьох ітерацій виправлення в SESSION-003/004. Далі не йти, повернути звіт із відкритими питаннями.

Кожна сесія має власний файл запуску, boolean exit і заборонену зону. Сесії не делегуються і не виконуються паралельно. Обмежену роботу всередині сесії можна делегувати за правилом воркспейса (повернення на перевірку, запис у checkpoint, що саме делеговано і чим перевірено).

**Evidence:** вимога обмежити пакет 8 сесіями з воротами між фазами; розділи 6 і 7 фактів показують, що G2 залежить від зовнішніх обставин, тому гілка B вбудована, а не залишена питанням до власника.

## D-020: Робота з реєстром рішень, релізом 0.2.9 і Knowledge Delta

**Status: ratified.** Пакет не редагує ratified записи реєстру. У SESSION-008 пропонуються `provisional` записи: (1) eif-mcp це необов'язковий адаптер на інстанс над `eifctl`, не четвертий шар, не authority і не залежність ядра; (2) словник статусу файла запуску сесії (D-008). Їхні номери беруться першими вільними на момент merge (на дату пакета `main` закінчується на D-21, а незлитий реліз 0.2.9 уже займає D-22 і D-23), тож номер визначається з актуального `origin/main`, не з цього файла. Перед SESSION-001 і перед SESSION-008 робиться `git fetch` та rebase на актуальний `origin/main`. Якщо реліз 0.2.9 уже в `main`, враховується D-22 (RTK виходить з поверхні EIF): жодних команд чи інструкцій про RTK у артефактах цього пакета не додається. Версія пакета й дата релізу не змінюються (release це дія власника), запис у `CHANGELOG.md` лише в секції `Unreleased`.

**Evidence:** `core/policies/decisions.md` (D-21 провізіональний, нумерація); прочитаний на читання worktree релізу 0.2.9 (D-22, D-23).

## Amending a ratified decision

Ratified рішення не редагується на місці. Нове рішення вказує, яке замінює, і старе отримує `superseded by D-NNN`.

## Open (not yet decided)

Кожен пункт має типову відповідь, тож жоден не зупиняє виконання.

- **O-1. Канал схвалення фази 2.** Чи підтримує elicitation хоча б один клієнт на встановленій версії. Тригер: canary у SESSION-005. Типово: гілка B (D-019).
- **O-2. Стабільність API SDK v2.** Версія закріплюється в SESSION-001. Тригер: будь-яка зміна, що ламає тести. Типово: лишатись на закріпленій версії, нову перевіряти окремою сесією.
- **O-3. Чи відкладають хости схеми інструментів.** Впливає на реальну ціну `tools/list`. Тригер: спостереження в canary (без витрат моделі, якщо клієнт показує токени чи контекст). Типово: рахувати найгірший випадок (D-017), реальну ціну не заявляти.
- **O-4. Формат конфігурації Hermes для MCP.** Тригер: довідка CLI Hermes у SESSION-004. Типово: шаблон позначений `unverified`.
- **O-5. Коли реліз 0.2.9 потрапить у `main`.** Тригер: `git fetch` перед SESSION-001. Типово: D-020.
- **O-6. Бюджет ходів моделі на canary і на поведінкове порівняння D-19.** Рішення власника. Типово: 0, що означає canary-статуси `configured-not-verified`, G2 не пройдено, порівняння `DEFERRED`.

## Least-risk defaults

- Назви файлів і каталогів: за конвенцією відповідного каталогу репозиторію. Нова мова документів пакета це українська з англійськими термінами; код, коментарі, commit-повідомлення англійською.
- Непередбачена дрібна неоднозначність у схемі інструмента: найменша зворотна зміна, найвужчі типи, `additionalProperties: false`.
- Невідомий стан зовнішнього сервісу чи клієнта: вважати недоступним і записати `configured-not-verified` або `unknown`, не вигадувати.
- Невідомий формат конфігурації клієнта: шаблон `unverified` без команди провайдера.
- Бракує дозволу на витрату або зовнішній виклик: не виконувати, записати `NOT RUN` і причину.
- Розмір відповіді невизначений: обрати меншу межу й додати `truncated`.
- Нова залежність потрібна не для extra: не додавати.
- Команди в артефактах цього пакета: звичайні `python ...` без обгорток маршрутизації виводу; точні стани (git, SHA, JSON) читати без фільтрації.
- Конфлікт між цим пакетом і ratified рішенням реєстру: пріоритет за реєстром, зупинка лише якщо потрібна окрема пропозиція заміни.

## Execution facts: SESSION-001

SDK pin for D-013: `mcp==2.1.1` (tested lower bound `>=2.1.1,<3`).
A clean Python 3.11.15 environment resolves the base package and SDK together;
Python 3.12 is not installed on this machine. The source branch still contains
`origin/main` at `dda7b0c`; release 0.2.9 has not landed.
B0 is remeasured with UTF-8 output and temporary instance roots replaced by `.`.
Compared with the planning measurement, light differs by -78/-72/-73/-73 bytes
for Claude Code/Codex/Cursor/Hermes respectively; the policy walks are unchanged.
These are normalization differences, not token savings. SDK probe and test
commands are recorded in the session closeout.

License-contour sequencing adjustment: the exact standard Python Software
Foundation Trove classifier is normalized to the already allowed `PSF-2.0`.
The Windows dependency metadata uses `PSF`; bare `PSF` remains unknown, denied
licenses still win, and `license-policy.json` is unchanged. This compatibility
fix was pulled forward from SESSION-004 so dependency viability can be checked
before implementation. Reproduction before the fix: clean Windows environment
license check reported only pywin32 as UNKNOWN. Regression tests cover the exact
classifier, bare alias, denied precedence and a policy without PSF-2.0.
Probe: both in-memory and stdio roundtrips PASS; tools/list 212 bytes for one
probe tool. `Context.elicit` is present; no host elicitation was attempted.

## D-021: Bounded doctor coverage for a reader

**Status: provisional, implementation clarification of D-005 and D-012.**
The MCP doctor uses the same structured core checks, omitting active source
resolution, ancestor size budgets, skill discovery and optional provider probes.
Those operations can inspect outside the selected instance or execute provider
commands; the reader contract forbids both. The response is `partial`, names
the skipped checks, and recommends direct CLI verification for full coverage.
Marker checks also read the fixed adapter entrypoint, `.gitignore` and
`.gitattributes` inside the selected instance; these are the minimum additional
local sources needed by the existing doctor. CLI behavior is unchanged.

Execution-record validation is a local required-fields check, not EIF instance
validation: the framework source is intentionally not initialized as a project.
