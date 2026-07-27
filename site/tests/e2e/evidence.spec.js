import { test, expect } from '@playwright/test';

test.describe('engineering-intelligence methodology', () => {
  test('explains layers, session lifecycle, learning and skills without an outcome claim', async ({
    page,
  }) => {
    await page.goto('/#methodology');
    await expect(page.locator('#methodology')).toContainText('Engineering Intelligence');
    await expect(page.locator('#layers .layers__layer')).toHaveCount(3);
    await expect(page.locator('#session .session__timeline li')).toHaveCount(4);
    await expect(page.locator('#learning .learning__flow li')).toHaveCount(6);
    await expect(page.locator('#learning')).toContainText('Retro');
    await expect(page.locator('#learning')).toContainText('versioned instructions, not hidden model behavior');
    await expect(page.locator('#methodology')).toContainText('does not train model weights');
    // The traced packet diagram carries the layer story now: four written
    // outcomes plus a drawn map, both present without any script running.
    await expect(page.locator('#layers .ledger__outcome')).toHaveCount(4);
    await expect(page.locator('#layers .ledger')).toContainText('CLOSEOUT + RETRO');
    await expect(page.locator('#layers .ledger')).toContainText('Packet memory');
    await expect(page.locator('#layers .ledger')).toContainText('Retrieval, not recall');
  });

  test('the two knowledge directions read as a matched pair', async ({ page }) => {
    await page.goto('/#layers');
    const up = page.locator('.layers__flow--up');
    await expect(page.locator('.layers__flow--down')).toBeVisible();
    await expect(up).toContainText('Promotion is the exception');

    // Each flow is a two-row grid stretched to the taller column's height,
    // and auto rows stretch by default: the shorter half used to push its
    // spare height into the gap under its own "Flows up:" lead-in.
    const alignContent = await up.evaluate((el) => getComputedStyle(el).alignContent);
    expect(alignContent).toBe('start');
  });

  test('no outcome column under the traced map is coloured louder than its neighbours', async ({
    page,
  }) => {
    await page.goto('/#layers');
    const columns = await page.evaluate(() =>
      [...document.querySelectorAll('#layers .ledger__outcome')].map((el) => ({
        border: getComputedStyle(el).borderTopColor,
        hasMarker:
          getComputedStyle(el.querySelector('.label'), '::before').content !== 'none',
      })),
    );
    expect(columns).toHaveLength(4);
    // One uniform hairline: the per-outcome tint made "At closeout" look
    // promoted above the other three for a reason nothing on the page stated.
    expect(new Set(columns.map((c) => c.border)).size).toBe(1);
    // The colour moved to a marker that matches the mark in the drawing.
    expect(columns.every((c) => c.hasMarker)).toBe(true);
  });

  test('Ukrainian mode carries the same methodology structure', async ({ page }) => {
    await page.goto('/');
    await page.locator('#lang-toggle').click();
    await expect(page.locator('#methodology')).toContainText('Інженерний інтелект');
    await expect(page.locator('#layers .layers__layer')).toHaveCount(3);
    await expect(page.locator('#session .session__timeline li')).toHaveCount(4);
    await expect(page.locator('#learning .learning__flow li')).toHaveCount(6);
    await expect(page.locator('#learning')).toContainText('Ретроспектива');
    await expect(page.locator('#layers .ledger__outcome')).toHaveCount(4);
    await expect(page.locator('#layers .ledger')).toContainText('ЗАКРИТТЯ І РЕТРО');
    await expect(page.locator('#layers .ledger')).toContainText('Пакет зберігає контекст');
    await expect(page.locator('#learning')).toContainText('не прихована поведінка моделі');
    await expect(page.locator('#loop')).toContainText('Контекст');
    await expect(page.locator('#loop')).toContainText('Уточнення');
    await expect(page.locator('body')).toContainText(
      'зберігаються між сесіями',
    );

    const ukrainianText = await page.locator('main').innerText();
    for (const avoidableAnglicism of [
      'scope',
      'progress',
      'failure patterns',
      'fallback',
      'core path',
      'vendor docs',
      'codebase',
      'workflow',
      'closeout',
      'promotion',
      'Tier 1',  // English must not regress to tier wording
      'Tier 2',
      'Tier 3',
      'playbook',
      'skill',
      'Орієнтація',
      'Коригування',
      'розмовою з агентом',
    ]) {
      expect(ukrainianText).not.toContain(avoidableAnglicism);
    }
    for (const canonicalArtifact of ['Knowledge Delta']) {
      expect(ukrainianText).toContain(canonicalArtifact);
    }
    // Compared case-insensitively on purpose: several of these render inside
    // .label, which is text-transform: uppercase, so innerText returns the
    // transformed casing. The assertion is about the adapted Ukrainian term
    // being used instead of an anglicism, not about how it is cased.
    const ukrainianLower = ukrainianText.toLowerCase();
    // Layers are named, not numbered: numbering is navigational shorthand
    // only (Р1/Р2/Р3), so asserting "рівень 1" would lock in the wording the
    // rename deliberately removed.
    for (const adaptedTerm of [
      'сценарії роботи',
      'навички агента',
      'рівень фреймворку',
      'рівень проєкту',
    ]) {
      expect(ukrainianLower).toContain(adaptedTerm);
    }
  });
});

