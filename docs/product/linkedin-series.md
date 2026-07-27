---
type: reference
status: active
scope: framework
created: 2026-07-27
review_after: 2026-10-27
---

# LinkedIn series

Ten posts about EIF, in English and Ukrainian, planned as one arc rather
than ten announcements.

This file sits next to [`claims-evidence.md`](claims-evidence.md) on
purpose. A post is a public claim. Every claim in this series has to survive
the same register that governs the website, including its forbidden wording
list. If a draft here needs a sentence the register does not allow, the
sentence is wrong, not the register.

## What the series is for

Not reach. The framework has one maintainer and no support capacity, so a
thousand curious readers is worse than twenty who try it on a real
repository and say what broke.

The series succeeds if an engineer who runs coding agents daily reads one
post, recognizes a failure they have had, and understands the specific
mechanism that addresses it well enough to argue with it. That is the whole
goal. Every editing decision below follows from it.

## Audience

Primary: senior and staff engineers, tech leads and hands-on engineering
managers who already use coding agents on a real codebase and have hit the
memory problem. They do not need convincing that agents are useful. They
need a name for what keeps going wrong.

Secondary: the Ukrainian engineering community. Ukrainian is not a
translation courtesy here, it is the reason the locale layer exists and one
of the few parts of this project a reader can verify in two minutes.

Not the audience: buyers, executives looking for a platform, and anyone who
wants a tool that removes engineering judgment. The posts should read as
uninteresting to them, and that is fine.

## What the series claims, and what it never claims

Claims, all backed:

- Chat history is not engineering memory, and the failure modes are
  specific and nameable.
- EIF separates methodology, durable project knowledge and session context
  into three layers, with an explicit decision governing promotion between
  them.
- Retrieval happens before implementation.
- Execution is bounded: scope, evidence, stop conditions, closeout.
- Optional integrations stay optional, with named fallback paths.
- The project states what it has verified and inside what bounds.

Never, in any language:

- That it is production-ready, proven at scale, or an official release.
- That it improves quality, reduces rework, produces fewer bugs, or saves
  developer hours. None of that is measured.
- Any comparison of governed against ungoverned work. No such study exists.
- Any token reduction percentage.
- Any claim that a tool is needed for EIF to work.
- Any duration claim about a human. Nothing has been timed against a
  person.

The full list of banned strings is in
[`site/src/content/claims.json`](../../site/src/content/claims.json), and
the site build enforces it. Run a draft past that list before posting.

## Voice

The single rule: write the way you would write a message to one engineer
you respect, who is busy and has seen a lot of frameworks.

Everything below is a consequence of that rule.

**Never use, in either language:**

- Long dashes of any kind. Comma, colon, full stop, or rewrite the
  sentence.
- Emoji. Not as bullets, not as decoration, not one at the end.
- A rhetorical question as the opening line.
- One-sentence paragraphs stacked for rhythm. That layout is the single
  clearest tell that a post was optimized rather than written.
- "Here's the thing", "Let that sink in", "The result?", "Spoiler",
  "Plot twist", "Game changer", "unlock", "leverage", "supercharge",
  "10x", "revolutionize", "in a world where".
- Ukrainian equivalents: «А тепер найцікавіше», «І ось що я зрозумів»,
  «Результат?», «Це змінює все», «проривний», «революційний»,
  «наразі» (use «зараз»), «даний» (use «цей»), «у якості» (use «як»),
  «здійснювати» plus a noun where one verb exists.
- Numbers that are not measured. If a figure appears, it must be traceable
  to a file in the repository.
- A closing plea for engagement. No "what do you think", no "drop a
  comment", no "let me know below".
- Hashtags on more than the first and last post, and never more than three.

**Do use:**

- A concrete first line that states something, so the preview earns the
  click on its own.
- Paragraphs of two to four lines, blank line between.
- The specific mechanism rather than the adjective. "Promotion is a
  decision someone makes" beats "intelligent knowledge management".
- The bound, stated by you, before anyone else finds it. On LinkedIn this
  is the differentiator, not a weakness.
- One link, at the end, and only where there is something to read.

## Format and cadence

- Two posts a week, Tuesday and Thursday, roughly 09:00 Kyiv time. Five
  weeks for the arc.
- 900 to 1600 characters. Long enough to say the mechanism, short enough
  that nobody has to press "see more" twice.
- LinkedIn does not render code blocks or markdown. Any command goes on its
  own line as plain text, at most two lines, and only where it is the
  point.
