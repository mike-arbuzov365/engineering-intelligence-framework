import './styles/tokens.css';
import './styles/base.css';
import './styles/hero.css';
import './styles/sections.css';
import './styles/loop.css';
import './styles/integrations.css';
import './styles/content.css';
import './styles/reveal.css';
import './styles/motion.css';
import './styles/figure-tip.css';
import './styles/code-block.css';
import './styles/install.css';
import './styles/lang-toggle.css';

// Collapse enhanced disclosures only after the main module and its styles
// loaded successfully. If JavaScript is disabled or this bundle fails, the
// static HTML stays expanded and readable instead of becoming dead UI.
document.documentElement.classList.add('js');

// The `eif:deploy-status` meta tag is injected at build time by the
// eif-deploy-status Vite plugin (vite.config.js), so it is statically
// verifiable in dist/index.html without running this script.

let loopCleanup;

// --- Loop scene: highlight the phase closest to the viewport's vertical
// center as the reader scrolls, and let clicking a diagram node jump to (and
// activate) its phase. Progressive enhancement only - the adjacent
// .loop__phases <ol> is the always-visible, always-complete content; this
// keeps the sticky diagram's echo in sync and adds a shortcut while JS is
// available.
//
// Deliberately NOT IntersectionObserver: with six short phases, several can
// be simultaneously 100%-intersecting at once, and picking "highest ratio"
// among tied 1.0 values has no stable, predictable winner - it read as the
// active dot jumping around at random while scrolling, and racing visibly
// against the click handler's own scrollIntoView. A direct
// getBoundingClientRect() distance-to-center comparison has exactly one
// closest phase at any scroll position, so there is nothing to race.
//
// Safe to call again after a language swap replaces the loop section's DOM
// (tears down the previous listeners first, then re-queries fresh nodes).
function initLoopScene() {
  loopCleanup?.();

  const phases = Array.from(document.querySelectorAll('.loop__phase'));
  const diagram = document.querySelector('.loop__diagram');
  const nodes = document.querySelectorAll('.loop__diagram .loop__node');
  if (phases.length === 0 || !diagram) return;

  // The static diagram is decorative because no-JS visitors cannot activate
  // its nodes. Expose it as phase navigation only after the handlers exist,
  // avoiding dead focus targets in the progressive-enhancement path.
  diagram.removeAttribute('aria-hidden');
  diagram.setAttribute('role', 'group');
  diagram.setAttribute('aria-label', diagram.dataset.label);

  const phaseByName = new Map();
  phases.forEach((phase) => phaseByName.set(phase.dataset.phase, phase));

  function setActive(phase) {
    nodes.forEach((node) => {
      const isActive = node.dataset.phase === phase;
      node.classList.toggle('is-active', isActive);
      if (isActive) node.setAttribute('aria-current', 'step');
      else node.removeAttribute('aria-current');
    });
  }

  function updateActiveFromScroll() {
    const viewportCenter = window.innerHeight / 2;
    let closest = null;
    let closestDistance = Infinity;
    for (const phase of phases) {
      const rect = phase.getBoundingClientRect();
      const distance = Math.abs(rect.top + rect.height / 2 - viewportCenter);
      if (distance < closestDistance) {
        closestDistance = distance;
        closest = phase;
      }
    }
    if (closest) setActive(closest.dataset.phase);
  }

  let ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      updateActiveFromScroll();
      ticking = false;
    });
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  updateActiveFromScroll();

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const interactionHandlers = [];
  nodes.forEach((node) => {
    node.setAttribute('role', 'button');
    node.setAttribute('tabindex', '0');
    node.setAttribute('aria-label', node.dataset.label);

    const activate = () => {
      const target = phaseByName.get(node.dataset.phase);
      setActive(node.dataset.phase);
      target?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
    };
    const onKeydown = (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      activate();
    };
    node.addEventListener('click', activate);
    node.addEventListener('keydown', onKeydown);
    interactionHandlers.push([node, activate, onKeydown]);
  });

  loopCleanup = () => {
    window.removeEventListener('scroll', onScroll);
    window.removeEventListener('resize', onScroll);
    interactionHandlers.forEach(([node, activate, onKeydown]) => {
      node.removeEventListener('click', activate);
      node.removeEventListener('keydown', onKeydown);
    });
  };
}

