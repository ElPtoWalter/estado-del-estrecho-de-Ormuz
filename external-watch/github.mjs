// Fixed target, short-lived GitHub App installation token; never a public dispatch proxy.
import {textResponse} from './snapshot.mjs';
export const REPO = 'ElPtoWalter/estado-del-estrecho-de-Ormuz';
export const REPO_ID = 1298193500;
export const WORKFLOW = 'update-status.yml';
const API = 'https://api.github.com';
const enc = new TextEncoder();
const b64 = bytes => btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
export async function jwt(appId, pem, now) {
  if (!/^\d+$/.test(appId || '') || !pem?.includes('BEGIN PRIVATE KEY')) throw Error('app_configuration_missing');
  const bytes = Uint8Array.from(atob(pem.replace(/-----[^-]+-----|\s/g, '')), x => x.charCodeAt(0));
  const key = await crypto.subtle.importKey('pkcs8', bytes, {name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256'}, false, ['sign']);
  const header = b64(enc.encode(JSON.stringify({alg: 'RS256', typ: 'JWT'})));
  const body = b64(enc.encode(JSON.stringify({iat: Math.floor(now/1000)-60, exp: Math.floor(now/1000)+540, iss: appId})));
  const message = `${header}.${body}`;
  return message + '.' + b64(new Uint8Array(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key, enc.encode(message))));
}

export class GitHub {
  constructor(env, fetcher, now = Date.now, beforeWrite = async () => {}) {
    Object.assign(this, {env, fetcher, beforeWrite});
    this.clock=typeof now==='function'?now:()=>now;
  }
  async request(path, token, method = 'GET', body) {
    if (method === 'POST') await this.beforeWrite();
    const response = await this.fetcher(API + path, {method, redirect: 'error', signal: AbortSignal.timeout(15000),
      headers: {Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'Ormuz-IndependentWatch/1', 'Content-Type': 'application/json'},
      ...(body === undefined ? {} : {body: JSON.stringify(body)})});
    if (response.status === 204) return null;
    if (!response.ok) throw Error('github_http_' + response.status);
    return JSON.parse(await textResponse(response, 4000000));
  }
  async withToken(operation) {
    if (!/^\d+$/.test(this.env.GITHUB_INSTALLATION_ID || '')) throw Error('app_configuration_missing');
    const auth = await jwt(this.env.GITHUB_APP_ID, this.env.GITHUB_APP_PRIVATE_KEY, this.clock());
    const grant = await this.request(`/app/installations/${this.env.GITHUB_INSTALLATION_ID}/access_tokens`, auth, 'POST', {
      repository_ids: [REPO_ID], permissions: {actions: 'write'},
    });
    const receivedAt=this.clock();
    try {
      if (typeof grant.token !== 'string' || !grant.token || grant.permissions?.actions !== 'write' ||
          (grant.permissions.metadata && grant.permissions.metadata !== 'read') || Object.keys(grant.permissions || {}).some(x => !['actions','metadata'].includes(x)) ||
          grant.repositories?.length !== 1 || grant.repositories[0].id !== REPO_ID ||
          !Number.isFinite(Date.parse(grant.expires_at)) || Date.parse(grant.expires_at) <= receivedAt || Date.parse(grant.expires_at) - receivedAt > 60*60000) throw Error('installation_scope_invalid');
      return await operation(grant.token);
    } finally {
      // Cleanup is required even after losing the coordinator lease.
      if (grant.token) {
        try {await this.request('/installation/token', grant.token, 'DELETE');}
        catch {throw Error('installation_token_revocation_failed');}
      }
    }
  }
  async inspect(token) {
    const repo = await this.request(`/repos/${REPO}`, token);
    if (repo.id !== REPO_ID || repo.full_name !== REPO || repo.default_branch !== 'main' || repo.archived || repo.disabled) throw Error('repository_identity_changed');
    let active = false;
    for (const status of ['queued','in_progress','waiting','requested','pending']) {
      const data = await this.request(`/repos/${REPO}/actions/runs?branch=main&status=${status}&per_page=100`, token);
      if (data.total_count > 100) throw Error('active_run_visibility_incomplete');
      active ||= data.workflow_runs.some(r => /\/(update-status|diario-ormuz|deploy-public)\.yml(?:@|$)/.test(r.path));
    }
    const data = await this.request(`/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?branch=main&per_page=100`, token);
    if (!Array.isArray(data.workflow_runs)) throw Error('run_response_invalid');
    // A successful workflow may be a no-op. Never use its completion as V7 proof.
    return {active, runs: data.workflow_runs};
  }
  async dispatch(token, request) {
    await this.request(`/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, token, 'POST', {
      ref: 'main', inputs: {recovery_request_id: request.id, recovery_expected_verified_at: request.verified},
    });
  }
}
