/* Move the one existing pair, never clone it or watch scrolling. No persistence,
   tracking, requests or timers. Without JS the mobile-first placement remains. */
(() => {
  'use strict';
  const block = document.querySelector('[data-own-projects]');
  const early = document.getElementById('projects-mobile-position');
  const late = document.getElementById('projects-desktop-position');
  if (!block || !early || !late || typeof window.matchMedia !== 'function') return;
  const mobile = window.matchMedia('(max-width: 48rem)');
  function place() {
    const marker = mobile.matches ? early : late;
    if (marker.nextElementSibling !== block) marker.insertAdjacentElement('afterend', block);
  }
  place();
  if (typeof mobile.addEventListener === 'function') mobile.addEventListener('change', place);
  else if (typeof mobile.addListener === 'function') mobile.addListener(place);
})();
