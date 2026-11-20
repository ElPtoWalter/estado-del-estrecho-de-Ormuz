import {probe} from './snapshot.mjs';
import {GitHub} from './github.mjs';

const enabled = (env, key) => env[key] === 'true';
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
  async tick() {
    if (!enabled(this.env, 'CHECKS_ENABLED')) return {status: 'disabled'};
    const owner = await this.acquire(); if (!owner) return {status: 'overlap_suppressed'};
    try {
      const now = this.clock();
      let snapshot;
      try {snapshot = await probe(this.fetcher, now);}
      catch {snapshot = {errors: ['public_snapshot_unreachable_or_inconsistent'], warnings: [], recoverable: false};}
      const report = {checked_at: new Date(now).toISOString(), scope: 'published_snapshot_not_all_services', ...snapshot};
      if (enabled(this.env, 'RECOVERY_ENABLED')) {
        try {report.recovery = await this.recover(snapshot, now);}
        catch {report.recovery = 'requires_operator_review'; report.errors.push('recovery_control_failed');}
      } else report.recovery = 'disabled';
      try {report.alert = await this.alert(report, now);}
      catch {report.alert = 'requires_operator_review'; report.errors.push('alert_control_failed');}
      await this.storage.put('report', report);
      return report;
    } finally {
      await this.storage.transaction(async tx => {
        if ((await tx.get('lease'))?.owner === owner) await tx.delete('lease');
      });
    }
  }
  async recover(snapshot, now) {
    if (!snapshot.recoverable) return 'invalid_snapshot_no_dispatch';
    const previous = await this.storage.get('dispatch');
    // A retry requires a visible terminal run. An ambiguous POST is never blindly retried.
    if (previous?.verified === snapshot.verified) {
      const gh = new GitHub(this.env, this.fetcher, now);
      return gh.withToken(async token => {
        const info = await gh.inspect(token);
        const run = info.runs.find(r => r.display_title === 'Recuperación externa ' + previous.id);
        let status = !run ? 'dispatch_unconfirmed_no_retry' : run.status !== 'completed' ? 'run_pending' :
          run.conclusion === 'success' ? 'run_succeeded_verification_not_advanced' : 'run_failed_operator_retry_required';
        if (run?.status === 'completed' && ['success','failure','cancelled','timed_out'].includes(run.conclusion)) {
          if ((previous.attempt || 1) >= 3) status = 'retry_limit_operator_review';
          else if (now - previous.at < 90*60000) status = 'confirmed_run_cooldown';
          else if (info.active || info.recentSuccess) status = 'workflow_or_publication_in_progress';
          else return this.attempt(gh, token, snapshot, now, (previous.attempt || 1)+1);
        }
        await this.storage.put('dispatch', {...previous, status, run_id: run?.id || null});
        return status;
      });
    }
    if (snapshot.age_minutes < 75) return 'verification_recent';
    if (previous && now - previous.at < 90*60000) return 'cooldown';
    const gh = new GitHub(this.env, this.fetcher, now);
    return gh.withToken(async token => {
      const info = await gh.inspect(token);
      if (info.active || info.recentSuccess) return 'workflow_or_publication_in_progress';
      return this.attempt(gh, token, snapshot, now, 1);
    });
  }
  async attempt(gh, token, snapshot, now, attempt) {
    const request = {id: crypto.randomUUID(), verified: snapshot.verified, at: now, attempt, status: 'attempt_recorded'};
    await this.storage.put('dispatch', request); // Must precede the network side effect.
    try {
      await gh.dispatch(token, request);
      await this.storage.put('dispatch', {...request, status: 'accepted_not_execution_proof'});
      return 'accepted_not_execution_proof';
    } catch {
      await this.storage.put('dispatch', {...request, status: 'uncertain_no_retry'});
      return 'dispatch_uncertain_operator_review';
    }
  }
  async alert(report, now) {
    const fingerprint = [...report.errors].sort().join('|');
    const previous = await this.storage.get('incident');
    if (!fingerprint) {
      if (previous) await this.storage.put('incident', {...previous, resolved_at: new Date(now).toISOString()});
      return enabled(this.env, 'ALERTS_ENABLED') ? 'healthy' : 'disabled';
    }
    const incident = previous?.fingerprint === fingerprint && !previous.resolved_at ? {...previous, checks: previous.checks+1} :
      {id: crypto.randomUUID(), fingerprint, checks: 1, since: now, attempted: false};
    await this.storage.put('incident', incident);
    if (!enabled(this.env, 'ALERTS_ENABLED')) return 'disabled';
    if (incident.checks < 2 || now - incident.since < 14*60000) return 'confirming_incident';
    if (incident.attempted) return 'attempt_recorded_no_duplicate';
    const url = new URL(this.env.ALERT_WEBHOOK_URL || '');
    if (url.protocol !== 'https:' || url.host !== this.env.ALERT_HOST || url.username || url.password ||
        !/^[a-z0-9-]+(?:\.[a-z0-9-]+)+$/i.test(url.hostname) || /(?:localhost|\.local|\.internal)$/.test(url.hostname) ||
        /^\d+(?:\.\d+){3}$/.test(url.hostname) ||
        (this.env.ALERT_WEBHOOK_TOKEN || '').length < 32) throw Error('alert_destination_invalid');
    await this.storage.put('incident', {...incident, attempted: true});
    const response = await this.fetcher(url.href, {method: 'POST', redirect: 'error', signal: AbortSignal.timeout(15000),
      headers: {Authorization: 'Bearer ' + this.env.ALERT_WEBHOOK_TOKEN, 'Content-Type': 'application/json', 'Idempotency-Key': incident.id},
      body: JSON.stringify({id: incident.id, type: 'ormuz_technical_incident', checked_at: report.checked_at, errors: report.errors, verified_at: report.verified || null})});
    await response.body?.cancel();
    await this.storage.put('incident', {...incident, attempted: true, acknowledged: response.ok});
    return response.ok ? 'acknowledged' : 'rejected_operator_review';
  }
  async status(request) {
    const secret = this.env.READ_STATUS_TOKEN || '';
    if (secret.length < 32) return new Response(null, {status: 404});
    // Hash before constant-length comparison; never expose an unauthenticated health/trigger route.
    const digest = async value => new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value)));
    const a = await digest(request.headers.get('Authorization') || ''), b = await digest('Bearer ' + secret);
    let diff = 0; for (let i=0; i<a.length; i++) diff |= a[i] ^ b[i];
    if (diff) return new Response(null, {status: 401});
    const report = await this.storage.get('report');
    const age = report ? (this.clock() - Date.parse(report.checked_at))/60000 : Infinity;
    const ok = enabled(this.env, 'CHECKS_ENABLED') && age >= 0 && age <= 45 && report?.errors.length === 0 &&
      !['requires_operator_review','rejected_operator_review'].includes(report?.alert);
    return Response.json({ok, last_check_age_minutes: Number.isFinite(age) ? age : null, report: report || null},
      {status: ok ? 200 : 503, headers: {'Cache-Control': 'no-store'}});
  }
}
