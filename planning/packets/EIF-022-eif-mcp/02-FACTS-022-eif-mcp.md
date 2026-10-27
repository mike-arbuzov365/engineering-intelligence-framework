---
packet: EIF-022-eif-mcp
type: facts
status: verified-for-planning
created: 2026-10-26
evidence_cutoff: 2026-10-26
---

# Факти: eif-mcp

## Межа доказів

Перевірено 2026-10-26 у worktree від свіжого `origin/main` (`dda7b0c`, `pyproject.toml` версії 0.2.8) після `git fetch --all --prune`:

- код `src/engineering_intelligence_framework/` (`cli.py`, `commands/*.py`, `workspace_contract.py`) і `scripts/eif_*.py`, які синхронізуються в `_impl/`;
- шаблони `templates/packet-*.md`, `templates/session-launch.md`, playbooks і skills пакетів;
- `adapters/README.md`, `adapters/parity-matrix.json`, `docs/benchmarks/README.md`, `core/policies/decisions.md`;
- синтетичні інстанси, створені `eifctl new` з чотирма адаптерами в тимчасовому каталозі (приватні інстанси не використовувались);
- довідка MCP Python SDK через Context7 та версія, встановлена на машині вимірювання (`mcp 2.1.1`);
- вебпошук щодо підтримки elicitation клієнтами (лише вторинні джерела, помічені нижче);
- незлитий worktree релізу 0.2.9 прочитано лише на читання, як сигнал про рішення, що скоро з'являться в `main`. Він не є authority.

Усе, що датоване до цієї дати і не перевірене повторно, вважати потенційно застарілим. Мітки: `OBSERVED` перевірено напряму, `INFERRED` висновок із перевіреного, `ASSUMED` не перевірено, названо, чого бракує.

## Experience retrieval (preflight планування)

`OBSERVED` У репозиторії фреймворку немає каталогу `knowledge/`: `scripts/eif_search_knowledge.py` відповідає "not a directory", отже індексувати нічого. Пошук за "mcp", "token", "session continuity", "adapter" в окремому приватному інстансі власника (лише читання) повернув один запис про реєстр зовнішніх skills, нерелевантний до дизайну. Пошук тексту по репозиторію знайшов згадки MCP лише в контексті vendor-docs (розділ 7). Попередніх уроків про MCP-адаптери для методології немає. Приватні подробиці з інстанса власника в пакет не переносились.

## 1. Вхідні обмеження від власника

`OBSERVED` (вхідне доручення пакета). Власник прийняв рішення про форму eif-mcp: Python-адаптер у репозиторії фреймворку як `eifctl mcp serve`, один процес на один явно вибраний EIF-інстанс (корінь через змінну середовища або аргумент), тонкий адаптер над функціями `eifctl`. Фаза 1 лише читання: стислий brief за профілем і типом задачі, пошук knowledge, статус пакета й наступна сесія, doctor/verify, session validate/resume-audit, delivery check. Фаза 2 керовані записи з точним попереднім переглядом і схваленням від host: session checkpoint, запис evidence, render knowledge-delta і closeout. Без self-approval і без generic execute. Реалізацію оркеструє окремий чат після схвалення пакета.

Власник також має набір правил проєктування для своїх MCP-серверів. Пакет відтворює їх як власні рішення (ідентичність і процес, класи ефекту, brief за замовчуванням, словник статусів, типізовані помилки, receipt для записів, виміряний `tools/list`, тестування через справжній SDK і справжній клієнт). Приватні сервери власника в пакеті не називаються і не є джерелом чисел.

## 2. Базова лінія токенів (вимір)

Скрипт: [evidence/measure_baseline.py](evidence/measure_baseline.py). Результат: [evidence/baseline-2026-10-26.json](evidence/baseline-2026-10-26.json).

Відтворення (з кореня worktree, `PYTHONPATH` вказує на `src/`, а `--eifctl` на запуск CLI з вихідного дерева):

```text
python planning/packets/EIF-022-eif-mcp/evidence/measure_baseline.py \
  --eifctl "python -W ignore -m engineering_intelligence_framework.cli" \
  --source-ref "<ref>" --out baseline.json
```

Метод `OBSERVED`:

