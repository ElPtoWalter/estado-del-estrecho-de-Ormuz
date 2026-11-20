import {DurableObject} from 'cloudflare:workers';
import {Coordinator} from './coordinator.mjs';
export class OrmuzCoordinator extends DurableObject {
  constructor(ctx, env) {super(ctx, env); this.core = new Coordinator(ctx.storage, env);}
  tick() {return this.core.tick();}
  fetch(request) {return this.core.status(request);}
}
export default {
  async scheduled(_event, env, ctx) {
    if (env.CHECKS_ENABLED !== 'true') return;
    ctx.waitUntil(env.COORDINATOR.getByName('estrecho-ormuz-v1').tick());
  },
  async fetch(request, env) {
    if (request.method !== 'GET' || new URL(request.url).pathname !== '/health') return new Response(null, {status: 404});
    return env.COORDINATOR.getByName('estrecho-ormuz-v1').fetch(request);
  },
};
