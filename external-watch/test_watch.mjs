import test from 'node:test';
import assert from 'node:assert/strict';
import {parse, probe, BASE, PAGES, textResponse} from './snapshot.mjs';
import {Coordinator} from './coordinator.mjs';
import {GitHub, REPO, REPO_ID, jwt} from './github.mjs';

const NOW = Date.parse('2026-11-20T06:00:00Z');
const iso = n => new Date(n).toISOString().replace('.000Z', 'Z');
const ID = 'a'.repeat(24), COMMIT = 'b'.repeat(40);
function xml(age = 90, overrides = {}) {
  const fields = {assessment_id: ID, source_commit: COMMIT, verified_at: iso(NOW-age*60000), brief_assessment_id: ID,
    brief_source_checked_at: iso(NOW-age*60000), journal_edition_at: iso(NOW-60*60000), journal_checked_at: iso(NOW-10*60000), journal_check_outcome: 'not_due', ...overrides};
  return '<publication version="1" engine="operational-intelligence-v7">' + Object.entries(fields).map(([k,v]) => `<${k}>${v}</${k}>`).join('') + '</publication>';
}
class Storage {
  data = new Map(); tail = Promise.resolve();
  async get(k) {return structuredClone(this.data.get(k));}
  async put(k,v) {this.data.set(k, structuredClone(v));}
  async delete(k) {this.data.delete(k);}
  transaction(fn) {const p = this.tail.then(() => fn(this)); this.tail = p.catch(() => {}); return p;}
}
const key = await crypto.subtle.generateKey({name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256', modulusLength: 2048, publicExponent: new Uint8Array([1,0,1])}, true, ['sign','verify']);
const der = new Uint8Array(await crypto.subtle.exportKey('pkcs8', key.privateKey));
const PEM = '-----BEGIN PRIVATE KEY-----\n' + btoa(String.fromCharCode(...der)) + '\n-----END PRIVATE KEY-----';
function harness({age = 90, env = {}, changed = {}, active = false, recent = false, dispatchThrows = false, grantPatch = {}} = {}) {
  const store = new Storage(), calls = [];
  let clock = NOW;
  const body = xml(age, changed);
  const fetcher = async (url, init = {}) => {
    url = String(url); calls.push({url, ...init});
    if (url.startsWith(BASE)) return new Response(url.endsWith('.xml') ? body : `<meta name="ormuz-assessment" content="${ID}">`);
    if (url === 'https://ops.example.org/incident') return new Response(null, {status: 204});
    if (url.endsWith('/access_tokens')) return Response.json({token: 'ephemeral-test-token', expires_at: iso(clock+3600000), permissions: {actions:'write', metadata:'read'}, repositories:[{id:REPO_ID}], ...grantPatch});
    if (url.endsWith('/installation/token')) return new Response(null, {status:204});
    if (url.endsWith(`/repos/${REPO}`)) return Response.json({id:REPO_ID, full_name:REPO, default_branch:'main'});
    if (url.includes('/workflows/update-status.yml/runs?')) return Response.json({workflow_runs: recent ? [{conclusion:'success',updated_at:iso(clock-60000)}] : []});
    if (url.includes('/actions/runs?')) return Response.json({total_count:active?1:0, workflow_runs:active?[{path:'.github/workflows/diario-ormuz.yml'}]:[]});
    if (url.endsWith('/dispatches')) {if (dispatchThrows) throw Error('uncertain network acceptance'); return new Response(null, {status:204});}
    throw Error('unexpected route');
  };
  const settings = {CHECKS_ENABLED:'true', ALERTS_ENABLED:'false', RECOVERY_ENABLED:'false', GITHUB_APP_ID:'123', GITHUB_INSTALLATION_ID:'456', GITHUB_APP_PRIVATE_KEY:PEM, ...env};
  const core = new Coordinator(store, settings, fetcher, () => clock);
  return {core, store, calls, fetcher, settings, advance: n => {clock += n*60000;}};
}

test('journal heartbeat and edition cannot refresh stale V7; legitimate no-edition is a warning', () => {
  const stale = parse(xml(181, {journal_edition_at:iso(NOW),journal_checked_at:iso(NOW)}), NOW);
  assert.deepEqual(stale.errors,['v7_stale']);
  const oldEdition = parse(xml(1,{journal_edition_at:iso(NOW-72*3600000),journal_check_outcome:'not_due'}),NOW);
  assert.deepEqual(oldEdition.errors,[]); assert.ok(oldEdition.warnings.includes('no_recent_edition_editorial_only'));
  assert.deepEqual(parse(xml(180),NOW).errors,[]);
});
test('invalid identities, duplicate fields, future sources, entity declarations and mismatched brief fail closed', () => {
  for (const value of [xml(90,{assessment_id:'bad'}),xml(-7),xml(90,{brief_assessment_id:'c'.repeat(24)}),xml()+'<assessment_id>x</assessment_id>', '<!DOCTYPE x>'+xml(),xml(90,{brief_source_checked_at:iso(NOW)})]) assert.throws(() => parse(value,NOW));
});
test('journal technical heartbeat failure differs from absent edition', () => {
  assert.ok(parse(xml(90,{journal_checked_at:iso(NOW-37*3600000)}),NOW).errors.includes('newsroom_technical_check_stale_or_invalid'));
  assert.ok(parse(xml(90,{journal_check_outcome:'invented'}),NOW).errors.length);
});
test('probe brackets six actual HTML pages with two manifests', async () => {
  const h=harness(); const report=await probe(h.fetcher,NOW);
  assert.equal(report.publication,'xml_and_six_html_verified'); assert.equal(h.calls.length,8);
  assert.ok(h.calls.every(r => r.method === undefined && r.redirect === 'error'));
});
test('partial HTML or changing release fails proof', async () => {
  let count=0;
  await assert.rejects(probe(async url => new Response(url.endsWith('.xml')?xml(90,++count===2?{source_commit:'c'.repeat(40)}:{}):`<meta name="ormuz-assessment" content="${ID}">`),NOW));
  await assert.rejects(probe(async url => new Response(url.endsWith('.xml')?xml(): '<html>old page</html>'),NOW));
});
test('bounded HTTP reader rejects oversized and failed responses', async () => {
  await assert.rejects(textResponse(new Response('x'.repeat(11)),10));
  await assert.rejects(textResponse(new Response('no',{status:503}),100));
});
test('disabled template performs no network, dispatch or alert', async () => {
  const h=harness({env:{CHECKS_ENABLED:'false',RECOVERY_ENABLED:'true',ALERTS_ENABLED:'true'}});
  assert.deepEqual(await h.core.tick(),{status:'disabled'}); assert.equal(h.calls.length,0);
});
test('default checking is GET-only and does not need credentials', async () => {
  const h=harness(); const result=await h.core.tick();
  assert.equal(result.recovery,'disabled'); assert.equal(result.alert,'disabled');
  assert.ok(h.calls.every(c=>c.url.startsWith(BASE) && !c.method));
});
test('persistent transactional lease suppresses overlapping cron checks and survives restart', async () => {
  const h=harness(); const owner=await h.core.acquire();
  const restarted=new Coordinator(h.store,h.settings,h.fetcher,()=>NOW);
  assert.deepEqual(await restarted.tick(),{status:'overlap_suppressed'});
  h.advance(11); const replacement=await h.core.acquire(); assert.notEqual(replacement,owner);
});
test('simultaneous lease acquisition has exactly one winner', async () => {
  const h=harness(); const owners=await Promise.all([h.core.acquire(),h.core.acquire(),h.core.acquire()]);
  assert.equal(owners.filter(Boolean).length,1);
});
test('authenticated status is read only and notices a monitor that stopped checking', async () => {
  const h=harness({env:{READ_STATUS_TOKEN:'s'.repeat(40)}});
  assert.equal((await h.core.status(new Request('https://local/health'))).status,401);
  const req=()=>new Request('https://local/health',{headers:{Authorization:'Bearer '+'s'.repeat(40)}});
  assert.equal((await h.core.status(req())).status,503);
  await h.core.tick(); assert.equal((await h.core.status(req())).status,200);
  h.advance(46); assert.equal((await h.core.status(req())).status,503);
  assert.equal(h.calls.length,8);
});
test('status endpoint absent if its secret is not configured',async()=>{
  const h=harness(); assert.equal((await h.core.status(new Request('https://local/health'))).status,404);
});
test('GitHub App JWT verifies cryptographically and expires in less than ten minutes', async () => {
  const token=await jwt('123',PEM,NOW), [a,b,c]=token.split('.');
  const decode=s=>Uint8Array.from(atob(s.replaceAll('-','+').replaceAll('_','/')),x=>x.charCodeAt(0));
  assert.ok(await crypto.subtle.verify('RSASSA-PKCS1-v1_5',key.publicKey,decode(c),new TextEncoder().encode(a+'.'+b)));
  const payload=JSON.parse(new TextDecoder().decode(decode(b))); assert.equal(payload.iat,NOW/1000-60);assert.equal(payload.exp,NOW/1000+540);
});
test('recovery is scoped, correlated, recorded before dispatch, revoked and never repeated for same verification',async()=>{
  const h=harness({env:{RECOVERY_ENABLED:'true'}});
  const original=h.core.fetcher; h.core.fetcher=async(url,init)=>{
    if(String(url).endsWith('/dispatches')) assert.equal((await h.store.get('dispatch')).status,'attempt_recorded');
    return original(url,init);
  };
  assert.equal((await h.core.tick()).recovery,'accepted_not_execution_proof');
  const create=h.calls.find(c=>c.url.endsWith('/access_tokens'));
  assert.deepEqual(JSON.parse(create.body),{repository_ids:[REPO_ID],permissions:{actions:'write'}});
  const dispatch=h.calls.find(c=>c.url.endsWith('/dispatches')); const body=JSON.parse(dispatch.body);
  assert.equal(body.ref,'main');assert.equal(body.inputs.recovery_expected_verified_at,iso(NOW-90*60000));
  assert.equal(h.calls.at(-1).method,'DELETE');
  h.advance(16);assert.equal((await h.core.tick()).recovery,'dispatch_unconfirmed_no_retry');
  assert.equal(h.calls.filter(c=>c.url.endsWith('/dispatches')).length,1);
});
test('ambiguous acceptance is persisted and cannot be blindly retried',async()=>{
  const h=harness({dispatchThrows:true,env:{RECOVERY_ENABLED:'true'}});
  assert.equal((await h.core.tick()).recovery,'dispatch_uncertain_operator_review');
  h.advance(100);await h.core.tick();assert.equal(h.calls.filter(c=>c.url.endsWith('/dispatches')).length,1);
});
test('only a confirmed terminal run permits a bounded retry after cooldown',async()=>{
  const h=harness({env:{RECOVERY_ENABLED:'true'}});
  await h.core.tick();
  const original=h.core.fetcher;
  h.core.fetcher=async(url,init)=>{
    if(String(url).includes('/workflows/update-status.yml/runs?')) {
      const state=await h.store.get('dispatch');
      return Response.json({workflow_runs:[{id:101,status:'completed',conclusion:'failure',display_title:'Recuperación externa '+state.id}]});
    }
    return original(url,init);
  };
  h.advance(20);assert.equal((await h.core.tick()).recovery,'confirmed_run_cooldown');
  h.advance(71);assert.equal((await h.core.tick()).recovery,'accepted_not_execution_proof');
  h.advance(91);assert.equal((await h.core.tick()).recovery,'accepted_not_execution_proof');
  h.advance(91);assert.equal((await h.core.tick()).recovery,'retry_limit_operator_review');
  assert.equal(h.calls.filter(c=>c.url.endsWith('/dispatches')).length,3);
});
test('active journal/deploy/updater or recent successful updater prevents dispatch',async()=>{
  for(const mode of [{active:true},{recent:true}]) {
    const h=harness({...mode,env:{RECOVERY_ENABLED:'true'}});
    assert.equal((await h.core.tick()).recovery,'workflow_or_publication_in_progress');
    assert.ok(!h.calls.some(c=>c.url.endsWith('/dispatches')));
  }
});
test('insufficient age or invalid public snapshot cannot dispatch',async()=>{
  for(const mode of [{age:74},{changed:{brief_assessment_id:'bad'}}]) {
    const h=harness({...mode,env:{RECOVERY_ENABLED:'true'}});await h.core.tick();
    assert.ok(!h.calls.some(c=>c.url.includes('api.github.com')));
  }
});
test('broad installation token fails closed and is revoked without dispatch',async()=>{
  const h=harness({grantPatch:{permissions:{actions:'write',contents:'write'}},env:{RECOVERY_ENABLED:'true'}});
  assert.equal((await h.core.tick()).recovery,'requires_operator_review');
  assert.ok(!h.calls.some(c=>c.url.endsWith('/dispatches'))); assert.equal(h.calls.at(-1).method,'DELETE');
});
test('alert needs two spaced failures; stable incident ID suppresses duplicates',async()=>{
  const h=harness({age:181,env:{ALERTS_ENABLED:'true',ALERT_HOST:'ops.example.org',ALERT_WEBHOOK_URL:'https://ops.example.org/incident',ALERT_WEBHOOK_TOKEN:'x'.repeat(40)}});
  assert.equal((await h.core.tick()).alert,'confirming_incident');h.advance(15);
  assert.equal((await h.core.tick()).alert,'acknowledged');h.advance(15);
  assert.equal((await h.core.tick()).alert,'attempt_recorded_no_duplicate');
  const alerts=h.calls.filter(c=>c.url.includes('ops.example.org'));assert.equal(alerts.length,1);assert.ok(alerts[0].headers['Idempotency-Key']);
});
test('webhook configuration rejects unexpected host before sending',async()=>{
  const h=harness({age:181,env:{ALERTS_ENABLED:'true',ALERT_HOST:'different.example.org',ALERT_WEBHOOK_URL:'https://ops.example.org/incident',ALERT_WEBHOOK_TOKEN:'x'.repeat(40)}});
  await h.core.tick();h.advance(15);assert.equal((await h.core.tick()).alert,'requires_operator_review');
  assert.ok(!h.calls.some(c=>c.url.includes('ops.example.org')));
});
test('failed alert network response is not automatically resent',async()=>{
  const h=harness({age:181,env:{ALERTS_ENABLED:'true',ALERT_HOST:'ops.example.org',ALERT_WEBHOOK_URL:'https://ops.example.org/incident',ALERT_WEBHOOK_TOKEN:'x'.repeat(40)}});
  const original=h.core.fetcher;let posts=0;
  h.core.fetcher=async(url,init)=>{if(String(url).includes('ops.example.org')) {posts++;throw Error('network ambiguous');}return original(url,init);};
  await h.core.tick();h.advance(15);await h.core.tick();h.advance(15);await h.core.tick();assert.equal(posts,1);
});
