const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');
const source = readFileSync(join(__dirname, 'own-projects.js'), 'utf8');
const KEY = 'own-projects-mobile-seen-v1';

function events() {
  const listeners = new Map();
  return {
    listeners,
    addEventListener(type, fn, options) {
      if (!listeners.has(type)) listeners.set(type, new Set());
      listeners.get(type).add(fn);
      if (type === 'scroll') assert.equal(options.passive, true);
    },
    removeEventListener(type, fn) { listeners.get(type)?.delete(fn); },
    emit(type, event = {}) { for (const fn of [...(listeners.get(type) || [])]) fn(event); },
  };
}
function page({ mobile = true, seen = false, data = new Map(), height = 800, panelHeight = 165,
                readError = false, writeError = false, noMedia = false, noClose = false,
                missing = false, legacy = false, position = 'fixed', bottom = '8px' } = {}) {
  if (seen) data.set(KEY, '1');
  const css = new Set();
  const close = { ...events(), hidden: true, closest: () => null };
  const attrs = new Map();
  let introBottom = 1200, focusCalls = 0, doc;
  const intro = {
    getBoundingClientRect: () => ({ bottom: introBottom }),
    getAttribute: name => attrs.get(name) ?? null,
    setAttribute: (name, value) => attrs.set(name, value),
    removeAttribute: name => attrs.delete(name),
    focus: options => { assert.equal(options.preventScroll, true); focusCalls++; doc.activeElement = intro; },
    closest: () => null,
  };
  const block = {
    hidden: false, style: {},
    classList: { add: name => css.add(name), remove: name => css.delete(name) },
    querySelector: selector => { assert.equal(selector, '.own-projects__close'); return noClose ? null : close; },
    getBoundingClientRect: () => ({ height: panelHeight, width: 374 }),
    contains: element => element === close || element === block,
  };
  const early = { previousElementSibling: intro, nextElementSibling: block };
  const late = { nextElementSibling: null };
  const children = new Set();
  const detach = () => { early.nextElementSibling = late.nextElementSibling = null; children.delete(block); };
  for (const marker of [early, late]) {
    marker.insertAdjacentElement = (where, node) => {
      assert.equal(where, 'afterend'); assert.equal(node, block);
      detach(); marker.nextElementSibling = block;
    };
  }
  doc = {
    ...events(), hidden: false, fullscreenElement: null, activeElement: intro, busy: false,
    querySelector: selector => selector === '[data-own-projects]' ? (missing ? null : block) : (doc.busy ? {} : null),
    getElementById: id => id === 'projects-mobile-position' ? early : late,
    body: { appendChild(node) { if (node === block) detach(); children.add(node); } },
    createElement(tag) {
      assert.equal(tag, 'div');
      const node = { style: {}, setAttribute() {}, remove() { children.delete(node); } };
      return node;
    },
  };
  const media = { matches: mobile, ...events() };
  if (legacy) { delete media.addEventListener; media.addListener = fn => media.listeners.set('change', new Set([fn])); }
  const win = {
    ...events(), innerHeight: height, innerWidth: 390, scrollY: 0,
    visualViewport: { ...events(), height, scale: 1 },
    getComputedStyle: () => ({ position, bottom }),
    sessionStorage: {
      getItem(key) { assert.equal(key, KEY); if (readError) throw Error('blocked'); return data.get(key) ?? null; },
      setItem(key, value) { assert.equal(key, KEY); if (writeError) throw Error('quota'); data.set(key, value); },
    },
  };
  if (!noMedia) win.matchMedia = query => { assert.equal(query, '(max-width: 48rem)'); return media; };
  vm.runInNewContext(source, { document: doc, window: win });
  return {
    block, close, early, late, doc, win, data, children, css,
    get focusCalls() { return focusCalls; },
    get scrollListeners() { return win.listeners.get('scroll')?.size || 0; },
    scroll(y = 650, bottom = 450) { win.scrollY = y; introBottom = bottom; win.emit('scroll'); },
    resize(matches) { media.matches = matches; media.emit('change'); },
    visiblePopup() { return css.has('own-projects--popup') && !block.hidden; },
  };
}

