import { test, expect } from '@playwright/test';

test.describe('hero', () => {
  test('product name is the loudest element, and the hero is four controls, one of which leaves the page', async ({
    page,
  }) => {
    await page.goto('/');
    const h1Text = (await page.textContent('h1.hero__name'))?.replace(/\s+/g, ' ').trim();
    expect(h1Text).toContain('Engineering Intelligence Framework');
    await expect(page.locator('.hero__ctas a')).toHaveCount(4);
    await expect(page.locator('.hero__ctas .hero__ctas-repo')).toHaveCount(1);
    // A second button row and a strip of facts were tried here and made the
    // screen busier without making it clearer.
    await expect(page.locator('.hero__facts')).toHaveCount(0);
    await expect(page.locator('.hero__actions')).toHaveCount(0);
  });

  test('the repository control is the only filled one on the page', async ({ page }) => {
    await page.goto('/');
    const repo = page.locator('.hero__ctas-repo');
    // The fourth pill used to be a fourth scroll anchor, so the hero's
    // loudest row went nowhere at all.
    await expect(repo).toHaveAttribute(
      'href',
      'https://github.com/mike-arbuzov365/engineering-intelligence-framework',
    );
    await expect(repo).toHaveAttribute('target', '_blank');
    await expect(repo).toHaveAttribute('rel', /noopener/);
    // At pill size the word alone was not saying "GitHub"; the mark rides
    // with it, in place of the caret the three anchors carry.
    await expect(repo.locator('.hero__ctas-mark')).toHaveCount(1);

    const filled = await page.evaluate(() => {
      const accent = getComputedStyle(document.documentElement)
        .getPropertyValue('--eif-accent')
        .trim();
      const toRgb = (value) => {
        const probe = document.createElement('span');
        probe.style.color = value;
        document.body.append(probe);
        const resolved = getComputedStyle(probe).color;
        probe.remove();
        return resolved;
      };
      const target = toRgb(accent);
      return [...document.querySelectorAll('a, button')]
        // The skip link is filled too, and should be: it is an accessibility
        // affordance that only exists while focused, not a control competing
        // for attention on the page.
        .filter((el) => !el.classList.contains('skip-link'))
        .filter((el) => getComputedStyle(el).backgroundColor === target)
        .map((el) => el.className);
    });
    expect(filled).toEqual(['hero__ctas-repo']);
  });

  test('no horizontal overflow at the configured viewport', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(700);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflow).toBe(false);
  });

  test('reduced motion: hero content is final-state immediately, no animation applied', async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');
    const { opacity, animationName } = await page.evaluate(() => {
      const style = getComputedStyle(document.querySelector('.hero__name'));
      return { opacity: style.opacity, animationName: style.animationName };
    });
    expect(opacity).toBe('1');
    expect(animationName).toBe('none');
  });

  test('keyboard: skip link, language toggle, then the four hero controls in order', async ({
    page,
  }) => {
    await page.goto('/');
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveClass('skip-link');

    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveId('lang-toggle');

    // Three destinations on this page, then the one that leaves it: what
    // this is, how it is built, how it learns, and where the code is.
    for (const label of [
      'What EIF is',
      'The three layers',
      'How it learns',
      'GitHub',
    ]) {
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus')).toHaveText(label);
    }
  });

  test('the four hero controls stay on one row from 1080px up', async ({ page }) => {
    await page.goto('/');
    // The hero splits into prose and figure at 1080, and a longer label on
    // the repository pill put the row over its column between there and
    // about 1170 - one pill dropping to a second line over two pixels of
    // slack. Same word in both languages for the same reason.
    for (const width of [1080, 1170, 1280, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      const tops = await page
        .locator('.hero__ctas a')
        .evaluateAll((els) => [...new Set(els.map((el) => Math.round(el.getBoundingClientRect().top)))]);
      expect(tops, `wrapped at ${width}px`).toHaveLength(1);
    }
  });

  test('one orbit drawing, expanded in two places, and the circuit is off the page', async ({
    page,
  }) => {
    await page.goto('/');
    // A hero is a poster: no key under it. Section 03 draws the same mark
    // and is where it is explained, with the five-line key beside it.
    await expect(page.locator('.hero__legend')).toHaveCount(0);
    await expect(page.locator('.hero .hero__aside .figure-legend')).toHaveCount(0);
    await expect(page.locator('.hero .scale__map')).toHaveCount(1);
    await expect(page.locator('#layers .scale .scale__map')).toHaveCount(1);
    await expect(page.locator('.hero .scale__core-label')).toHaveText('EIF');
    await expect(page.locator('#layers .scale .figure-legend__item')).toHaveCount(5);

    // The circuit is archived under src/partials/deprecated/, not rendered.
    // Its class names are what would give it away if a copy came back.
    await expect(page.locator('.hero__shelf')).toHaveCount(0);

    // Both copies come from the same partial, so they cannot drift: same
    // shape count, same tip count, in whichever language is showing.
    const shapes = (scope) =>
      page.locator(`${scope} .scale__map`).evaluate((svg) => ({
        shapes: svg.querySelectorAll('circle, path, line, rect, text').length,
        tips: svg.querySelectorAll('[data-tip]').length,
      }));
    expect(await shapes('.hero')).toEqual(await shapes('#layers .scale'));
  });

  test('the curator is a dot on a ring, with an aura and nothing else', async ({ page }) => {
    await page.goto('/');
    const curator = page.locator('.hero .scale__curator');
    await expect(curator.locator('.scale__curator-ring')).toHaveCount(1);
    await expect(curator.locator('.scale__curator-dot')).toHaveCount(1);
    // The aura is what survived an attempt to draw the curator as a tapered
    // comet: it kept the mark alive, the tail made it read as an alarm on a
    // figure whose subject is the green circuit.
    await expect(curator.locator('.scale__curator-halo')).toHaveCount(1);
    await expect(curator.locator('.scale__curator-tail')).toHaveCount(0);

    const marker = await page.locator('.hero .scale__curator-marker').evaluate((el) => {
      const style = getComputedStyle(el);
      return {
        animationName: style.animationName,
        duration: style.animationDuration,
        origin: style.transformOrigin,
      };
    });
    expect(marker.animationName).toBe('eif-scale-curator');
    // Its own period, deliberately unrelated to the 16s promotion sequence:
    // curation is not a step in it.
    expect(marker.duration).toBe('27s');
    expect(marker.origin).toBe('310px 266px');

    const halo = await page
      .locator('.hero .scale__curator-halo')
      .evaluate((el) => getComputedStyle(el).animationName);
    expect(halo).toBe('eif-scale-curator-halo');

    // The key beside the figure in section 03 draws it at the size it is.
    await expect(page.locator('#layers .scale .figure-legend__item--dot-warn')).toHaveCount(1);
  });

  test('sessions are named nodes a step smaller than the projects above them', async ({ page }) => {
    await page.goto('/');
    const labels = await page
      .locator('.hero .scale__session text')
      .evaluateAll((els) => els.map((el) => el.textContent));
    expect(labels).toEqual(['S1', 'S2', 'S3']);

    const radii = await page.evaluate(() => ({
      session: Number(
        document.querySelector('.hero .scale__session circle').getAttribute('r'),
      ),
      project: Number(
        document.querySelector('.hero .scale__project circle').getAttribute('r'),
      ),
    }));
    // Same kind of object, one level down. They were bare dots, which read
    // as punctuation under the packet bracket rather than as the three runs
    // the bracket groups.
    expect(radii.session).toBeLessThan(radii.project);
  });

  test('the hero mark translates its route notes with the page', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('.hero .scale__note').first()).toHaveText('method + experience');
    await page.locator('#lang-toggle').click();
    await expect(page.locator('.hero .scale__note').first()).toHaveText('метод і досвід');
    // Proper nouns stay put in both languages.
    await expect(page.locator('.hero .scale__core-label')).toHaveText('EIF');
  });

  test('hero figure stops animating once the hero is scrolled away', async ({ page }) => {
    await page.goto('/');
    const mark = page.locator('.hero .scale__session--1');
    const inSection = page.locator('#layers .scale .scale__session--1');
    const playState = (locator) =>
      locator.evaluate((el) => getComputedStyle(el).animationPlayState);

    expect(await playState(mark)).toBe('running');

    // Far enough that no part of the full-height hero is intersecting.
    await page.evaluate(() => window.scrollTo(0, 4000));
    await expect(page.locator('.hero .hero__figure')).toHaveClass(/is-paused/);
    expect(await playState(mark)).toBe('paused');
    // Section 03 draws the same partial and shares its class names, but it is
    // a different figure in a different section: it must not freeze because
    // the hero left the viewport, which is exactly when it is being read.
    expect(await playState(inSection)).toBe('running');

    // Resumes rather than restarting, so returning to the top does not
    // replay the accumulation from empty.
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(page.locator('.hero .hero__figure')).not.toHaveClass(/is-paused/);
    expect(await playState(mark)).toBe('running');
  });

  test('the pause observer survives a language swap', async ({ page }) => {
    await page.goto('/');
    // The hero mark now lives inside an i18n block, so switching language
    // replaces the SVG node and leaves the previous observer holding a
    // detached element.
    await page.locator('#lang-toggle').click();
    await page.evaluate(() => window.scrollTo(0, 4000));
    await expect(page.locator('.hero .hero__figure')).toHaveClass(/is-paused/);
    await page.evaluate(() => window.scrollTo(0, 0));
    await expect(page.locator('.hero .hero__figure')).not.toHaveClass(/is-paused/);
  });

  test('no third-party network requests on hero load', async ({ page }) => {
    const external = [];
    page.on('request', (req) => {
      const url = new URL(req.url());
      if (url.hostname !== 'localhost' && url.hostname !== '127.0.0.1') {
        external.push(req.url());
      }
    });
    await page.goto('/');
    expect(external).toEqual([]);
  });
});

