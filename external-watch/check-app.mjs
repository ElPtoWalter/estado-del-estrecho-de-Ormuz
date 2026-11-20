// Explicit future authorization required. This probe can mint/revoke, never dispatch.
import {pathToFileURL} from 'node:url';
import {GitHub,REPO,REPO_ID} from './github.mjs';
export async function checkApp(env,fetcher=fetch,now=Date.now) {
  if(env.APP_AUTH_PROBE_AUTHORIZED!=='true') return {ok:false,status:'not_authorized_no_request'};
  const gh=new GitHub(env,fetcher,now);
  const summary=await gh.withToken(async token=>{
    const info=await gh.inspect(token);
    return {repository:REPO,repository_id:REPO_ID,active_writer:info.active,visible_updater_runs:info.runs.length};
  });
  return {ok:true,...summary,token_scope_checked:true,token_revocation_confirmed:true,dispatch_performed:false};
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {
    const result=await checkApp(process.env);console.log(JSON.stringify(result));
    if(!result.ok)process.exitCode=1;
  } catch {
    console.log(JSON.stringify({ok:false,status:'app_authentication_or_revocation_failed',dispatch_performed:false}));process.exitCode=1;
  }
}
