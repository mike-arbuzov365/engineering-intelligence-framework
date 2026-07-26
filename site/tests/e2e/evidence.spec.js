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
    await expect(page.locator('#layers .ledger')).toContainText('ЗАКРИТТЯ + РЕТРО');
    await expect(page.locator('#layers .ledger')).toContainText('Пам’ять пакета');
    await expect(page.locator('#learning')).toContainText('не прихована поведінка моделі');
    await expect(page.locator('#loop')).toContainText('Контекст');
    await expect(page.locator('#loop')).toContainText('Уточнення');
    await expect(page.locator('body')).toContainText(
      'переживають кожну окрему сесію',
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
  test('seven task rows are present', async ({ page }) => {
    await page.goto('/#evidence');
    const rows = page.locator('#evidence .reveal');
    await expect(rows).toHaveCount(7);
    for (const label of ['Install', 'Adopt', 'Retrieve', 'Plan', 'Verify', 'Switch', 'Localize']) {
      await expect(page.locator('#evidence .reveal', { hasText: label })).toBeVisible();
    }
  });

  test('bounded pilot and timing evidence name their own limits', async ({ page }) => {
    await page.goto('/#evidence');
    const proof = page.locator('.evidence__proof');
    await expect(proof).toContainText('not a statistically powered efficiency comparison');
    await expect(proof).toContainText('No claim is made about human authoring or review time');
  });
});

test.describe('quickstart', () => {
  test('shows the real init command, the package-index caveat and no human-duration promise', async ({
    page,
  }) => {
    await page.goto('/#quickstart');
    const command = page.locator('.quickstart__command');
    await expect(command).toContainText('pip install .');
    await expect(command).toContainText('eifctl init');
    const section = page.locator('#quickstart');
    // `pip install` is real here, from a clone; what is not real yet is a
    // package index, and the caveat says exactly that and no more.
    await expect(section).not.toContainText('pip install engineering-intelligence-framework');
    await expect(section).toContainText('Installable, not yet published');
    await expect(section).toContainText('eif_release.py');
    await expect(section).toContainText('No claim is made about how long any of this takes a human');
    // The reference run's locale is stated as a configuration outcome, not
    // as an unexplained "closes in Ukrainian".
    await expect(section).toContainText('whichever language the instance');
  });
});

test.describe('honesty guardrails after the limitations section was removed', () => {
  test('the no-quality-claim now lives with the evidence it qualifies', async ({ page }) => {
    await page.goto('/#evidence');
    const proof = page.locator('.evidence__proof');
    await expect(proof).toContainText('makes no claim about task quality');
    await expect(proof).toContainText('no baseline, no control group');
  });

  test('no section, anchor or link to a limitations section survives', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#limitations')).toHaveCount(0);
    await expect(page.locator('a[href="#limitations"]')).toHaveCount(0);
  });
});

test.describe('final CTA', () => {
  test('repository link falls back to an on-page anchor without a configured URL', async ({
    page,
  }) => {
    await page.goto('/');
    const repoLink = page.locator('.final-cta__repo');
    await expect(repoLink).toHaveAttribute('href', '#evidence');
    // The label is the promise; the pre-publication caveat is its own line,
    // not a parenthetical inside the call to action.
    await expect(repoLink).toHaveText('Public repository');
    // The caveat sits in the repository row, not inside the link label, and
    // the build empties it once a real URL exists.
    await expect(page.locator('.final-cta__pending')).toContainText(
      'added at publication',
    );
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

  test('all seven task rows and their limitations are readable without a script', async ({
    page,
  }) => {
    await page.goto('/#evidence');
    const details = page.locator('#evidence .reveal__detail');
    await expect(details).toHaveCount(7);
    for (let index = 0; index < 7; index += 1) {
      await expect(details.nth(index)).toBeVisible();
    }
    const text = await page.locator('#evidence .evidence__tasks').innerText();
    for (const word of ['Install', 'Adopt', 'Retrieve', 'Plan', 'Verify', 'Switch', 'Localize']) {
      expect(text.toLowerCase()).toContain(word.toLowerCase());
    }
    expect(text).toContain('Limitation:');
  });
});