- No images for the first three posts. From post four onward, one figure
  from the site per post is allowed where the figure genuinely explains
  something, exported as a plain PNG.

## Bilingual policy

Two separate posts, not one post with both languages stacked. Stacked
bilingual posts halve the readable length of each and read as neither.

- English post on the main feed.
- Ukrainian version as a separate post the following day, or on a Ukrainian
  professional community where one fits.
- The Ukrainian is written, not translated. Same facts, same order, same
  bounds. Where a literal rendering would sound like machine output, the
  sentence gets rebuilt.

## The arc

| # | Working title | The one thing a reader should take away |
|---|---|---|
| 1 | Chat history is not engineering memory | The problem has specific, nameable failure modes, and there is now a public repository |
| 2 | Three layers, and a rule for each | What is allowed to survive a session, and what should evaporate |
| 3 | Retrieval before implementation | Storing knowledge is the easy half |
| 4 | One session cannot promote its own lesson | Why learning runs as two loops, not one |
| 5 | A merged PR is not evidence | Bounded execution: scope, stop conditions, closeout |
| 6 | Ranking your sources in one list is the bug | Authority is multi-axis |
| 7 | What governance costs | The honest token accounting, with the balance left open |
| 8 | The tools are optional, and that is a design constraint | Named fallback paths, and the one call that leaves the machine |
| 9 | I made it hard for my own site to overclaim | The claims register and the build gate |
| 10 | The language is configuration, not a default | The locale layer, and what it does not cover |

---

## Post 1. Chat history is not engineering memory

### EN

Most coding agents start every session as a stranger to the codebase they
worked on yesterday.

The session that made a decision is gone. The reasoning behind it was
compacted away halfway through. The next session re-reads the same files,
re-derives the same conclusion, and sometimes confidently tries the approach
that was already rejected, because nothing recorded that it was rejected.

I have been running a methodology against this daily since May, in a private
repository. It is now extracted into a public one.

Engineering Intelligence Framework is a control plane, not another chat
memory store. It separates three things that agent workflows usually
collapse into one: reusable methodology, durable project knowledge, and
ephemeral session context. Knowledge is pulled into a session before
implementation rather than searched for after it. What a session learned
becomes project knowledge only through an explicit decision.

Apache-2.0. Ontology, JSON schemas, a CLI with seven subcommands, thirteen
playbooks, and one reproducible vertical slice you can run from a clone.

It also states what it has not verified. There is a claims register listing
every public claim, its evidence and its bound, and the site build fails if
the page says something the register does not allow.

[link]

### UA

Більшість агентів для коду починає кожну сесію так, ніби вчора не бачила
цього репозиторію.

Сесія, яка ухвалила рішення, зникла. Міркування, що привели до нього,
стиснулися десь на середині. Наступна сесія перечитує ті самі файли,
доходить того самого висновку, а іноді впевнено пробує підхід, який уже
відхилили, бо ніде не записано, що його відхилили.

Я щодня працюю за цією методологією з травня, у приватному репозиторії.
Тепер вона винесена в публічний.

Engineering Intelligence Framework працює як керуючий рівень, а не як ще
одне сховище чат-пам'яті. Він розділяє три речі, які в агентних процесах
зазвичай злипаються в одну: методологію, придатну до повторного
використання, стійке знання про проєкт і тимчасовий контекст сесії. Знання
підтягується в сесію перед реалізацією, а не шукається після неї. Те, чого
сесія навчилася, стає знанням проєкту лише через явне рішення.

Ліцензія Apache-2.0. Онтологія, JSON-схеми, CLI із сімома підкомандами,
тринадцять плейбуків і один відтворюваний вертикальний зріз, який
запускається з клону.

Він так само прямо каже, чого не перевірено. Є реєстр тверджень, де в
кожного публічного твердження вказано доказ і межу, а збірка сайту падає,
якщо сторінка стверджує те, чого реєстр не дозволяє.

[посилання]

---

## Post 2. Three layers, and a rule for each

### EN

The most useful thing I did for agent work was decide what is allowed to
survive a session.

Three layers, and a rule for each.

Framework: the methodology itself. Playbooks, ontology, quality gates.
Reusable across projects, changes rarely, and never because one session had
a bad day.

Project: durable knowledge about this repository. Decisions, constraints,
facts, risks. Each one carries a status and an evidence label saying whether
it was observed, inferred or assumed. This is the layer an agent reads
before it starts.