test.describe('evidence', () => {
  test('eight task rows are present', async ({ page }) => {
    await page.goto('/#evidence');
    const rows = page.locator('#evidence .reveal');
    await expect(rows).toHaveCount(8);
    for (const label of [
      'Install',
      'Adopt',
      'Retrieve',
      'Plan',
      'Verify',
      'Switch',
      'Localize',
      'Measure',
    ]) {
      await expect(page.locator('#evidence .reveal', { hasText: label })).toBeVisible();
    }
  });

  test('the install row states the command that works, not the index it is not on', async ({
    page,
  }) => {
    await page.goto('/#evidence');
    const install = page.locator('#evidence .reveal').nth(0);
    await expect(install).toContainText('pip install .');
    // Release status is docs/product/release-status.md's job, not this row's.
    // What stays here is the bound on the evidence itself.
    await expect(install).not.toContainText('PyPI');
    await expect(install).toContainText('Claude Code adapter');
  });

  test('every row carries its own scope line, and none of them apologises', async ({ page }) => {
    await page.goto('/#evidence');
    // Was a "Bounded proof on record" block trailing the whole section,
    // which read as a disclaimer appended to a page of claims. Then the
    // per-row bound was labelled "Limitation:", which read as an apology
    // attached to every capability. It is the scope of the check now, in the
    // row the check belongs to.
    await expect(page.locator('.evidence__proof')).toHaveCount(0);
    const scopes = page.locator('#evidence .reveal__detail strong', { hasText: 'Scope:' });
    await expect(scopes).toHaveCount(8);
    await expect(page.locator('#evidence')).not.toContainText('Limitation:');
    // Nothing on this page presents itself as unreleased or provisional.
    for (const word of ['pilot', 'Pre-release', 'pre-release', 'not yet']) {
      await expect(page.locator('#evidence')).not.toContainText(word);
    }
  });

  test('the switch row names four supported adapters, with no tier among them', async ({ page }) => {
    await page.goto('/#evidence');
    const swap = page.locator('#evidence .reveal').nth(5);
    await expect(swap).toContainText('Four adapters for four agents');
    await expect(swap).toContainText('twelve ordered pairs');
    // D-16 retired the required/experimental split: what differs between the
    // four is hook mechanics, and the row says so instead of labelling two of
    // them as provisional.
    await expect(swap).not.toContainText('experimental');
    await expect(swap).toContainText('mechanics, not status');
  });

  test('the Ukrainian rows read as Ukrainian, not as a word-for-word carry-over', async ({
    page,
  }) => {
    await page.goto('/#evidence');
    await page.locator('#lang-toggle').click();
    const section = page.locator('#evidence');
    await expect(section).toContainText('Чотири адаптери для чотирьох агентів');
    await expect(section.locator('.reveal__detail strong', { hasText: 'Межі:' })).toHaveCount(8);

    const text = await section.innerText();
    // The three that made the Measure row unreadable: "комірка" for a table
    // cell, "мовчанка" for a deliberate absence of a claim, and "пілот" for
    // a benchmark run. All three are literal carries that mean something
    // else, or nothing, in Ukrainian.
    for (const carriedOver of ['комірка', 'комірку', 'мовчанка', 'пілот', 'Обмеження:']) {
      expect(text).not.toContain(carriedOver);
    }
  });

  test('the measured/not-measured boundary survives, stated plainly', async ({ page }) => {
    await page.goto('/#evidence');
    const measure = page.locator('#evidence .reveal').nth(7);
    await expect(measure).toContainText('one model, three fixtures, six attempts');
    await expect(measure).toContainText('makes no efficiency or task-quality claim');
    await expect(measure).toContainText('no baseline and no control group');
    await expect(measure).toContainText(
      'Nothing measures how long a person spends writing or reviewing code',
    );
  });
});