// --- Reveal rows (integrations, evidence/tasks): CSS already reveals on
// hover/focus with no JS at all. This adds a persistent open/close toggle
// for touch, where ":hover" does not apply, and keeps aria-expanded correct
// for assistive tech. Safe to call again after a language swap - listeners
// attach to whatever `.reveal__trigger` elements exist at call time.
function initRevealRows() {
  document.querySelectorAll('.reveal__trigger').forEach((trigger) => {
    // Static HTML is expanded for the no-JS path. Once enhancement is
    // available, collapse each row before wiring the disclosure control.
    trigger.disabled = false;
    trigger.setAttribute('aria-expanded', 'false');
    trigger.addEventListener('click', () => {
      const row = trigger.closest('.reveal');
      const isOpen = row.classList.toggle('is-open');
      trigger.setAttribute('aria-expanded', String(isOpen));
    });
  });
}

// --- Hero figure: stop the looping figure once the hero is off screen.
// It restates the descriptor it sits next to, so once neither is visible it
// is spending frames on nothing. IntersectionObserver is the right tool here
// (unlike the loop scene above): the question is a genuine binary, is any
// part of the hero on screen, with no tie to break between candidates.
//
// Progressive enhancement only. Without this the animation simply keeps
// running, which is the pre-existing behavior, and prefers-reduced-motion
// still wins over both since the animation is only ever declared inside
// that query.
// Safe to call again after a language swap replaces the hero mark's DOM: the
// previous observer is disconnected first, otherwise every toggle would leave
// another live observer holding a reference to a detached SVG.
let heroFigureObserver;

function initHeroFigure() {
  heroFigureObserver?.disconnect();

  const hero = document.querySelector('.hero');
  // Scoped to the hero. The circuit diagram in section 03 carries the same
  // class now that the two figures swapped places, and pausing it whenever
  // the hero is off screen would freeze it exactly when it is being read.
  const figure = document.querySelector('.hero .hero__figure');
  if (!hero || !figure || typeof IntersectionObserver !== 'function') return;

  heroFigureObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        figure.classList.toggle('is-paused', !entry.isIntersecting);
      }
    },
    { threshold: 0 },
  );
  heroFigureObserver.observe(hero);
}

// --- Figure tooltips: every drawn object that means something names itself
// on hover, in whichever language the page is showing.
//
// Progressive enhancement, and deliberately pointer-only. The figures stay
// aria-hidden and out of the tab order: each one already has a written key
// beside it carrying the same content, so making 40 SVG shapes focusable
// would add 40 tab stops that tell a screen-reader user nothing new. The
// tooltip is a shortcut for people who can see the drawing, not the only
// place the information exists.
//
// The text lives in data-tip on the shape, inside the i18n block, so the
// Ukrainian template carries its own copy and no translation table is needed
// here. One shared tooltip element, moved and re-filled, rather than one per
// figure.
let tipCleanup;

// Set by initFigureTips. Lets another component change its own tip text and
// have an already-open tip redraw, without that component knowing where the
// tooltip element lives or how it is positioned. A no-op before the tips are
// bound, and after a language swap it points at the current binding.
let refreshTip = () => {};