1. Для кожного з адаптерів `claude-code`, `codex`, `cursor`, `hermes` скрипт виконує `eifctl new` у тимчасовому каталозі (проєкт `synthetic-demo`, мова `en`).
2. Рівень A (завантажує хост без рішення агента): entrypoint адаптера плюс frontmatter 12 skill-loaders (`name` і `description`).
3. Рівень B (entrypoint велить агенту прочитати або виконати на першій задачі): stdout одного `eifctl doctor`; "прохід по skill" це runtime-джерело SKILL.md плюс один крок відносних `.md`-посилань з нього (глибші читання не враховані).
4. Токени це оцінка `ceil(bytes / 4)`. Це не вимір токенайзера. Реальні токени дає лише `/context` у хості або `count_tokens`, а це зовнішній виклик поза нульовим бюджетом. Похибка оцінки невідома і для кирилиці вища, тому числа порівнюються між собою, а не з білінгом.
5. Байти детерміновані. Латентність залежить від машини, тому в порівняннях не використовується.

Результат за адаптерами (байти; сценарій `light` = entrypoint + frontmatter skills + один doctor):

| Адаптер | Entrypoint | Frontmatter skills | Doctor | light | knowledge_search | packet_plan | packet_run |
|---|---|---|---|---|---|---|---|
| claude-code | 6 704 | 3 735 | 1 570 | 12 009 | 16 396 | 27 173 | 27 959 |
| codex | 6 704 | 3 735 | 1 558 | 11 997 | 16 384 | 27 161 | 27 947 |
| cursor | 6 953 | 3 735 | 1 606 | 12 294 | 16 681 | 27 458 | 28 244 |
| hermes | 6 705 | 3 735 | 1 562 | 12 002 | 16 389 | 27 166 | 27 952 |

Для Claude Code це ≈ 3 003 токени (`light`) і ≈ 6 990 (`packet_run`) за оцінкою. Складові "проходу по skill": `run-execution-packet` 15 950 байт (SKILL.md і три playbooks), `plan-execution-packet` 15 164, `knowledge-search` 4 387.

Додаткові `OBSERVED`:

- Якщо хост завантажує loaders цілком, а не лише frontmatter, `light` для Claude Code зростає до 19 080 байт. Який із двох випадків діє, перевірено лише для Claude Code (його README фіксує спостережене виявлення skills). Для інших трьох `ASSUMED`.
- Entrypoint для `uk`-інстанса має той самий розмір (6 704), бо блок інваріантний до мови (парність-матриця: "governance block content is English-invariant").
- Runtime-пакет інстанса: 155 файлів, 887 081 байт (усе, що можна прочитати, не те, що читається за замовчуванням).
- Латентність (залежить від машини): холодний підпроцес `eifctl version` ≈ 0,8-1,5 с, `eifctl doctor` ≈ 1,1-2,2 с у двох прогонах, при цьому лише `import engineering_intelligence_framework.cli` коштує ≈ 1,0-1,4 с. Висновок: імпорт переважає, тож довгоживучий процес, який імпортує один раз, не платить цю ціну за кожен виклик.

`INFERRED` (арифметика над виміряним B0 для Claude Code і бюджетами з [D-006](03-DECISIONS-022-eif-mcp.md) та [D-014](03-DECISIONS-022-eif-mcp.md), найгірший випадок: хост завантажує `tools/list` цілком): "після" для `light` = компактний блок 2 400 + frontmatter skills 3 735 + `tools/list` 6 144 + brief 1 536 (замість doctor) = 13 815 байт проти 12 009, тобто приблизно +15 %. Для `packet_run` те саме плюс дві секційні читання по 4 000 = 21 815 проти 27 959, приблизно -22 %. Для `packet_plan` 21 815 проти 27 173, приблизно -20 %. Висновок: на легких задачах MCP за бюджетами може коштувати дорожче, а виграш можливий у сценаріях `packet_*`, де секційне читання замінює проходи по 15-16 KB. Це гіпотеза для воріт G1c, а не результат, бо бюджети це рішення, а не виміри. У поточному середовищі Claude Code схеми інструментів відкладені (у системному промпті видно лише імена), тож реальна вартість `tools/list` залежить від хоста (Open O-3).

## 3. Що з операцій EIF детерміновано і як викликається

`OBSERVED` (читання коду). Усе нижче працює без моделі.