test.describe('quickstart', () => {
  test('shows the real init command and no command the reader cannot run yet', async ({ page }) => {
    await page.goto('/#quickstart');
    await expect(page.locator('#install-panel-unix')).toContainText('pip install .');
    await expect(page.locator('.install__init-command')).toContainText('eifctl init');
    const section = page.locator('#quickstart');
    // The screen carries a command that works from a clone. It must never
    // print the package-index form, which is the one thing here that would
    // fail for a reader; that guarantee is what lets the screen drop the
    // release-status notes it used to carry. Those now live in
    // docs/product/release-status.md, off the page.
    await expect(section).not.toContainText('pip install engineering-intelligence-framework');
    await expect(section).not.toContainText('not yet published');
    await expect(section).not.toContainText('eif_release.py');
    // The reference run's locale is stated as a configuration outcome, not
    // as an unexplained "closes in Ukrainian".
    await expect(section).toContainText('whichever language the instance');
  });

  test('answers the three questions a first-time reader actually has', async ({ page }) => {
    await page.goto('/#quickstart');
    const section = page.locator('#quickstart');
    // Where does this go, what do I need first.
    await expect(section).toContainText('Python 3.11 or newer');
    await expect(section).toContainText('typed into a terminal');
    // What is that lone dot. It read as a typo to the first owner review.
    await expect(section).toContainText('is not a typo');
    // And the closing paragraph carries the weight of supporting prose, not
    // of a second lede - it is the only unclassed <p> the section used to
    // have, and it rendered at full foreground because of it.
    const outcome = section.locator('.quickstart__outcome');
    await expect(outcome).toHaveCSS('color', 'rgb(168, 159, 140)');
  });
});

test.describe('honesty guardrails after the limitations section was removed', () => {
  test('the no-quality-claim now lives with the evidence it qualifies', async ({ page }) => {
    await page.goto('/#evidence');
    // It has moved three times, all in the same direction: out of a
    // standalone limitations section, into a proof block under the ledger,
    // then into the Measure row beside the run it qualifies, and finally
    // into plain language there.
    const measure = page.locator('#evidence .reveal').nth(7);
    await expect(measure).toContainText('no efficiency or task-quality claim anywhere');
    await expect(measure).toContainText('no baseline and no control group');
  });

  test('no section, anchor or link to a limitations section survives', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#limitations')).toHaveCount(0);
    await expect(page.locator('a[href="#limitations"]')).toHaveCount(0);
  });
});

