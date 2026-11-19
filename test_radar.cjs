const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function setup(lang='es',hasFrame=true){
 const events={},timers=new Map(),scripts=[];
 const button={disabled:false,textContent:'Open'};
 const frame={classList:{add(){}},style:{},events:{},addEventListener(k,f){this.events[k]=f}};
 const container={dataset:{},querySelector:()=>hasFrame?frame:null,insertBefore:s=>scripts.push(s)};
 const placeholder={hidden:false},toolbar={hidden:true},status={textContent:''};
 const nodes={marineMapContainer:container,marineMapPlaceholder:placeholder,marineMapToolbar:toolbar,marineMapStatus:status};
 const document={documentElement:{lang},addEventListener:(k,f)=>events[k]=f,getElementById:k=>nodes[k],
  createElement:()=>({events:{},addEventListener(k,f){this.events[k]=f},remove(){this.removed=true}})};
 const window={setTimeout:(fn,ms)=>{timers.set(1,{fn,ms});return 1},clearTimeout:id=>timers.delete(id)};
 vm.runInNewContext(fs.readFileSync(__dirname+'/radar-map.js','utf8'),{document,window});
 const click=()=>events.click({target:{closest:()=>button}});
 return {button,frame,container,placeholder,toolbar,status,scripts,timers,click};
}
test('radar never contacts the supplier before reader action and blocks duplicate clicks',()=>{
 const x=setup();assert.equal(x.scripts.length,0);x.click();x.click();
 assert.equal(x.scripts.length,1);assert.equal(x.container.dataset.aisLoading,'true');
});
test('iframe insertion never claims successful AIS availability, including an HTTP error document',()=>{
 const x=setup();x.click();x.scripts[0].events.load();
 assert.equal(x.container.dataset.aisInserted,'true');
 assert.equal(x.container.dataset.aisLoaded,undefined);
 assert.equal(x.placeholder.hidden,true);assert.equal(x.toolbar.hidden,false);
 assert.match(x.status.textContent,/Si no aparece el mapa/);assert.doesNotMatch(x.status.textContent,/Radar AIS cargado/);
 assert.equal(x.timers.size,0);x.click();assert.equal(x.scripts.length,1);
});
test('supplier script errors allow retry and retain the alternative link',()=>{
 const x=setup();x.click();x.scripts[0].events.error();
 assert.equal(x.button.disabled,false);assert.equal(x.placeholder.hidden,false);
 assert.equal(x.container.dataset.aisLoading,'false');assert.match(x.status.textContent,/MarineTraffic/);
 x.click();assert.equal(x.scripts.length,2);
});
test('missing iframe does not produce a success state',()=>{
 const x=setup('es',false);x.click();x.scripts[0].events.load();
 assert.equal(x.container.dataset.aisInserted,undefined);assert.equal(x.placeholder.hidden,false);
 assert.match(x.status.textContent,/No se pudo cargar/);
});
test('hanging supplier times out and a late load cannot overwrite the error',()=>{
 const x=setup();x.click();const timer=x.timers.get(1);assert.equal(timer.ms,15000);
 timer.fn();const message=x.status.textContent;x.scripts[0].events.load();
 assert.equal(x.status.textContent,message);assert.equal(x.container.dataset.aisInserted,undefined);
 assert.equal(x.button.disabled,false);
});
test('English interface states the same availability limitation',()=>{
 const x=setup('en');x.click();x.scripts[0].events.load();
 assert.match(x.status.textContent,/If the map is missing/);assert.doesNotMatch(x.status.textContent,/AIS radar loaded/);
});