Session: everything else. The reasoning, the dead ends, the file listings,
the twelve commands that produced one answer. Most of it should evaporate,
and it does.

The failure I kept hitting before this was the middle layer having no
boundary. Everything a session concluded felt like project knowledge at the
moment it was concluded. Six sessions later the project memory was a pile of
half-true observations with no way to tell which ones had ever been checked.

So a session now ends with a Knowledge Delta: what it learned, what should
be promoted, what should stay where it is, and what turned out to be wrong.
Promotion is a decision someone makes. It is not a side effect of finishing
the work.

### UA

Найкорисніше, що я зробив для роботи з агентами, це вирішив, чому взагалі
дозволено пережити сесію.

Три рівні, і для кожного своє правило.

Фреймворк: сама методологія. Плейбуки, онтологія, гейти якості. Придатна до
повторного використання в різних проєктах, змінюється рідко й ніколи не
через те, що в однієї сесії був невдалий день.

Проєкт: стійке знання про цей репозиторій. Рішення, обмеження, факти,
ризики. У кожного свій статус і позначка доказовості: спостережено, виведено
чи припущено. Саме цей рівень агент читає перед початком роботи.

Сесія: усе інше. Міркування, глухі кути, лістинги файлів, дванадцять команд,
які дали одну відповідь. Більша частина цього має випаруватися, і вона
випаровується.

До цього я постійно натикався на те, що середній рівень не мав межі. Усе, до
чого доходила сесія, у мить висновку відчувалося як знання проєкту. Через
шість сесій пам'ять проєкту перетворювалася на купу напівправдивих
спостережень, де вже не розібрати, які з них хтось перевіряв.

Тому сесія тепер закривається Knowledge Delta: чого вона навчилася, що варто
підняти на рівень вище, що лишається на місці, а що виявилося хибним.
Підняття це рішення, яке хтось ухвалює. Не побічний ефект завершеної роботи.

---

## Post 3. Retrieval before implementation

### EN

Storing knowledge is the easy half. The half that decides whether storing it
was worth anything is whether something reads it before the work starts.

Almost every agent memory setup I have seen gets this backwards. Knowledge
goes in at the end of a session, and comes out only when someone thinks to
ask for it. Which is exactly when they already know the answer, because they
just spent forty minutes re-deriving it.

In EIF, retrieval is a step in the workflow, not an available feature. Before
a session scopes any implementation, it searches the project knowledge base
for what has already been decided, tried, or rejected near this task, and
pulls it into context.

The search is offline keyword search over the knowledge index. No embeddings,
no vector store. That is a deliberate limit, not an oversight: I would rather
have retrieval that returns nothing and says so than retrieval that returns
something plausible and cannot tell me why.

It reports three different failures separately, and never as "no results":
a file that would not parse, a file that parses but violates the ontology,
and a file whose status makes it ineligible, because a rejected decision
should not surface as guidance.

What this is not: tested at scale. It works on the knowledge bases I have,
which are the size one engineer produces. That bound is in the repository.

### UA

Зберегти знання це проста половина. Половина, від якої залежить, чи було
взагалі варто зберігати, це чи прочитає його щось перед початком роботи.

Майже кожна схема агентної пам'яті, яку я бачив, робить це навпаки. Знання
потрапляє туди наприкінці сесії, а виходить тоді, коли хтось здогадається
його попросити. Тобто саме тоді, коли відповідь уже відома, бо людина щойно
витратила сорок хвилин, щоб дійти до неї вдруге.

В EIF пошук досвіду це крок процесу, а не доступна можливість. Перш ніж
сесія візьме будь-яку реалізацію в роботу, вона шукає в базі знань проєкту
те, що вже вирішено, спробувано чи відхилено поруч із цим завданням, і
підтягує знайдене в контекст.

Пошук офлайновий, за ключовими словами, по індексу знань. Без ембедингів,
без векторної бази. Це свідоме обмеження, а не недогляд: краще пошук, який
нічого не повернув і прямо про це сказав, ніж пошук, який повернув щось
правдоподібне й не може пояснити чому.

Три різні збої він розрізняє й ніколи не видає за «нічого не знайдено»: файл,
який не розібрався; файл, який розібрався, але порушує онтологію; і файл,
чий статус робить його непридатним, бо відхилене рішення не має спливати як
порада.

