const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');
const source = readFileSync(join(__dirname, 'own-projects.js'), 'utf8');

function page(matches, { legacy = false, missing = false, noMedia = false } = {}) {
  const block = {};
  const moves = [];
  let listener;
  const early = { nextElementSibling: block };
  const late = { nextElementSibling: null };
  for (const marker of [early, late]) {
    marker.insertAdjacentElement = (where, node) => {
      assert.equal(where, 'afterend');
      assert.equal(node, block);
      early.nextElementSibling = late.nextElementSibling = null;
      marker.nextElementSibling = block;
      moves.push(marker);
    };
  }
  const media = { matches };
  if (legacy) media.addListener = fn => { listener = fn; };
  else media.addEventListener = (event, fn) => { assert.equal(event, 'change'); listener = fn; };
  const context = {
    document: {
      querySelector: selector => { assert.equal(selector, '[data-own-projects]'); return missing ? null : block; },
      getElementById: id => id === 'projects-mobile-position' ? early : late,
    },
    window: noMedia ? {} : { matchMedia: query => { assert.equal(query, '(max-width: 48rem)'); return media; } },
  };
  vm.runInNewContext(source, context);
  return { block, moves, early, late, resize: matches => { media.matches = matches; listener(); } };
}

test('mobile keeps the one pair at the early HTML position without moving it', () => {
  const p = page(true);
  assert.equal(p.early.nextElementSibling, p.block);
  assert.equal(p.moves.length, 0);
});
test('desktop restores the existing end position', () => {
  const p = page(false);
  assert.equal(p.late.nextElementSibling, p.block);
  assert.equal(p.moves.length, 1);
});
test('resize moves rather than duplicates; repeated change is a no-op', () => {
  const p = page(false);
  p.resize(true); p.resize(true);
  assert.equal(p.early.nextElementSibling, p.block);
  assert.equal(p.moves.length, 2);
  p.resize(false);
  assert.equal(p.late.nextElementSibling, p.block);
  assert.equal(p.moves.length, 3);
});
test('older matchMedia listeners work too', () => {
  const p = page(false, { legacy: true });
  p.resize(true);
  assert.equal(p.early.nextElementSibling, p.block);
});
test('missing block or unsupported matchMedia leaves the page alone', () => {
  assert.equal(page(true, { missing: true }).moves.length, 0);
  assert.equal(page(false, { noMedia: true }).moves.length, 0);
});
test('placement is local, without tracking, scroll listeners, timers or clones', () => {
  for (const forbidden of ['fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'cookie', 'cloneNode', 'setInterval', 'setTimeout', "'scroll'"]) {
    assert.ok(!source.includes(forbidden), forbidden);
  }
});