test.describe('final CTA', () => {
  test('the repository link is live in every build mode', async ({ page }) => {
    await page.goto('/');
    const repoLink = page.locator('.final-cta__repo');
    // It used to resolve to "#evidence" outside a production build, so the
    // closing screen's one outbound destination was a dead link in dev and
    // preview. The URL is a project constant now, not a deployment input.
    await expect(repoLink).toHaveAttribute(
      'href',
      'https://github.com/mike-arbuzov365/engineering-intelligence-framework',
    );
    await expect(repoLink).toHaveText('Public repository');
    // And the caveat line under it is gone rather than permanently empty:
    // it captioned a decision that has since been made.
    await expect(page.locator('.final-cta__pending')).toHaveCount(0);
  });

  test('the closing screen is two matched groups of destinations, not a strip of links', async ({
    page,
  }) => {
    await page.goto('/');
    await expect(page.locator('.final-cta__group')).toHaveCount(2);
    await expect(page.locator('.final-cta__group-title').nth(0)).toHaveText('Read on');
    await expect(page.locator('.final-cta__group-title').nth(1)).toHaveText('Reach me');

    const readOn = page.locator('.final-cta__group').nth(0).locator('a');
    await expect(readOn.nth(0)).toHaveAttribute('href', '#control-plane');
    await expect(readOn.nth(1)).toHaveAttribute('href', '#evidence');

    const reachMe = page.locator('.final-cta__group').nth(1).locator('a');
    await expect(reachMe).toHaveCount(2);
    await expect(reachMe.nth(0)).toHaveAttribute(
      'href',
      'https://www.linkedin.com/in/preosvan/',
    );
    await expect(reachMe.nth(1)).toHaveAttribute('href', 'mailto:mike.arbuzov365@gmail.com');

    // Every row explains where it goes; a bare link list is what this
    // replaced.
    const rows = page.locator('.final-cta__rows > li');
    await expect(rows).toHaveCount(5);
  });

  test('the closing screen states what this is and what keeps it current', async ({ page }) => {
    await page.goto('/');
    const lede = page.locator('#final-cta .section__lede');
    // The strongest fact available: this is not a proposal, it is the public
    // form of something already in daily use.
    await expect(lede).toContainText('public extraction of a private framework');
    await expect(lede).toContainText('every working day');
    // The old lede set disagreement against agreement to tell the reader how
    // to feel about the contact column, and "developed in the open" left it
    // ambiguous whether the framework or the engineer was being described.
    await expect(lede).not.toContainText('disagreement');
    await expect(lede).not.toContainText('decoration');
    await expect(lede).not.toContainText('developed in the open');

    const notes = page.locator('#final-cta .final-cta__note p');
    await expect(notes).toHaveCount(2);
    await expect(notes.nth(0)).toContainText('stays with that repository');
    await expect(notes.nth(1)).toContainText('already behind');
    // On-page destinations are labelled with the page's own section numbers,
    // instead of the same words twice down one column.
    const readOnLabels = page.locator('.final-cta__group').nth(0).locator('.label');
    await expect(readOnLabels.nth(0)).toHaveText('Section 04');
    await expect(readOnLabels.nth(1)).toHaveText('Section 09');
  });

  test('the whole closing screen translates, including the repository label', async ({ page }) => {
    await page.goto('/');
    await page.locator('#lang-toggle').click();
    await expect(page.locator('.final-cta__repo')).toHaveText('Публічний репозиторій');
    await expect(page.locator('.final-cta__group-title').nth(1)).toHaveText('Зв’язатися');
    const reachMe = page.locator('.final-cta__group').nth(1).locator('a');
    await expect(reachMe.nth(0)).toHaveAttribute(
      'href',
      'https://www.linkedin.com/in/preosvan/',
    );
    await expect(reachMe.nth(1)).toHaveAttribute('href', 'mailto:mike.arbuzov365@gmail.com');
  });

  test('the footer states the licence and nothing about the build machine', async ({ page }) => {
    await page.goto('/');
    const footer = page.locator('footer');
    await expect(footer).toContainText('Apache-2.0');
    await expect(footer).not.toContainText('not yet deployed');
    await page.locator('#lang-toggle').click();
    await expect(footer).toContainText('Apache-2.0');
    await expect(footer).not.toContainText('не розгорнута');
  });
});

test.describe('evidence no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('all eight task rows and their limitations are readable without a script', async ({
    page,
  }) => {
    await page.goto('/#evidence');
    const details = page.locator('#evidence .reveal__detail');
    await expect(details).toHaveCount(8);
    for (let index = 0; index < 8; index += 1) {
      await expect(details.nth(index)).toBeVisible();
    }
    const text = await page.locator('#evidence .evidence__tasks').innerText();
    for (const word of [
      'Install',
      'Adopt',
      'Retrieve',
      'Plan',
      'Verify',
      'Switch',
      'Localize',
      'Measure',
    ]) {
      expect(text.toLowerCase()).toContain(word.toLowerCase());
    }
    expect(text).toContain('Scope:');
  });
});
