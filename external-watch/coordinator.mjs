import {probe, textResponse} from './snapshot.mjs';
import {GitHub} from './github.mjs';

const enabled = (env, key) => env[key] === 'true';
const result = (status, errors = [], details = {}) => ({status, errors, ...details});
export class Coordinator {
  constructor(storage, env, fetcher = fetch, clock = Date.now) {Object.assign(this, {storage, env, fetcher, clock});}
  async acquire() {
    const owner = crypto.randomUUID(), now = this.clock();
    return this.storage.transaction(async tx => {
      const lease = await tx.get('lease');
      if (lease && lease.until > now) return null;
      await tx.put('lease', {owner, until: now + 10*60000}); return owner;
    });
  }
  async guarded(owner, operation) {
    return this.storage.transaction(async tx => {
      const lease = await tx.get('lease');
      if (lease?.owner !== owner || lease.until <= this.clock()) throw Error('coordinator_lease_lost');
      return operation(tx);
    });
  }
  async tick() {
    if (!enabled(this.env, 'CHECKS_ENABLED')) return {status: 'disabled'};
    const owner = await this.acquire(); if (!owner) return {status: 'overlap_suppressed'};
    const now = this.clock();
    try {
      await this.guarded(owner, tx => tx.put('attempt', {started_at: new Date(now).toISOString()}));
      let snapshot;
      try {snapshot = await probe(this.fetcher, this.clock);}
      catch {snapshot = {errors: ['public_snapshot_unreachable_or_inconsistent'], warnings: [], recoverable: false};}
      const probed = this.clock();
      const report = {checked_at: new Date(now).toISOString(), scope: 'published_snapshot_not_all_services', ...snapshot};
      if (enabled(this.env, 'RECOVERY_ENABLED')) {
        try {report.recovery = await this.recover(snapshot, now, owner);}
        catch (error) {report.recovery = result('requires_operator_review', [
          error.message === 'installation_token_revocation_failed' ? 'installation_token_revocation_failed' : 'recovery_control_failed']);}
      } else report.recovery = result('disabled');
      report.errors.push(...report.recovery.errors);
      const recovered = this.clock();
      try {report.alert = await this.alert(report, now, owner);}
      catch {report.alert = result('requires_operator_review', ['alert_control_failed']);}
      report.errors.push(...report.alert.errors);
      const finished = this.clock();
      report.metrics = {elapsed_ms: finished-now, probe_ms: probed-now, recovery_ms: recovered-probed,
        alert_ms: finished-recovered, cpu_time_ms: null, cpu_measurement: 'provider_metrics_required'};
      await this.guarded(owner, async tx => {
        const count = (await tx.get('completed_checks') || 0)+1;
        report.metrics.completed_checks = count;
        let phaseB = await tx.get('phase_b');
        if (!enabled(this.env,'ALERTS_ENABLED') && !enabled(this.env,'RECOVERY_ENABLED') && snapshot.recoverable) {
          const gap = phaseB ? now-phaseB.last : Infinity;
          phaseB = phaseB && gap>=0 && gap<=30*60000 ?
            {...phaseB,count:phaseB.count+1,last:now,max_gap_ms:Math.max(phaseB.max_gap_ms,gap)} :
            {count:1,first:now,last:now,max_gap_ms:0};
          await tx.put('phase_b',phaseB);
        }
        report.phase_b_observation = phaseB || null;
        await tx.put('completed_checks', count);
        await tx.put('report', report);
        await tx.delete('fault');
        await tx.put('attempt', {started_at: new Date(now).toISOString(), completed_at: new Date(finished).toISOString()});
      });
      return report;
    } catch (error) {
      // A stale lease owner must not overwrite the newer owner's report or side effects.
      if (error.message === 'coordinator_lease_lost') throw error;
      await this.guarded(owner, tx => tx.put('fault', {at: new Date(this.clock()).toISOString(), code: 'monitor_internal_failure'}));
      throw Error('monitor_internal_failure');
    } finally {
      await this.storage.transaction(async tx => {
        if ((await tx.get('lease'))?.owner === owner) await tx.delete('lease');
      });
    }
  }
  async recoveryGate() {
    const phaseB = await this.storage.get('phase_b');
    return enabled(this.env, 'ALERTS_ENABLED') && (this.env.READ_STATUS_TOKEN || '').length >= 32 &&
      /^[a-f0-9]{64}$/.test(this.env.RECOVERY_GATE_EVIDENCE_SHA256 || '') && phaseB?.count>=96 &&
      phaseB.last-phaseB.first>=1425*60000 && phaseB.max_gap_ms<=30*60000;
  }
  async recover(snapshot, now, owner) {
    if (!await this.recoveryGate()) return result('activation_gate_closed', ['recovery_prerequisites_not_recorded']);
    if (!snapshot.recoverable) return result('invalid_snapshot_no_dispatch');
    const previous = await this.storage.get('dispatch');
    if (!previous && snapshot.age_minutes < 75) return result('verification_recent');
    const gh = new GitHub(this.env, this.fetcher, this.clock, () => this.guarded(owner, async () => {}));
    return gh.withToken(async token => {
      const info = await gh.inspect(token);
      let attempt = 1, errors = [];
      const trace = previous ? {request_id: previous.id, attempt: previous.attempt, published_commit: snapshot.commit} : {};
      if (previous) {
        const elapsed = (now-previous.at)/60000;
        const run = info.runs.find(r => r.display_title === 'Recuperación externa '+previous.id);
        Object.assign(trace, {run_id: run?.id || null, run_status: run?.status || null, run_conclusion: run?.conclusion || null});
        if (!run) {
          const uncertain = previous.status === 'uncertain_no_retry' || previous.status === 'attempt_recorded';
          return result('dispatch_unconfirmed_no_retry', uncertain || elapsed > 30 ? ['recovery_dispatch_not_confirmed'] : [], trace);
        }
        if (run.status !== 'completed') return result('run_pending', elapsed > 45 ? ['recovery_run_overdue'] : [], trace);
        if (!['success','failure','cancelled','timed_out'].includes(run.conclusion)) return result('terminal_result_requires_review', ['recovery_run_result_unknown'], trace);
        if (snapshot.verified !== previous.verified) {
          if (Date.parse(snapshot.verified) <= Date.parse(previous.verified)) return result('verification_regressed', ['v7_verification_regressed'], trace);
          if (snapshot.age_minutes < 75) return result('verification_advanced_causation_not_assumed', [], trace);
        } else {
          attempt = (previous.attempt || 1)+1;
          errors = [run.conclusion === 'success' ? 'recovery_completed_without_new_v7_verification' : 'recovery_run_failed'];
          if (attempt > 3) return result('retry_limit_operator_review', [...errors,'recovery_retry_limit_exhausted'], trace);
        }
        if (elapsed < 90) return result('confirmed_run_cooldown', errors, trace);
      }
      if (info.active) return result('workflow_or_publication_in_progress', errors, trace);
      return this.attempt(gh, token, snapshot, now, attempt, owner, errors);
    });
  }
  async attempt(gh, token, snapshot, now, attempt, owner, errors) {
    const request = {id: crypto.randomUUID(), verified: snapshot.verified, at: now, attempt, status: 'attempt_recorded'};
    await this.guarded(owner, tx => tx.put('dispatch', request));
    try {
      await gh.dispatch(token, request);
      await this.guarded(owner, tx => tx.put('dispatch', {...request, status: 'accepted_not_execution_proof'}));
      return result('accepted_not_execution_proof', errors, {request_id: request.id, attempt});
    } catch (error) {
      if (error.message === 'coordinator_lease_lost') throw error;
      await this.guarded(owner, tx => tx.put('dispatch', {...request, status: 'uncertain_no_retry'}));
      return result('dispatch_uncertain_operator_review', [...errors,'recovery_dispatch_uncertain'], {request_id: request.id, attempt});
    }
  }
  alertDestination() {
    const url = new URL(this.env.ALERT_WEBHOOK_URL || '');
    if (url.protocol !== 'https:' || url.host !== this.env.ALERT_HOST || url.username || url.password ||
        !/^[a-z0-9-]+(?:\.[a-z0-9-]+)+$/i.test(url.hostname) || /(?:localhost|\.local|\.internal)$/.test(url.hostname) ||
        /^\d+(?:\.\d+){3}$/.test(url.hostname) || (this.env.ALERT_WEBHOOK_TOKEN || '').length < 32) throw Error('alert_destination_invalid');
    return url;
  }
  async acknowledged(response, id) {
    if (![200,202].includes(response.status)) {await response.body?.cancel();return false;}
    try {
      const ack = JSON.parse(await textResponse(response,4096));
      return ack.id === id && ack.accepted === true;
    } catch {return false;}
  }
  async alert(report, now, owner) {
    const active = report.errors.length > 0;
    let incident = await this.storage.get('incident');
    if (!enabled(this.env,'ALERTS_ENABLED')) return result('disabled');
    if (active) {
      // One episode keeps its identity even if its error codes change.
      incident = incident && (!incident.resolved_at || (incident.attempted && !incident.acknowledged)) ?
        {...incident, checks: incident.checks+1, resolved_at: null} :
        {id: crypto.randomUUID(), checks:1, since:now, attempted:false};
    } else if (incident) incident = {...incident, resolved_at: incident.resolved_at || new Date(now).toISOString()};
    if (!incident) return result('healthy');
    await this.guarded(owner, tx => tx.put('incident',incident));
    const details = {incident_id:incident.id, receiver_acknowledged:!!incident.acknowledged};
    if (incident.acknowledged) return result(active ? 'receiver_acknowledged' : 'resolved',[],details);
    if (!active && !incident.attempted) return result('resolved_without_send',[],details);
    if (active && !incident.attempted && (incident.checks < 2 || now-incident.since < 14*60000)) return result('confirming_incident',[],details);
    const url = this.alertDestination();
    const headers = {Authorization:'Bearer '+this.env.ALERT_WEBHOOK_TOKEN, 'Content-Type':'application/json'};
    if (incident.attempted) {
      // Reconcile a receiver receipt; never blindly repeat an ambiguous POST.
      url.searchParams.set('incident_id',incident.id);
      try {
        const response = await this.fetcher(url.href,{redirect:'error',signal:AbortSignal.timeout(15000),headers});
        if (await this.acknowledged(response,incident.id)) {
          await this.guarded(owner, tx => tx.put('incident',{...incident,acknowledged:true}));
          return result('receiver_acknowledged',[],{...details,receiver_acknowledged:true});
        }
      } catch { /* Persisted attempt remains uncertain; no resend. */ }
      return result('delivery_unconfirmed_no_resend',['alert_delivery_unconfirmed'],details);
    }
    await this.guarded(owner, tx => tx.put('incident',{...incident,attempted:true}));
    await this.guarded(owner,async()=>{});
    try {
      const response = await this.fetcher(url.href,{method:'POST',redirect:'error',signal:AbortSignal.timeout(15000),
        headers:{...headers,'Idempotency-Key':incident.id},
        body:JSON.stringify({id:incident.id,type:'ormuz_technical_incident',checked_at:report.checked_at,errors:report.errors,verified_at:report.verified || null})});
      const accepted = await this.acknowledged(response,incident.id);
      await this.guarded(owner,tx=>tx.put('incident',{...incident,attempted:true,acknowledged:accepted}));
      return result(accepted ? 'receiver_acknowledged' : 'delivery_unconfirmed_no_resend',accepted ? [] : ['alert_delivery_unconfirmed'],{...details,receiver_acknowledged:accepted});
    } catch (error) {
      if (error.message === 'coordinator_lease_lost') throw error;
      return result('delivery_unconfirmed_no_resend',['alert_delivery_unconfirmed'],details);
    }
  }
  async status(request) {
    const secret = this.env.READ_STATUS_TOKEN || '';
    if (secret.length < 32) return new Response(null,{status:404});
    const digest = async value => new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)));
    const a=await digest(request.headers.get('Authorization') || ''), b=await digest('Bearer '+secret);
    let diff=0;for(let i=0;i<a.length;i++)diff |= a[i]^b[i];
    if(diff)return new Response(null,{status:401});
    const report=await this.storage.get('report'), fault=await this.storage.get('fault'), attempt=await this.storage.get('attempt');
    const age=report ? (this.clock()-Date.parse(report.checked_at))/60000 : Infinity;
    const stuck=attempt && !attempt.completed_at && this.clock()-Date.parse(attempt.started_at)>5*60000;
    const unresolvedFault=fault && (!report || Date.parse(fault.at)>=Date.parse(report.checked_at));
    const ok=enabled(this.env,'CHECKS_ENABLED') && age>=0 && age<=45 && report?.errors.length===0 && !stuck && !unresolvedFault;
    return Response.json({ok,last_check_age_minutes:Number.isFinite(age)?age:null,stuck:!!stuck,fault:unresolvedFault?fault:null,report:report || null},
      {status:ok?200:503,headers:{'Cache-Control':'no-store'}});
  }
}