Чого тут немає: перевірки на масштабі. Воно працює на тих базах знань, які є
в мене, а це розмір, який виробляє один інженер. Ця межа записана в
репозиторії.

---

## Post 4. One session cannot promote its own lesson

### EN

A session that just solved something is the worst possible judge of whether
what it learned generalizes.

It has one data point, and it is emotionally invested in that data point.
Every one of us has written a rule into a team wiki at 6pm on the strength of
a single afternoon.

So learning in EIF runs as two loops rather than one.

The inner loop is per session. It asks what this session learned and records
it, with its evidence label and its status. That is all it does. It cannot
change the methodology.

The outer loop is a retro across many sessions. It asks a different question:
what keeps happening. Not what happened once and felt significant, but what
has now shown up in a way that is hard to argue with.

Promotion into the framework layer is driven by the outer loop only. A single
session can record a lesson. It cannot ratify one.

This is slower, and it is meant to be. The thing I was trying to prevent is
a methodology that mutates every day in response to whatever the last task
happened to be, which is not learning. It is drift with good intentions.

### UA

Сесія, яка щойно щось розв'язала, найгірший з можливих суддів того, чи
узагальнюється її урок.

У неї одна точка даних, і вона в цю точку емоційно вкладена. Кожен із нас
дописував правило у вікі команди о шостій вечора на підставі одного вдалого
дня.

Тому навчання в EIF іде двома циклами, а не одним.

Внутрішній цикл працює в межах сесії. Він питає, чого ця сесія навчилася, і
записує це з позначкою доказовості та статусом. І все. Змінити методологію
він не може.

Зовнішній цикл це ретроспектива по багатьох сесіях. Він ставить інше питання:
що повторюється. Не що сталося одного разу й здалося важливим, а що вже
проявилося так, що заперечити важко.

Підняття на рівень фреймворку запускає лише зовнішній цикл. Одна сесія може
записати урок. Затвердити його вона не може.

Це повільніше, і так задумано. Я намагався не допустити методології, яка
щодня мутує під останнє завдання. Це не навчання. Це дрейф із добрими
намірами.

---

## Post 5. A merged pull request is not evidence

### EN

A merged PR proves that someone approved a diff. It does not prove the
behavior works, and treating the two as the same thing is how a codebase
accumulates features nobody has ever seen run.

Agent workflows make this worse, because the agent is fluent. It will
describe what it implemented in confident, correct-sounding prose, and that
description is not evidence either.

So execution in EIF is bounded before it starts. A unit of work declares its
scope, what observable success looks like, what will evaluate it, an
iteration budget, and a stop condition. Then it runs, and it closes out
against what it declared, not against how it went.

The demo in the repository is deliberately small, and the shape is the point:
seed real knowledge, retrieve it, make one change informed by that retrieval,
and verify it with a real test that fails before the change and passes after
it. Not a test written afterwards to match the code. One that was failing.

The bound worth stating: this is one synthetic demo project plus one real
private pilot. It is not a representative sample of engineering work, and I
have measured nothing about quality. What is verified is that the loop runs
end to end and that the closeout reflects what actually happened.

### UA

Змержений PR доводить, що хтось схвалив діф. Він не доводить, що поведінка
працює, і коли ці дві речі вважають однією, кодова база наповнюється
функціями, які ніхто ніколи не бачив у роботі.

З агентами це загострюється, бо агент красномовний. Він опише реалізоване
впевненою й правильною на вигляд прозою, і цей опис теж не доказ.

Тому виконання в EIF обмежене ще до старту. Одиниця роботи оголошує свою
область, вигляд спостережуваного успіху, чим це перевірятимуть, бюджет
ітерацій і умову зупинки. Далі вона виконується й закривається за тим, що
оголосила, а не за тим, як усе пішло.

Демо в репозиторії навмисно маленьке, і суть саме у формі: додати реальне
знання, знайти його, внести одну зміну на його основі й перевірити її
справжнім тестом, який до зміни падає, а після неї проходить. Не тестом,
дописаним постфактум під готовий код. Тим, який падав.

Межа, яку варто назвати: це один синтетичний демопроєкт плюс один реальний
приватний пілот. Це не репрезентативна вибірка інженерної роботи, і якості я
не вимірював. Перевірено те, що цикл проходить від початку до кінця, а
закриття відповідає тому, що справді сталося.

---

## Post 6. Ranking your sources in one list is the bug

### EN

