import './styles/tokens.css';
import './styles/base.css';
import './styles/hero.css';
import './styles/sections.css';
import './styles/loop.css';
import './styles/integrations.css';
import './styles/content.css';
import './styles/reveal.css';
import './styles/motion.css';
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

const REINIT_HANDLERS = {
  loop: initLoopScene,
  reveal: initRevealRows,
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