test.describe('hero no-js', () => {
  test.use({ javaScriptEnabled: false });

  test('hero content and all four control hrefs are present without a script running', async ({
    page,
  }) => {
    await page.goto('/');
    await expect(page.locator('#lang-toggle')).toBeHidden();
    const h1Text = (await page.textContent('h1.hero__name'))?.replace(/\s+/g, ' ').trim();
    expect(h1Text).toContain('Engineering Intelligence Framework');

    // Plain anchors, so the repository link works with no script at all.
    const hrefs = await page
      .locator('.hero__ctas a')
      .evaluateAll((els) => els.map((el) => el.getAttribute('href')));
    expect(hrefs).toEqual([
      '#methodology',
      '#layers',
      '#learning',
      'https://github.com/mike-arbuzov365/engineering-intelligence-framework',
    ]);
  });

  test('the orbit renders without a script, in the hero and in section 03', async ({ page }) => {
    await page.goto('/');
    // The drawing is a build-time include, not something JavaScript assembles:
    // an unexpanded marker would leave both places empty here and nowhere else.
    await expect(page.locator('.hero .scale__map')).toHaveCount(1);
    await expect(page.locator('#layers .scale .scale__map')).toHaveCount(1);
    await expect(page.locator('.hero .scale__curator-dot')).toHaveCount(1);
    await expect(page.locator('.hero .scale__session')).toHaveCount(3);
  });
});
