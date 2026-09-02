/* One existing pair, no network or tracking. The session flag only remembers
   this site's mobile promotion; unavailable storage leaves the in-flow fallback. */
(() => {
  'use strict';
  const block = document.querySelector('[data-own-projects]');
  const early = document.getElementById('projects-mobile-position');
  const late = document.getElementById('projects-desktop-position');
  if (!block || !early || !late || typeof window.matchMedia !== 'function') return;
  const close = block.querySelector('.own-projects__close');
  const intro = early.previousElementSibling;
  const mobile = window.matchMedia('(max-width: 48rem)');
  const key = 'own-projects-mobile-seen-v1';
  let storage, seen = false, open = false, waiting = false, spacer;
  try {
    storage = window.sessionStorage;
    seen = storage.getItem(key) === '1';
  } catch (_) { storage = null; }

  function move(marker) {
    if (marker.nextElementSibling !== block) marker.insertAdjacentElement('afterend', block);
  }
  function stopWaiting() {
    if (waiting) window.removeEventListener('scroll', progress);
    waiting = false;
  }
  function clearPopup() {
    open = false;
    block.classList.remove('own-projects--popup');
    block.style.visibility = '';
    if (close) close.hidden = true;
    if (spacer) { spacer.remove(); spacer = null; }
  }
  function inline() {
    stopWaiting(); clearPopup(); move(early); block.hidden = false;
  }
  function viewportHeight() {
    return Math.min(window.innerHeight, window.visualViewport?.height || window.innerHeight);
  }
  function canFloat() {
    return close && intro && storage && viewportHeight() >= 512 &&
      (!window.visualViewport || window.visualViewport.scale <= 1.1) &&
      typeof window.getComputedStyle === 'function';
  }
  function fits() {
    const bounds = block.getBoundingClientRect();
    const style = window.getComputedStyle(block);
    return style.position === 'fixed' && bounds.height > 0 &&
      bounds.height + Math.max(24, (parseFloat(style.bottom) || 0) + 8) <= viewportHeight() * .30 &&
      bounds.width <= window.innerWidth;
  }
  function readingSpace() {
    return block.getBoundingClientRect().height +
      Math.max(24, (parseFloat(window.getComputedStyle(block).bottom) || 0) + 8);
  }
  function dismiss() {
    const hadFocus = block.contains(document.activeElement);
    stopWaiting(); clearPopup(); block.hidden = true; move(late);
    // Never steal focus on opening; return a keyboard closer to its reading point.
    if (hadFocus && intro) {
      const previous = intro.getAttribute('tabindex');
      intro.setAttribute('tabindex', '-1'); intro.focus({ preventScroll: true });
      if (previous === null) intro.removeAttribute('tabindex');
      else intro.setAttribute('tabindex', previous);
    }
  }
  function progress() {
    if (!waiting || !mobile.matches || document.hidden || document.fullscreenElement) return;
    if (document.activeElement?.closest('input, textarea, select, [contenteditable="true"]') ||
        document.querySelector('dialog[open], [aria-modal="true"], [aria-expanded="true"]')) return;
    const height = viewportHeight();
    if (window.scrollY < height * .5 || intro.getBoundingClientRect().bottom > height * .75) return;
    stopWaiting();
    block.classList.add('own-projects--popup');
    block.style.visibility = 'hidden';
    document.body.appendChild(block); block.hidden = false; close.hidden = false;
    if (!canFloat() || !fits()) { inline(); return; }
    // Mark at the first display, not only on closing: navigation won't repeat it.
    try { storage.setItem(key, '1'); }
    catch (_) { storage = null; inline(); return; }
    seen = true; open = true; block.style.visibility = '';
    // Keeps the very last lines/links reachable above the panel without a scroll lock.
    spacer = document.createElement('div');
    spacer.setAttribute('aria-hidden', 'true');
    spacer.style.height = readingSpace() + 'px';
    document.body.appendChild(spacer);
  }
  function sync() {
    stopWaiting();
    if (!mobile.matches) {
      clearPopup(); move(late); block.hidden = false; return;
    }
    if (open) {
      if (!canFloat() || !fits()) dismiss();
      else spacer.style.height = readingSpace() + 'px';
      return;
    }
    clearPopup();
    if (seen) { block.hidden = true; move(late); return; }
    if (!canFloat()) { inline(); return; }
    move(late); block.hidden = true;
    waiting = true;
    window.addEventListener('scroll', progress, { passive: true });
  }
  if (close) close.addEventListener('click', dismiss);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && open) dismiss();
  });
  document.addEventListener('focusin', () => {
    if (open && document.activeElement?.closest('input, textarea, select, [contenteditable="true"]')) dismiss();
  });
  window.addEventListener('resize', sync);
  window.visualViewport?.addEventListener('resize', sync);
  window.addEventListener('pageshow', event => {
    if (!event.persisted) return;
    try { seen = storage?.getItem(key) === '1' || seen; } catch (_) { storage = null; }
    clearPopup(); sync();
  });
  if (typeof mobile.addEventListener === 'function') mobile.addEventListener('change', sync);
  else if (typeof mobile.addListener === 'function') mobile.addListener(sync);
  sync();
})();