Most source hierarchies I have written, and every one I have seen an agent
given, are a single ranked list. Official docs beat blog posts beat the
code beat guesswork. It looks obviously correct and it produces wrong
defaults constantly.

The reason is that "which source wins" is four different questions.

What should happen. What actually happens. Which instruction the agent is
required to follow right now. Whether an artifact is trustworthy enough to
cite at all.

Vendor documentation is usually the authority on the first. It is regularly
wrong about the second, because the installed version on this machine
behaves how it behaves regardless of what the docs say. An old internal
decision may still control execution while being empirically stale. A file
can be perfectly accurate and still not be citable, because its status says
it was superseded.

Collapse those into one ranking and you get an agent that quotes the manual
at a running process, or trusts a rejected decision because it came from a
high-ranked location.

EIF keeps them as four axes. A disagreement between them is recorded rather
than resolved by precedence, because the disagreement is usually the most
interesting thing on the page.

### UA

Більшість ієрархій джерел, які я писав, і кожна, яку я бачив у агента, це
один ранжований список. Офіційна документація важливіша за блог, блог
важливіший за код, код важливіший за здогад. Виглядає очевидно правильно й
постійно дає хибні дефолти.

Причина в тому, що «яке джерело перемагає» це чотири різні питання.

Як має бути. Як є насправді. Якій інструкції агент зобов'язаний коритися
просто зараз. І чи артефакт узагалі достатньо надійний, щоб на нього
посилатися.

Документація вендора зазвичай авторитет у першому питанні. У другому вона
регулярно помиляється, бо встановлена на цій машині версія поводиться так,
як поводиться, незалежно від написаного. Старе внутрішнє рішення може й далі
керувати виконанням, будучи емпірично застарілим. Файл може бути абсолютно
точним і при цьому непридатним для цитування, бо його статус каже, що його
замінили.

Злийте це в один рейтинг, і отримаєте агента, який цитує мануал живому
процесу або довіряє відхиленому рішенню, бо воно лежало у високорейтинговому
місці.

EIF тримає їх як чотири осі. Розбіжність між ними записують, а не знімають
старшинством, бо саме розбіжність зазвичай найцікавіше на сторінці.

---

## Post 7. What governance costs

### EN

Governance is not free in tokens, and I am not going to pretend otherwise
while asking anyone to adopt it.

Retrieval before the work costs context. Packet artifacts cost context. A
Knowledge Delta costs context. A real closeout, written against what was
declared rather than a summary of what happened, costs context. All of it
comes out of the same window an ungoverned agent would have spent entirely
on the task.

What it is meant to buy is fewer wrong paths taken confidently, fewer
rediscoveries, and fewer retries of an approach already recorded as
rejected.

Meant to. I have not measured it.

There is no study here comparing governed against ungoverned work end to
end. The benchmark that exists is one model, three synthetic tasks, two
modes, one attempt per cell. Six out of six succeeded, which is not enough
to claim anything about efficiency, so I do not.

I state the cost and leave the balance open, on the site and here. If
someone runs this on a real repository and finds the balance is negative,
that is the most useful message I could get right now, and it goes in the
repository under my own name.

### UA

Керованість коштує токенів, і я не вдаватиму інакше, поки пропоную комусь її
застосувати.

Пошук досвіду перед роботою коштує контексту. Артефакти пакета коштують
контексту. Knowledge Delta коштує контексту. Повноцінне закриття, написане
за оголошеним, а не як переказ того, що відбувалося, коштує контексту. Усе
це береться з того самого вікна, яке некерований агент витратив би цілком на
завдання.

Купувати це має менше впевнено обраних хибних шляхів, менше повторних
відкриттів і менше спроб підходу, який уже записано як відхилений.

Має. Я цього не виміряв.

Дослідження, яке порівняло б керовану й некеровану роботу від початку до
кінця, тут немає. Наявний бенчмарк це одна модель, три синтетичні завдання,
два режими, одна спроба на комірку. Шість із шести пройшли, і цього
недостатньо, щоб щось стверджувати про ефективність, тому я й не стверджую.

Я називаю ціну й лишаю баланс відкритим, і на сайті, і тут. Якщо хтось
запустить це на реальному репозиторії й побачить, що баланс негативний, це
буде найкорисніше повідомлення, яке я зараз можу отримати, і воно піде в
репозиторій під моїм ім'ям.

---

## Post 8. The tools are optional, and that is a design constraint

### EN

