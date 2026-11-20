// Public, minimal publication contract. No internal JSON or journal date as V7 heartbeat.
export const BASE = 'https://estrechoormuz.com';
export const PAGES = ['index.html', 'en.html', 'parte-diario.html', 'en-daily-brief.html', 'historial.html', 'en-history.html'];
export const minutes = (now, value) => {
  if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+00:00)$/.test(value || '')) return NaN;
  return (now - Date.parse(value)) / 60000;
};
export function parse(xml, now) {
  if (xml.length > 16000 || /<!|&/.test(xml) || !/<publication version="1" engine="operational-intelligence-v7">/.test(xml)) throw Error('invalid_contract');
  const field = name => {
    const values = [...xml.matchAll(new RegExp(`<${name}>([^<>]*)</${name}>`, 'g'))];
    if (values.length > 1) throw Error('duplicate_contract_field');
    return values[0]?.[1] || '';
  };
  const id = field('assessment_id'), commit = field('source_commit'), verified = field('verified_at');
  if (!/^[a-f0-9]{24}$/.test(id) || !/^[a-f0-9]{40}$/.test(commit)) throw Error('invalid_identity');
  const age = minutes(now, verified), briefAge = minutes(now, field('brief_source_checked_at'));
  if (![age, briefAge].every(x => Number.isFinite(x) && x >= -6)) throw Error('invalid_source_time');
  if (field('brief_assessment_id') !== id || field('brief_source_checked_at') !== verified) throw Error('brief_desynchronized');
  const errors = age > 180 ? ['v7_stale'] : [];
  const warnings = [];
  const checked = field('journal_checked_at'), editionAge = minutes(now, field('journal_edition_at'));
  if (!checked) warnings.push('newsroom_technical_check_unknown');
  else if (!Number.isFinite(minutes(now, checked)) || minutes(now, checked) < -6 || minutes(now, checked) > 2160 ||
           !['published', 'not_due', 'edition_already_exists'].includes(field('journal_check_outcome'))) errors.push('newsroom_technical_check_stale_or_invalid');
  if (!Number.isFinite(editionAge) || editionAge > 2160) warnings.push('no_recent_edition_editorial_only');
  else if (editionAge < -6) errors.push('future_edition');
  return {id, commit, verified, age_minutes: age, errors, warnings, recoverable: true};
}

export async function textResponse(response, limit) {
  if (!response.ok) throw Error('http_failure');
  const reader = response.body.getReader();
  const chunks = []; let size = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read(); if (done) break;
      size += value.byteLength;
      if (size > limit) throw Error('response_too_large');
      chunks.push(value);
    }
  } finally { await reader.cancel().catch(() => {}); }
  const bytes = new Uint8Array(size); let at = 0;
  for (const chunk of chunks) {bytes.set(chunk, at); at += chunk.length;}
  return new TextDecoder('utf-8', {fatal: true}).decode(bytes);
}

export async function probe(fetcher, now) {
  const get = async path => textResponse(await fetcher(BASE + '/' + path, {
    redirect: 'error', signal: AbortSignal.timeout(15000), headers: {'Cache-Control': 'no-cache', 'User-Agent': 'Ormuz-IndependentWatch/1'},
  }), path.endsWith('.xml') ? 16000 : 200000);
  const first = parse(await get('publication-health.xml'), now);
  for (const page of PAGES) {
    const html = await get(page);
    if (!html.includes(`<meta name="ormuz-assessment" content="${first.id}"`)) throw Error('html_not_aligned');
  }
  const last = parse(await get('publication-health.xml'), now);
  if (first.id !== last.id || first.commit !== last.commit || first.verified !== last.verified) throw Error('deployment_changed_during_probe');
  return {...last, publication: 'xml_and_six_html_verified', updater_process: 'requires_actions_evidence', radar: 'external_provider_not_probed'};
}