test('mobile waits for reading progress, never displays immediately', () => {
  const p = page();
  assert.equal(p.block.hidden, true); assert.equal(p.scrollListeners, 1);
  p.scroll(0, 400); assert.equal(p.visiblePopup(), false);
  p.scroll(650, 900); assert.equal(p.visiblePopup(), false);
  p.scroll(); assert.equal(p.visiblePopup(), true);
  assert.equal(p.close.hidden, false);
  assert.equal(p.focusCalls, 0);
  assert.equal(p.scrollListeners, 0);
  assert.equal(p.data.get(KEY), '1');
  assert.equal(p.children.size, 2); // same pair plus bottom reading space
  p.scroll(); assert.equal(p.children.size, 2);
});
test('close is immediate, removes popup/space and does not reopen on scroll or resize', () => {
  const p = page(); p.scroll();
  p.doc.activeElement = p.close;
  p.close.emit('click');
  assert.equal(p.block.hidden, true); assert.equal(p.children.size, 0);
  assert.equal(p.focusCalls, 1);
  p.scroll(); p.win.emit('resize');
  assert.equal(p.visiblePopup(), false); assert.equal(p.block.hidden, true);
});
test('Escape closes without stealing focus from the reading area', () => {
  const p = page(); p.scroll(); p.doc.emit('keydown', { key: 'Escape' });
  assert.equal(p.block.hidden, true); assert.equal(p.focusCalls, 0);
});
test('session flag prevents repeats on another page or language, even without closing', () => {
  const first = page(); first.scroll();
  const next = page({ data: first.data }); next.scroll();
  assert.equal(next.block.hidden, true); assert.equal(next.scrollListeners, 0);
  assert.equal(next.visiblePopup(), false);
});
test('new visit can display the popup again', () => {
  const p = page(); p.scroll(); assert.equal(p.visiblePopup(), true);
});
test('desktop placement is unchanged, including after a dismissed mobile popup', () => {
  const p = page({ mobile: false, seen: true });
  assert.equal(p.late.nextElementSibling, p.block); assert.equal(p.block.hidden, false);
  assert.equal(p.close.hidden, true); assert.equal(p.scrollListeners, 0);
  p.resize(true); assert.equal(p.block.hidden, true);
  p.resize(false); assert.equal(p.block.hidden, false);
});
test('resizing moves the same pair and never creates duplicate promotions', () => {
  const p = page({ mobile: false }); p.resize(true); p.scroll();
  assert.equal(p.visiblePopup(), true);
  p.resize(false);
  assert.equal(p.children.size, 0); assert.equal(p.late.nextElementSibling, p.block);
  p.resize(true);
  assert.equal(p.block.hidden, true); assert.equal(p.visiblePopup(), false);
});
test('legacy matchMedia listeners still work', () => {
  const p = page({ mobile: false, legacy: true }); p.resize(true); p.scroll();
  assert.equal(p.visiblePopup(), true);
});
test('read/write storage failures keep the inline fallback, not repeated popups', () => {
  for (const options of [{ readError: true }, { writeError: true }]) {
    const p = page(options); p.scroll();
    assert.equal(p.visiblePopup(), false); assert.equal(p.block.hidden, false);
    assert.equal(p.early.nextElementSibling, p.block); assert.equal(p.close.hidden, true);
    assert.equal(p.children.size, 0); assert.equal(p.scrollListeners, 0);
  }
});
test('missing block or unsupported matchMedia leaves the original HTML alone', () => {
  for (const options of [{ missing: true }, { noMedia: true }]) {
    const p = page(options);
    assert.equal(p.early.nextElementSibling, p.block); assert.equal(p.block.hidden, false);
  }
});
test('missing close button cannot enable a popup', () => {
  const p = page({ noClose: true }); p.scroll();
  assert.equal(p.early.nextElementSibling, p.block); assert.equal(p.block.hidden, false);
});
test('short screens and enlarged panels use the inline fallback', () => {
  for (const options of [{ height: 450 }, { panelHeight: 300 }, { position: 'static' }]) {
    const p = page(options); p.scroll();
    assert.equal(p.visiblePopup(), false); assert.equal(p.block.hidden, false);
    assert.equal(p.early.nextElementSibling, p.block);
    assert.equal(p.data.has(KEY), false);
  }
});
test('popup and safe-area allowance fit at most 30 percent of the visible screen', () => {
  const fit = page({ height: 667, panelHeight: 175 }); fit.scroll();
  assert.equal(fit.visiblePopup(), true);
  const large = page({ height: 667, panelHeight: 177 }); large.scroll();
  assert.equal(large.visiblePopup(), false);
});
test('opening the keyboard or pinch zoom dismisses an existing popup', () => {
  for (const change of [v => { v.height = 350; }, v => { v.scale = 2; }]) {
    const p = page(); p.scroll(); change(p.win.visualViewport);
    p.win.visualViewport.emit('resize');
    assert.equal(p.block.hidden, true); assert.equal(p.children.size, 0);
  }
});
test('safe-area inset counts toward the size cap and bottom reading space', () => {
  const p = page({ bottom: '42px' }); p.scroll();
  assert.equal(p.visiblePopup(), true);
  assert.ok([...p.children].some(node => node !== p.block && node.style.height === '215px'));
  const small = page({ height: 667, bottom: '42px' }); small.scroll();
  assert.equal(small.visiblePopup(), false);
});
test('focusing an editing field closes the popup even with a tall viewport', () => {
  const p = page(); p.scroll();
  p.doc.activeElement = { closest: () => ({}) }; p.doc.emit('focusin');
  assert.equal(p.block.hidden, true); assert.equal(p.focusCalls, 0);
});
test('does not open over a menu, dialog, editing field, hidden page or fullscreen', () => {
  for (const condition of ['busy', 'hidden', 'fullscreen', 'editing']) {
    const p = page();
    if (condition === 'busy') p.doc.busy = true;
    if (condition === 'hidden') p.doc.hidden = true;
    if (condition === 'fullscreen') p.doc.fullscreenElement = {};
    if (condition === 'editing') p.doc.activeElement = { closest: () => ({}) };
    p.scroll();
    assert.equal(p.visiblePopup(), false); assert.equal(p.data.has(KEY), false);
  }
});
test('back/forward cache cannot redisplay the already seen popup', () => {
  const p = page(); p.scroll();
  p.win.emit('pageshow', { persisted: true }); p.scroll();
  assert.equal(p.block.hidden, true); assert.equal(p.children.size, 0);
});
test('plain resize while open preserves the popup and updates bottom reading space', () => {
  const p = page(); p.scroll(); p.win.emit('resize');
  assert.equal(p.visiblePopup(), true); assert.equal(p.children.size, 2);
});
test('local preference only: no tracking, requests, timers, clones, modal or scroll lock', () => {
  for (const forbidden of ['fetch(', 'XMLHttpRequest', 'localStorage', 'document.cookie', 'cloneNode',
                            'setInterval', 'setTimeout', 'preventDefault(', 'showModal(', 'overflow']) {
    assert.ok(!source.includes(forbidden), forbidden);
  }
});