Three tools make EIF better. None of them is required, and the framework
installs none of them. That was not generosity, it was a constraint I put on
myself early, because a methodology that stops working when one vendor
changes a CLI flag is not a methodology.

A code graph gives structural navigation and impact analysis. Without it,
the agent falls back to source search and manual browsing, with no
graph-level hints. Slower, still correct.

A shell-output compressor filters command output before it reaches the
context window, with the reduction tracked. Without it, commands run
unfiltered and nothing is recorded. Noisier, still correct.

A documentation retriever answers from current library docs instead of
training-data recall. Without it, the agent uses local docs or its own
recall, and an unavailable provider is reported as unavailable rather than
quietly replaced by a guess about a version that may not be the installed
one.

Every fallback is named in advance, in the repository, not discovered at
runtime.

One of the three sends a query over the network. Exactly one. That is stated
in the same place as everything else it does, because "which of these leaves
my machine" is the first question I would ask about someone else's
framework.

### UA

Три інструменти роблять EIF кращим. Жоден із них не обов'язковий, і жодного
фреймворк не встановлює. Це не щедрість, а обмеження, яке я поставив собі
рано, бо методологія, що перестає працювати, коли вендор змінив прапорець у
CLI, це не методологія.

Граф коду дає структурну навігацію й аналіз впливу змін. Без нього агент
повертається до пошуку у вихідних файлах і ручного перегляду, без підказок за
графом. Повільніше, але так само правильно.

Стиснення виводу командного рядка фільтрує вивід, перш ніж він дійде до вікна
контексту, і фіксує скорочення. Без нього команди виконуються без фільтрації,
і нічого не фіксується. Шумніше, але так само правильно.

Пошук документації відповідає з актуальної документації бібліотек, а не з
пам'яті моделі. Без нього агент бере локальну документацію або власні знання
з навчання, а недоступність провайдера повідомляють як недоступність, а не
підміняють тихо здогадом про версію, яка може не збігатися зі встановленою.

Кожен запасний шлях названий заздалегідь, у репозиторії, а не з'ясовується
під час виконання.

Один із трьох надсилає запит у мережу. Рівно один. Це написано там само, де й
усе інше про нього, бо «що з цього виходить за межі моєї машини» перше
питання, яке я поставив би чужому фреймворку.

---

## Post 9. I made it hard for my own site to overclaim

### EN

Every capability sentence on the EIF website carries a claim ID. The ID
resolves to a register entry with four fields: what is claimed, the evidence,
the bound, and the wording that is forbidden for this specific claim.

The site build fails if a claim ID does not exist, if any forbidden phrase
appears anywhere in the source, if a count appears without a nearby claim
reference, if a private path leaks into the markup, or if the page would make
a runtime request to a third party.

The forbidden list includes phrases I would plausibly have written on a good
day. Production-ready. Proven at scale. Improves quality. Saves developer
hours. Faster than a human. Each one is banned because there is no
measurement behind it, and a build that fails is a better editor than my
memory at eleven at night.

It has caught me. It also once caught itself: the private-path scanner read
the "s" in "https://" as a Windows drive letter and reported the first
outbound link the site ever carried as a leaked machine path. That is in the
changelog too.

None of this makes the claims true. It makes them checkable, which is the
part I can actually build.

### UA

Кожне речення про можливості на сайті EIF має ідентифікатор твердження. Він
веде до запису в реєстрі з чотирма полями: що стверджується, який доказ, яка
межа і які формулювання для цього твердження заборонені.

Збірка сайту падає, якщо ідентифікатора не існує, якщо будь-де в джерелах
з'явилася заборонена фраза, якщо число стоїть без посилання на твердження
поруч, якщо в розмітку просочився приватний шлях або якщо сторінка зверталася
б під час роботи до сторонньої служби.

У списку заборонених є фрази, які я цілком міг би написати в хороший день.
Production-ready. Proven at scale. Покращує якість. Економить години
розробника. Швидше за людину. Кожна заборонена, бо за нею немає вимірювання,
а збірка, яка падає, кращий редактор, ніж моя пам'ять об одинадцятій вечора.

Мене вона вже ловила. Одного разу зловила й саму себе: сканер приватних
шляхів прочитав «s» у «https://» як літеру диска Windows і повідомив про
перше зовнішнє посилання сайту як про витік машинного шляху. Це теж є в
чейнджлозі.

Твердження від цього не стають істинними. Вони стають перевірюваними, а це та
частина, яку я справді можу побудувати.

---

