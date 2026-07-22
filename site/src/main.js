import './styles/tokens.css';
import './styles/base.css';
import './styles/hero.css';
import './styles/sections.css';
import './styles/loop.css';
import './styles/integrations.css';
import './styles/reveal.css';
import './styles/motion.css';

// The `eif:deploy-status` meta tag is injected at build time by the
// eif-deploy-status Vite plugin (vite.config.js), so it is statically
// verifiable in dist/index.html without running this script.

// --- Loop scene: highlight the phase nearest the viewport center as the
// reader scrolls. Progressive enhancement only - the adjacent .loop__phases
// <ol> is the always-visible, always-complete content; this just keeps the
// sticky diagram's echo in sync while JS is available.
function initLoopScene() {
  const phases = document.querySelectorAll('.loop__phase');
  const nodes = document.querySelectorAll('.loop__diagram .loop__node');
  const statusPhase = document.querySelector('.loop__status-phase');
  if (phases.length === 0 || !('IntersectionObserver' in window)) return;

  const nodeByPhase = new Map();
  nodes.forEach((node) => nodeByPhase.set(node.dataset.phase, node));

  function setActive(phase) {
    nodes.forEach((node) => node.classList.toggle('is-active', node.dataset.phase === phase));
    if (statusPhase) statusPhase.textContent = phase.charAt(0).toUpperCase() + phase.slice(1);
  }

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) setActive(visible.target.dataset.phase);
    },
    { rootMargin: '-40% 0px -40% 0px', threshold: [0, 0.5, 1] },
  );

  phases.forEach((phase) => observer.observe(phase));
}

// --- Reveal rows (integrations now, task/evidence rows reuse this in a
// later session): CSS already reveals on hover/focus with no JS at all.
// This adds a persistent open/close toggle for touch, where ":hover" does
// not apply, and keeps aria-expanded correct for assistive tech.
function initRevealRows() {
  document.querySelectorAll('.reveal__trigger').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      const row = trigger.closest('.reveal');
      const isOpen = row.classList.toggle('is-open');
      trigger.setAttribute('aria-expanded', String(isOpen));
    });
  });
}

initLoopScene();
initRevealRows();
