// Owner-authorized one-off rehearsal. Never schedules, installs or deploys a service.
import {pathToFileURL,fileURLToPath} from 'node:url';
import path from 'node:path';
import fs from 'node:fs/promises';
import {probe} from './snapshot.mjs';
import {GitHub,REPO} from './github.mjs';
export async function exercise(env,fetcher=fetch,now=Date.now) {
  if(env.RECOVERY_SINGLE_TEST_AUTHORIZED!=='true')return {ok:false,status:'not_authorized_no_request'};
  const receipt=env.RECOVERY_TEST_RECEIPT || '';
  if(!path.isAbsolute(receipt))throw Error('private_absolute_receipt_required');
  const parent=await fs.realpath(path.dirname(receipt));
  const checkout=await fs.realpath(fileURLToPath(new URL('../',import.meta.url)));
  const relative=path.relative(checkout,parent);
  if(!relative || (!relative.startsWith('..'+path.sep) && !path.isAbsolute(relative)))throw Error('receipt_must_stay_outside_checkout');
  const clock=typeof now==='function'?now:()=>now;
  const snapshot=await probe(fetcher,clock);
  if(snapshot.verified!==env.RECOVERY_EXPECTED_VERIFIED_AT || snapshot.age_minutes<75)throw Error('expected_snapshot_not_eligible');
  return new GitHub(env,fetcher,now).withToken(async token=>{
    const gh=new GitHub(env,fetcher,now), info=await gh.inspect(token);
    if(info.active)throw Error('writer_in_progress');
    const request={id:crypto.randomUUID(),verified:snapshot.verified,repository:REPO,status:'attempt_recorded',at:new Date(clock()).toISOString()};
    const file=await fs.open(receipt,'wx',0o600);
    try {await file.writeFile(JSON.stringify(request,null,2)+'\n');await file.sync();} finally {await file.close();}
    try {
      await gh.dispatch(token,request);
      await fs.writeFile(receipt,JSON.stringify({...request,status:'accepted_not_execution_proof'},null,2)+'\n');
      return {ok:true,status:'accepted_not_execution_proof',request_id:request.id};
    } catch {
      // Preserve the attempt record even if writing an updated status fails.
      return {ok:false,status:'dispatch_uncertain_no_retry',request_id:request.id};
    }
  });
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  try {const value=await exercise(process.env);console.log(JSON.stringify(value));if(!value.ok)process.exitCode=1;}
  catch {console.log(JSON.stringify({ok:false,status:'rehearsal_stopped_check_private_receipt_no_blind_retry'}));process.exitCode=1;}
}