## Post 10. The language is configuration, not a default

### EN

The reference walkthrough in the EIF repository closes its session in
Ukrainian.

Not because the framework is Ukrainian. Framework documentation is
English-first and stays that way. The run declares Ukrainian because a
closeout rendered in English would have proved nothing: English is what
everything defaults to anyway, so seeing it tells you nothing about whether
a locale layer exists.

A project instance declares its documentation locale in its own config. For
a `uk` instance, four surfaces come out in Ukrainian: status messages, the
Knowledge Delta, the closeout headings, and retrieval over Ukrainian
knowledge files. English remains the fallback for anything the locale pack
does not cover.

What this is not, and the repository says so in the same paragraph: full
localization of agent responses. The agent still answers in whatever
language you are working in. Four surfaces are verified end to end. That
number is four because I counted them, not because four is a milestone.

There is a version of this project where I would have shipped an English
demo and written "multilingual support" on the site. The demo would have
been easier and the claim would have been unverifiable. This way round, one
person who works in Ukrainian can check it in about two minutes.

### UA

Еталонний прохід у репозиторії EIF закриває сесію українською.

Не тому, що фреймворк український. Документація фреймворку англомовна
насамперед і такою лишається. Той прохід оголошує українську, бо закриття
англійською нічого не довело б: англійська і так стоїть за замовчуванням
скрізь, тож побачити її означає не дізнатися нічого про наявність мовного
рівня.

Екземпляр проєкту оголошує мову своєї документації у власній конфігурації.
Для екземпляра `uk` українською виходять чотири поверхні: статусні
повідомлення, Knowledge Delta, заголовки закриття сесії й пошук по
україномовних файлах знань. Англійська лишається запасною для всього, чого
мовний пакет не покриває.

Чого тут немає, і репозиторій каже це в тому самому абзаці: повної
локалізації відповідей агента. Агент і далі відповідає тією мовою, якою ви
працюєте. Перевірено від початку до кінця чотири поверхні. Число чотири тут
тому, що я їх порахував, а не тому, що чотири це віха.

Є версія цього проєкту, у якій я випустив би англомовне демо й написав на
сайті «мультимовна підтримка». Демо було б простіше, а твердження
неможливо було б перевірити. У цьому варіанті одна людина, яка працює
українською, перевіряє його хвилини за дві.

---

## Commenting on other people's posts

The series is one half. The other half is arriving in threads that are
already happening, which reaches the audience described at the top of this
file far more directly than a post on a small account does.

Rules, in order of how easy they are to get wrong:

1. **Enter through the strongest objection in the thread, not through the
   post.** A comment that agrees with the author adds nothing. A comment
   that answers what three commenters are already arguing about is the one
   people read.
2. **Say the one thing nobody in the thread has said.** If it is already
   there, do not comment.
3. **Link only when the link is checkable.** If the repository is private
   or the site is not deployed, do not post. A comment whose whole argument
   is "here is a thing you can go read" and then cannot be read is worse
   than silence.
4. **Concede the author's frame.** Their model is usually not wrong, it is
   usually incomplete in one specific place. Say which place.
5. **State the bound in the comment itself.** Same rule as the posts. "It
   is explicit about what it has not measured" belongs in the comment, not
   in a follow-up when someone challenges it.
6. **One comment. No reply-to-own-comment threads, no editing to add a
   link.**

### Comment 1. On "Steps of AI Adoption"

Target: Boris Cherny's post on the four steps of AI adoption and its
artifact. Chosen because the thread's dominant objection, from three
separate commenters, is that verification and trust are the real ceiling,
which is the argument this framework exists to be part of.

The angle: every guardrail named in that post governs what happens inside a
session, and none of them outlives the session. That is fine at ten agents
and expensive at a hundred. Concede the ladder, name the layer it stops
short of.

**Blocked until a public URL exists.** The repository is private and the
site is not deployed. Post it after that, and while the thread is still
moving.

#### EN

The guardrails in the list are all per-session: auto mode, code review,
worktree isolation, /loop, /batch. That holds to about step 2.

What breaks after it is not verification bandwidth. It is that agent 60 has
no idea what agents 1 through 59 already decided, tried and rejected, so
they re-derive the same context in parallel and a few of them confidently
retake a path that was ruled out that morning. Nothing in a worktree
outlives the session that made it.

