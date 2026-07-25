import { test, expect } from '@playwright/test';

test.describe('engineering-intelligence methodology', () => {
  test('explains layers, session lifecycle, learning and skills without an outcome claim', async ({
    page,
  }) => {
    await page.goto('/#methodology');
    await expect(page.locator('#methodology')).toContainText('Engineering Intelligence');
    await expect(page.locator('#layers .layers__tier')).toHaveCount(3);
    await expect(page.locator('#session .session__timeline li')).toHaveCount(4);
    await expect(page.locator('#learning .learning__flow li')).toHaveCount(6);
    await expect(page.locator('#learning')).toContainText('Retro');
    await expect(page.locator('#learning')).toContainText('versioned instructions, not hidden model behavior');
    await expect(page.locator('#methodology')).toContainText('does not train model weights');
    // The traced packet diagram carries the tier story now: four written
    // outcomes plus a drawn map, both present without any script running.
    await expect(page.locator('#layers .ledger__outcome')).toHaveCount(4);
    await expect(page.locator('#layers .ledger')).toContainText('CLOSEOUT + RETRO');
    await expect(page.locator('#layers .ledger')).toContainText('Packet memory');
    await expect(page.locator('#layers .ledger')).toContainText('Retrieval, not recall');
  });

  test('Ukrainian mode carries the same methodology structure', async ({ page }) => {
    await page.goto('/');
    await page.locator('#lang-toggle').click();
    await expect(page.locator('#methodology')).toContainText('Інженерний інтелект');
    await expect(page.locator('#layers .layers__tier')).toHaveCount(3);
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
      'Tier 1',
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
    for (const adaptedTerm of ['сценарії роботи', 'навички агента', 'рівень 1']) {
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
  test('shows the real init command and no PyPI/human-duration promise', async ({ page }) => {
    await page.goto('/#quickstart');
    await expect(page.locator('.quickstart__command')).toContainText('eif_init.py');
    const section = page.locator('#quickstart');
    await expect(section).not.toContainText('pip install eifctl');
    await expect(section).toContainText('No PyPI package yet');
  });
});

test.describe('limitations', () => {
  test('states pre-release, no-PyPI and the no-quality-claim explicitly', async ({ page }) => {
    await page.goto('/#limitations');
    const section = page.locator('#limitations');
    await expect(section).toContainText('Pre-release');
    await expect(section).toContainText('Not on PyPI');
    await expect(section).toContainText('makes no claim about task quality');
  });
});

test.describe('final CTA', () => {
  test('repository link falls back to an on-page anchor without a configured URL', async ({
    page,
  }) => {
    await page.goto('/');
    const repoLink = page.locator('.final-cta__repo');
    await expect(repoLink).toHaveAttribute('href', '#evidence');
    await expect(repoLink).toContainText('link added at publication');
  });

  test('architecture and evidence links point on-page', async ({ page }) => {
    await page.goto('/');
    const links = page.locator('.final-cta__links a');
    await expect(links.nth(0)).toHaveAttribute('href', '#control-plane');
    await expect(links.nth(1)).toHaveAttribute('href', '#evidence');
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