function initFigureTips() {
  tipCleanup?.();

  const targets = Array.from(document.querySelectorAll('[data-tip]'));
  if (targets.length === 0) return;

  let tip = document.getElementById('figure-tip');
  if (!tip) {
    tip = document.createElement('div');
    tip.id = 'figure-tip';
    tip.className = 'figure-tip';
    tip.setAttribute('aria-hidden', 'true');
    document.body.append(tip);
  }

  let visible = false;
  let activeTarget = null;

  function hide() {
    if (!visible) return;
    visible = false;
    activeTarget = null;
    tip.classList.remove('is-visible');
  }

  function show(target) {
    activeTarget = target;
    tip.textContent = target.dataset.tip;
    tip.classList.add('is-visible');
    visible = true;

    // Measure after the text is in, then clamp to the viewport so a tip on a
    // shape at the edge of a figure does not hang off the page.
    const box = target.getBoundingClientRect();
    const tipBox = tip.getBoundingClientRect();
    const margin = 8;
    let left = box.left + box.width / 2 - tipBox.width / 2;
    left = Math.max(margin, Math.min(left, window.innerWidth - tipBox.width - margin));
    let top = box.top - tipBox.height - 10;
    if (top < margin) top = box.bottom + 10;

    tip.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
  }

  const handlers = [];
  targets.forEach((target) => {
    const onEnter = () => show(target);
    target.addEventListener('pointerenter', onEnter);
    target.addEventListener('pointerleave', hide);
    handlers.push([target, onEnter]);
  });

  window.addEventListener('scroll', hide, { passive: true });

  // Only redraws a tip that is already open on that exact element. A copy
  // button activated from the keyboard must not make a tooltip appear out of
  // nowhere just because its label changed.
  refreshTip = (target) => {
    if (visible && activeTarget === target) show(target);
  };

  tipCleanup = () => {
    hide();
    refreshTip = () => {};
    window.removeEventListener('scroll', hide);
    handlers.forEach(([target, onEnter]) => {
      target.removeEventListener('pointerenter', onEnter);
      target.removeEventListener('pointerleave', hide);
    });
  };
}

// --- Copy button on command blocks. Progressive enhancement: the button is
// hidden by CSS until .js is on, so a reader without a script sees the
// commands rather than a control that cannot work.
//
// The confirmation is the button itself changing, not a toast. Two labels
// ship as attributes so the swap is a class change and an aria-label, with
// nothing to construct at click time and nothing to translate here.
// navigator.clipboard is unavailable on an insecure origin and can be denied
// by permission policy, and in both cases it rejects rather than degrading.
// The selection-based path still works there, so a button that looks like it
// copies actually copies instead of silently doing nothing.
async function writeClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // fall through
  }

  const staging = document.createElement('textarea');
  staging.value = text;
  staging.setAttribute('readonly', '');
  staging.style.cssText = 'position:fixed;top:0;left:-9999px;opacity:0';
  document.body.append(staging);
  staging.select();
  let copied = false;
  try {
    copied = document.execCommand('copy');
  } catch {
    copied = false;
  }
  staging.remove();
  return copied;
}

function initCopyButtons() {
  document.querySelectorAll('.code-block__copy').forEach((button) => {
    const block = button.closest('.code-block');
    const code = block?.querySelector('code');
    if (!code) return;

    let resetTimer;
    button.addEventListener('click', async () => {
      // Confirm nothing unless something was actually copied. A check mark
      // over an empty clipboard is worse than no button.
      if (!(await writeClipboard(code.innerText.trim()))) return;
      clearTimeout(resetTimer);
      button.classList.add('is-copied');
      // aria-label and data-tip carry the same label to two audiences, so
      // they move together. The tooltip is the pointer user's only written
      // confirmation - the icon swap alone does not name what happened.
      button.setAttribute('aria-label', button.dataset.copiedLabel);
      button.dataset.tip = button.dataset.copiedLabel;
      refreshTip(button);
      resetTimer = setTimeout(() => {
        button.classList.remove('is-copied');
        button.setAttribute('aria-label', button.dataset.copyLabel);
        button.dataset.tip = button.dataset.copyLabel;
        refreshTip(button);
      }, 2000);
    });
  });
}

// --- Install tabs: one platform panel at a time on the quickstart screen.
// Progressive enhancement, and the static HTML is the complete version: all
// three panels render with their own headings and the tab strip is not drawn
// at all until .js is on, so a reader without a script gets every command
// rather than one strip that cannot switch.
//
// Full tablist keyboard semantics rather than three buttons: arrows move
// between tabs, Home/End jump to the ends, and only the selected tab is a tab
// stop, which is what a screen-reader user is told to expect the moment the
// markup says role="tablist".
let installTabsCleanup;