| Операція | Де реалізована | Публічна функція зі структурою? | Вивід CLI |
|---|---|---|---|
| doctor / verify | `commands/doctor.run` обгортає `_impl/eif_verify_runtime.main` і додає перевірку відповідності встановленого пакета до lock та `verify_workspace_materialization` | Частково. Окремі `check_*` публічні, але звіт `Report` збирається і друкується всередині `main` | текст (`ok`/`FAIL`, 15 перевірок) |
| knowledge search | `_impl/eif_search_knowledge.search(...)` | Так, повертає dict (matched, skipped_by_status, malformed, schema_invalid) | текст або `--json` |
| session validate | `commands/session._validate_checkpoint(path, project_root=)` | Приватна, повертає `(data, errors)` | текст `PASS`/`FAIL` |
| session resume-audit | `commands/session._audit_checkpoint(path, project_root)` | Приватна, повертає `(data, mismatches)` | текст |
| session checkpoint | `commands/session._checkpoint(args)` | Ні, приймає argparse Namespace, пише файл атомарно, друкує | текст |
| session handoff | `commands/session._handoff` | Ні | текст `key=value` |
| delivery check | `commands/delivery.check_delivery(project, action=, scope=, at=)` | Так, повертає approval dict або кидає `DeliveryGuardError` | текст з `enforcement=machine` |
| render | `_impl/eif_render.main` | Ні, лише `main(argv)`. Має `--stdout` (перегляд), `--out`, `--force`, `--draft`, `--set` | файл або stdout |
| projects resolve | `commands/projects.resolve_project` | Так | текст |
| packet status | немає | немає | немає |
| brief, capabilities | немає | немає | немає |
| іменований доступ до policy-артефакту з секцією | немає (агент читає файл цілком) | немає | немає |

`OBSERVED` наслідок: "тонкий адаптер без другої реалізації" вимагає спершу витягти структуровані функції та додати три відсутні (packet status, brief, artifact get), а не обгортати текстовий вивід. Звідси [D-004](03-DECISIONS-022-eif-mcp.md).

`OBSERVED` приклад ризику текстового парсингу: `eifctl doctor` друкує абсолютний шлях інстанса в останньому рядку, а `session handoff --open` повертає `FAIL` із кодом 1 за задумом. Структурований шар має повертати відносні шляхи й коди.

## 4. Звідки сервер бере код і policy

`OBSERVED`:

1. Pinned-пакет інстанса `.eif/runtime/` містить 14 скриптів `eif_*.py` (список `BUNDLE_SCRIPTS` в `scripts/eif_init.py`), схеми, playbooks, skills, templates, docs, locales, integrations. У ньому немає модулів `session`, `delivery`, `projects`, `workspace`, `skills`, ні `workspace_materialization`. Ці модулі є лише в установленому пакеті.
2. Згенерований entrypoint вже комбінує обидва: `eifctl doctor --instance-path .` (установлений пакет) і `python .eif/runtime/eif_*.py` (pinned-скрипти). Він також велить читати policy лише з `.eif/runtime` та `.eif/workspace-runtime`, "ніколи наживо" з checkout.
3. `eifctl doctor` уже порівнює версію установленого пакета і digest ресурсів із `framework.lock.yaml` (`_check_installed_package_consistency`) і проситься переінсталювати, а не підганяти lock.
4. Рішення D-23 у незлитій гілці релізу 0.2.9 (статус там `ratified`, але у `main` його ще немає): машинний runtime це локальна версійна інсталяція; "doctor PASS ніколи не досягається перегенерацією lock під випадково встановлений пакет". Для eif-mcp це означає: сервер ніколи не лагодить drift, лише повідомляє.
5. `ASSUMED` Для інстансів із `source_type`, відмінним від `installed-package` (git-джерело), перевірки відповідності версії в `doctor` немає. Сервер має повідомляти `unknown`, а не `ok`.

`INFERRED`: єдине джерело, що покриває всі операції фаз 1 і 2, це установлений `eifctl`. Pinned-пакет лишається джерелом policy-тексту. Підпроцес на кожен виклик коштує ≈ 1 с імпорту, а in-process виклик після одного імпорту ні.

## 5. Пакування та залежності

`OBSERVED`:

1. База залежить лише від `PyYAML==6.0.2` і `jsonschema[format-nongpl]==4.23.0`. Python `>=3.11`.
2. На машині вимірювання встановлено `mcp 2.1.1`. У v2 `FastMCP` перейменовано на `MCPServer` (`from mcp.server import MCPServer`), шлях `mcp.server.fastmcp` видалено, а не позначено застарілим. Довідник скіла `mcp-builder` написаний під v1 (`FastMCP`), тож приклади потребують перекладу.
3. `mcp 2.1.1` вимагає 14 прямих пакетів (13 поза Windows): anyio, httpx2, jsonschema (`>=4.20.0`, сумісно з піном EIF), mcp-types, opentelemetry-api, pydantic (`>=2.12`), pyjwt[crypto], python-multipart, pywin32 (лише Windows), sse-starlette, starlette, typing-extensions, typing-inspection, uvicorn. Це на порядок більше за базу, тож `mcp` має бути optional extra.
4. У v2 `stdio_server` на час роботи перенаправляє fd 0 на null, а fd 1 на stderr, тож випадковий `print` в обробнику не псує протокол. У v1 це не так. Покладатись на цю властивість не можна (версія може змінитись), тому обробники не друкують у stdout.
5. SDK v2 дає `Client(server)` для in-memory тестів, але це не заміна тесту справжнього транспорту.
6. Ліцензійний контур: `scripts/eif_check_licenses.py` читає `sbom.cdx.json` і `scripts/requirements.txt`, а `THIRD_PARTY_NOTICES.md` перелічує базове замикання. Залежності extra не входять у цей SBOM. Потрібен окремий документований контур, інакше license check або SBOM-freshness стануть червоними чи неповними.
7. Рутинний hosted CI це один job із `scripts/tests/smoke.py` (D-14). Повний набір (`run_all.py`) і матриця пакетів працюють локально або з `release-check.yml` вручну. Тести з `mcp` не мають залежати від установлення `mcp` у smoke.