The guardrail that is missing sits outside every agent: durable project
knowledge with a lifecycle, pulled into a session before implementation
rather than searched for after it, and a closeout that decides what is
allowed to persist. Rejected decisions especially, because those have to
stay rejected without a human re-explaining them each time.

I have been running a methodology built around that since May, and
published it this week as EIF: [link]. Apache-2.0, and explicit about what
it has not measured, including any comparison against ungoverned work.

Step 2 to 3 is where it starts paying for itself, which is where you put
the trust bottleneck too.

#### UA

For reposting into a Ukrainian community, not for the thread itself.

Усі згадані запобіжники діють у межах однієї сесії: автоматичний режим
дозволів, автоматичне ревʼю коду, ізоляція worktree, /loop, /batch. Цього
вистачає приблизно до другого кроку.

Далі ламається не пропускна здатність перевірки. Ламається те, що
шістдесятий агент не має уявлення, що перші пʼятдесят девʼять уже
вирішили, спробували й відхилили. Вони паралельно доходять до того самого
контексту, а дехто впевнено повертається на шлях, який відкинули того ж
ранку. Ніщо у worktree не переживає сесію, яка його створила.

Запобіжник, якого бракує, лежить поза кожним агентом: стійке знання
проєкту з життєвим циклом, яке підтягують у сесію перед реалізацією, а не
шукають після неї, і закриття, яке вирішує, чому дозволено лишитися.
Особливо відхиленим рішенням, бо вони мають лишатися відхиленими без того,
щоб людина щоразу пояснювала це наново.

Я працюю за методологією, побудованою навколо цього, з травня, а цього
тижня опублікував її як EIF: [посилання]. Ліцензія Apache-2.0, і там прямо
сказано, чого не виміряно, зокрема будь-якого порівняння з некерованою
роботою.

#### Replies to prepare for

Draft direction only. Write the actual reply against what was said, not
against what was predicted.

- **"This is just RAG for your codebase."** No. Retrieval is one step of
  six. The part that does the work is the lifecycle: an artifact has a
  status, and a rejected one stays out of results until somebody decides
  otherwise. A vector store will happily return the approach you abandoned
  last week, ranked highly, because it is semantically perfect.
- **"Sounds like a lot of process for a solo dev."** Agreed, and at one
  agent it probably is not worth it. Say so. The whole argument is that it
  starts paying somewhere past step 2.
- **"Do you have numbers?"** No, and say it in the first sentence. One
  bounded pilot, one model, three fixtures, one attempt per cell. Not
  enough for a directional claim, which is why the site does not make one.
  Offer the register, do not argue.
- **"How is this different from CLAUDE.md / cursor rules / AGENTS.md?"**
  Those are instructions to the agent. This is knowledge about the project
  with a status and a source, plus a rule about what is allowed to become
  one of those instructions. EIF generates the entrypoint file; it is the
  output, not the system.
- **A hostile "another framework" reply.** One line, no defence: fair,
  there are a lot. It is Apache-2.0 and the claims register lists what is
  unverified, so it is cheap to check and cheap to dismiss.

## What to watch, and what to ignore

Ignore: impressions, likes, follower count. They measure how well a post
suits a feed, which is not the goal stated at the top of this file.

Watch, in order of what each is worth:

1. Someone reports running it on a repository that is not mine. This is the
   only outcome that changes what gets built next.
2. A specific objection to a mechanism. "The two-loop thing will not survive
   a team of eight" is worth more than fifty agreements.
3. Someone finds a claim on the site that the evidence does not support.
   That is a bug report, and it goes in the register.
4. Comments that engage with the bound rather than the headline. A reader
   who says "n=1 per cell is not a benchmark" has read the post.

If four weeks in, nobody has done any of the four, the series is not
working, and the answer is probably that the posts are describing mechanisms
to people who have not hit the problem yet. In that case: fewer mechanism
posts, more concrete failure stories with the mechanism at the end.

## Reserve topics

Written up only if the arc lands and there is appetite for more.

- The privacy scan and its suppression mechanism. A suppression identifies
  one finding by rule, exact path, content fingerprint, rationale and review
  date. It never disables a rule and never weakens a pattern, and an expired
  suppression is itself a finding. Good post about the difference between
  an exception and a hole.
- Adopting an existing repository that already has its own governance. The
  preflight refuses to write anything until someone decides how the two
  coexist.
- Adapters as a frozen scope. Four, no fifth, and why deciding to stop was
  harder than adding another.
- What "experimental" is actually doing in the capability table, and why
  half the rows say it.