function initInstallTabs() {
  installTabsCleanup?.();

  const lists = Array.from(document.querySelectorAll('.install__tablist'));
  if (lists.length === 0) return;

  const handlers = [];

  lists.forEach((list) => {
    const tabs = Array.from(list.querySelectorAll('.install__tab'));
    if (tabs.length === 0) return;

    const select = (tab, { focus = false } = {}) => {
      tabs.forEach((other) => {
        const isActive = other === tab;
        other.classList.toggle('is-active', isActive);
        other.setAttribute('aria-selected', String(isActive));
        other.tabIndex = isActive ? 0 : -1;
        const panel = document.getElementById(other.getAttribute('aria-controls'));
        panel?.classList.toggle('is-active', isActive);
      });
      if (focus) tab.focus();
    };

    tabs.forEach((tab, index) => {
      const onClick = () => select(tab);
      const onKeydown = (event) => {
        const step =
          event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
        let next = null;
        if (step !== 0) next = tabs[(index + step + tabs.length) % tabs.length];
        else if (event.key === 'Home') next = tabs[0];
        else if (event.key === 'End') next = tabs[tabs.length - 1];
        if (!next) return;
        event.preventDefault();
        select(next, { focus: true });
      };
      tab.addEventListener('click', onClick);
      tab.addEventListener('keydown', onKeydown);
      handlers.push([tab, onClick, onKeydown]);
    });

    // Re-assert the markup's own default through the same path a click takes,
    // so the roving tabindex is correct before anyone touches it.
    select(tabs.find((tab) => tab.classList.contains('is-active')) ?? tabs[0]);
  });

  installTabsCleanup = () => {
    handlers.forEach(([tab, onClick, onKeydown]) => {
      tab.removeEventListener('click', onClick);
      tab.removeEventListener('keydown', onKeydown);
    });
  };
}

const REINIT_HANDLERS = {
  loop: initLoopScene,
  reveal: initRevealRows,
  hero: initHeroFigure,
  install: initInstallTabs,
};

// --- Language toggle: English is the static, always-present default (so a
// no-JS visitor gets the primary language, not a degraded state). Each
// `.i18n-block` caches its own original (English) HTML once; switching to
// Ukrainian clones the matching <template>; switching back restores the
// cached English HTML. No cookie/localStorage - the choice is session-only,
// keeping the zero-storage state this site already verifies (D-08).
function initLanguageToggle() {
  const toggle = document.getElementById('lang-toggle');
  const skipLink = document.querySelector('.skip-link');
  const blocks = document.querySelectorAll('.i18n-block');
  if (!toggle || blocks.length === 0) return;

  // The language switch has no truthful behavior without JavaScript, so it
  // is hidden in static HTML and exposed only after its handler can run.
  toggle.hidden = false;

  const englishHtml = new Map();
  const ukrainianTemplate = new Map();
  blocks.forEach((block) => englishHtml.set(block.dataset.i18nId, block.innerHTML));
  document.querySelectorAll('#i18n-templates template').forEach((tpl) => {
    ukrainianTemplate.set(tpl.dataset.i18nId, tpl);
  });

  let lang = 'en';

  function applyReinit() {
    const kinds = new Set();
    blocks.forEach((block) => {
      if (block.dataset.i18nReinit) kinds.add(block.dataset.i18nReinit);
    });
    kinds.forEach((kind) => REINIT_HANDLERS[kind]?.());
    // Unconditional: tooltip text and the copy button's own labels live
    // inside the swapped markup, so both need rebinding after a language
    // change, not only the blocks that declare a reinit handler.
    initFigureTips();
    initCopyButtons();
  }

  function setLanguage(next) {
    lang = next;
    document.documentElement.lang = lang;
    blocks.forEach((block) => {
      const id = block.dataset.i18nId;
      if (lang === 'uk') {
        const tpl = ukrainianTemplate.get(id);
        if (tpl) block.innerHTML = tpl.innerHTML;
      } else {
        block.innerHTML = englishHtml.get(id) ?? block.innerHTML;
      }
    });
    toggle.setAttribute(
      'aria-label',
      lang === 'en' ? toggle.dataset.labelEn : toggle.dataset.labelUk,
    );
    toggle.classList.toggle('is-uk', lang === 'uk');
    if (skipLink) {
      skipLink.textContent = lang === 'uk' ? skipLink.dataset.labelUk : skipLink.dataset.labelEn;
    }
    document.title = lang === 'uk' ? toggle.dataset.titleUk : toggle.dataset.titleEn;
    applyReinit();
  }

  toggle.addEventListener('click', () => setLanguage(lang === 'en' ? 'uk' : 'en'));
}

initLoopScene();
initRevealRows();
initLanguageToggle();
initHeroFigure();
initInstallTabs();
initFigureTips();
initCopyButtons();