## 6. Клієнти та їхні можливості

| Адаптер | Конфіг MCP (з `integrations/vendor-docs/README.md`) | Elicitation |
|---|---|---|
| Claude Code | `~/.claude.json`, ключ `mcpServers` | `INFERRED` (вторинні джерела): підтримка з версії 2.1.76, березень 2026. Встановлена версія на дату EIF-021 була 2.1.169. Не перевірено офіційним changelog. |
| Codex | `~/.codex/config.toml`, ключ `mcp_servers` | `INFERRED` (вторинні джерела): окрема політика схвалення для elicitation, вимкнена або автоматично відхиляється залежно від налаштувань. Одне джерело стверджує, що власні сервери не оголошують можливість. Потребує canary. |
| Cursor | `~/.cursor/mcp.json`, ключ `mcpServers` | `INFERRED` (форум Cursor): працює частково. Є звіти про зависання без UI на Windows (3.10.20) і про відсутність рендеру у вікні Agents на macOS. Сервер мусить мати таймаут. |
| Hermes | `~/.hermes/config.json`, ключ `mcpServers` | `ASSUMED`: невідомо. Формат конфігу теж не перевірений (шаблон у репозиторії не стверджує команди провайдера). |

`OBSERVED`: репозиторій має прецедент "EIF не встановлює MCP і не змінює user-level конфіг": згенеровані артефакти `integrations/vendor-docs/generated/mcp/` мають `installed: false` і `user_config_mutated_by_generator: false`. eif-mcp повторює цю межу.

`OBSERVED`: Cursor не має механізму hook'ів для tool-call, Codex і Hermes мають block-only hook-контракти, а Claude Code hook'и це локальний стан машини (parity-matrix, `adapters/README.md`). Тому enforcement через hook не заявляється, а схвалення фази 2 не спирається на hook'и.

## 7. Методологічні факти, що торкаються рішень

`OBSERVED`:

1. Тексти "EIF сам не говорить MCP" є в `integrations/vendor-docs/README.md`, `integrations/vendor-docs/manifest.json` (поле `verification_gap`), `integrations/README.md`, `docs/architecture/HOW-EIF-WORKS.md` (розділ про vendor-docs), `CHANGELOG.md`. Вони описують пробу сторонньої MCP-інтеграції, що лишається правдою, але після появи `eifctl mcp serve` фраза без уточнення вводить в оману. Потрібне точкове уточнення.
2. Правило D-10 (опційність Graphify) діє: ядро EIF, bootstrap, адаптери і doctor не залежать від необов'язкових інтеграцій. eif-mcp має бути такою ж опційною.
3. Прогрес пакета не є машиночитним. Файли запуску сесій попередніх пакетів зберігають `status: prepared` (EIF-020) або `prepared-awaiting-owner-approval` (EIF-021) і після виконання. Завершення фіксує лише `07-CLOSEOUT` (`complete-local`, `completed-local`), а `.session-context/` ефемерний і видаляється під час closeout. Отже "наступна сесія" не виводиться з наявних даних без нової конвенції ([D-008](03-DECISIONS-022-eif-mcp.md)).
4. Правило делегування: playbook `execution-packet-execution.md` Step 4 у цій версії вже дозволяє обмежене делегування в межах сесії (п'ять умов; розширене правило воркспейса має шість і сумісне). Перелік записів, які пише лише активний агент: checkpoint, closeout, evidence, Knowledge Delta.
5. MCP-клієнт не повідомляє серверу, хто викликає: активний агент чи субагент. Отже межу "делегат не пише checkpoint" сервер не здатен забезпечити, лише `instruction_only` ([D-011](03-DECISIONS-022-eif-mcp.md)).
6. `eifctl session checkpoint` вже дозволяє агенту самому задати `--approval-state approved` та текст доказу. Поле фіксує твердження, а не доводить схвалення. Self-approval у фазі 2 стосується застосування запису, а не змісту цього поля.
7. D-19: твердження про користь інструкції потребує зіставного порівняння за фіксованих моделі, налаштувань, входу, оцінювача і бюджету. D-12: число економії токенів не публікується без відтворюваного benchmark і результату якості. Один прогін це лише доказ існування.
8. Реєстр рішень у `main` закінчується на D-21 (provisional). У незлитому релізі 0.2.9 додано D-22 (RTK виходить з активної поверхні EIF) і D-23. Нові framework-рішення цього пакета мають брати перший вільний номер на момент merge.
9. Якщо D-22 потрапить у `main`, `doctor` перестане друкувати рядок про `shell_output_compression`, тож базова лінія зміниться. Тому B0 перевимірюється першим кроком SESSION-001.

## 8. Прогалини

Що потрібно для мети і чого ще немає:

1. Відтворюваний вимір у `scripts/` із тестом і бюджети (сьогодні скрипт лише в `evidence/`).
2. Структуровані функції для doctor, session validate/audit/checkpoint, render preview/apply. Нові функції: статус пакета, brief, capabilities, доступ до артефакту.
3. Конвенція прогресу сесій у файлах запуску.
4. Сервер, extra, межі, помилки, статуси, логування, дедлайни.
5. Протокол схвалення фази 2, сховище prepared-subject у пам'яті, receipts, ідемпотентність.
6. Харнес зі справжнім SDK, тест wheel, ліцензійний контур extra.
7. Шаблони конфігурації та документація, canary з реальних клієнтів, статуси.
8. Компактний варіант блока entrypoint і виміряне "після".
9. Eval-питання `mcp-builder`.

## Ledger перенесених рішень і елементів

| Попередній пункт | Розміщення |
|---|---|
| Вхідне рішення власника про форму eif-mcp | Прийнято як вхід, уточнено в D-001..D-005, D-009; три розриви названо в [00-README](00-README.md) |
| EIF-021 B-01 автоматичне створення чатів | Re-deferred. eif-mcp його не торкається |
| EIF-021 B-02, B-03 compaction і розширений lifecycle session | Re-deferred |
| EIF-021 B-04 глобальний вибір проєкту | Re-deferred. Суперечить "один корінь на процес" (D-001, D-012) |
| EIF-021 B-05 policy engine для guarded actions | Re-deferred. Протокол D-010 це схвалення запису, а не загальний policy engine |
| EIF-021 B-10 структурний валідатор пакетів | Re-deferred. `eif_packet_status` лише читає прогрес |
| EIF-021 B-17 розширений quality-per-token benchmark | Частково in-scope: статичний footprint (S1, S5, S7, S8). Поведінкове порівняння D-19 DEFERRED без бюджету |
| EIF-021 B-18 набір canary адаптерів | Звужено: лише canary клієнтів для eif-mcp (S5). Повний набір re-deferred |
| EIF-021 B-19 підтримка вибору маршруту задачі | Re-deferred. `task_kind` задає агент явно, класифікатора немає |
| EIF-021 B-20 sandbox для виконуваних skills | Не стосується. eif-mcp виконує лише власний код |
| Практика "прогрес у `status` файлу запуску не оновлюється" | In-scope (S2), D-008 |
| Тексти "EIF не говорить MCP" | In-scope: уточнення в S4 і S8 |
| D-22 і D-23 релізу 0.2.9 (незлиті) | Не залежність. Враховано в D-003 (D-23) і в правилі перевимірювання (D-017). Rebase перед S1 |
| Публікація на PyPI, release, tag | Owner-only, поза пакетом |
| Рішення про бюджет на поведінкове порівняння і canary-ходи моделей | Open O-6 з типовою відповіддю 0 |

## Припущення для перевірки під час виконання

- `ASSUMED` Чисте віртуальне середовище розв'язує `engineering-intelligence-framework[mcp]` без конфліктів на Windows і Linux, Python 3.11 і 3.12 (S1 перевіряє, S4 доводить на wheel).
- `ASSUMED` API `MCPServer` у v2 підтримує явні `ToolAnnotations`, `structured_output` і elicitation з сервера у версії, закріпленій у S1. Якщо ні, S1 фіксує відхилення і D-013 уточнюється новим записом.
- `ASSUMED` Хост бачить `structuredContent` і `content`. Який саме з них клієнт показує моделі, різниться. Тому відповідь дублює компактний JSON у текстовому полі.
- `ASSUMED` Elicitation працює принаймні в одного з чотирьох клієнтів на встановленій версії. Це умова воріт G2 (Open O-1).
