const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function element(text = '') {
  const attrs = new Map();
  const classes = new Set();
  return {textContent: text, value: '', hidden: false, dataset: {}, events: {},
    classList: {remove: x => classes.delete(x), toggle: (x, on) => on ? classes.add(x) : classes.delete(x)},
    setAttribute: (key, value) => attrs.set(key, value), getAttribute: key => attrs.get(key),
    addEventListener(name, fn) { this.events[name] = fn; }, focus() { this.focused = true; }};
}
function page() {
  const ids = Object.fromEntries(['site-nav','archiveSearch','archiveSource','archiveReset','archiveSummary','currentYear'].map(id => [id, element()]));
  ids.archiveSource.value = 'all';
  const toggle = element(), empty = element();
  const cards = [element('Navegación verificada Reuters'), element('Aviso marítimo UKMTO')];
  cards[0].dataset.source = 'Reuters'; cards[1].dataset.source = 'UKMTO';
  const document = {documentElement: {lang:'es'}, events:{}, getElementById:id=>ids[id],
    querySelector:selector=>selector==='.nav-toggle'?toggle:empty,
    querySelectorAll:()=>cards, addEventListener(name, fn) { this.events[name]=fn; }};
  vm.runInNewContext(fs.readFileSync(__dirname+'/public-ui.js','utf8'), {document, Date, URL, location:{href:'https://example.org/'},navigator:{}});
  return {ids, toggle, empty, cards};
}
test('archive filters ignore accents and can reset without requesting data', () => {
  const {ids,cards,empty}=page();
  ids.archiveSearch.value='navegacion'; ids.archiveSearch.events.input();
  assert.equal(cards[0].hidden,false); assert.equal(cards[1].hidden,true);
  assert.equal(ids.archiveSummary.textContent,'1 resultados');
  ids.archiveSource.value='UKMTO'; ids.archiveSource.events.change();
  assert.equal(empty.hidden,false);
  ids.archiveReset.events.click();
  assert.equal(cards.some(x=>x.hidden),false); assert.equal(empty.hidden,true);
  assert.equal(ids.archiveSearch.focused,true);
});
test('menu state follows its control and closes on navigation', () => {
  const {ids,toggle}=page();
  toggle.events.click(); assert.equal(toggle.getAttribute('aria-expanded'),'true');
  ids['site-nav'].events.click({target:{closest:()=>({})}});
  assert.equal(toggle.getAttribute('aria-expanded'),'false');
});
test('embed copy retains its button after the asynchronous click finishes', async () => {
  const form=element(), frame=element(), code=element(), button=element();
  frame.style={};
  const nodes={'[data-embed-form]':form,'[data-embed-preview]':frame,'[data-embed-code]':code,'[data-copy-embed]':button};
  let restore;
  const document={documentElement:{lang:'es'},querySelector:key=>nodes[key]};
  vm.runInNewContext(fs.readFileSync(__dirname+'/embed.js','utf8'), {
    document, FormData:class {get(key){return {lang:'es',theme:'light',compact:'0'}[key];}},
    navigator:{clipboard:{writeText:async()=>{}}},setTimeout:fn=>{restore=fn;}
  });
  const event={currentTarget:button};
  const finished=button.events.click(event);
  event.currentTarget=null;
  await finished;
  assert.equal(button.textContent,'Copiado');
  restore(); assert.equal(button.textContent,'Copiar código');
});
