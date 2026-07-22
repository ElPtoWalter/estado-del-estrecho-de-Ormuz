(() => {
  const root = document.querySelector('[data-g4-widget]');
  if (!root) return;
  const q = new URLSearchParams(location.search);
  const lang = q.get('lang') === 'en' || document.documentElement.lang.startsWith('en') ? 'en' : 'es';
  const theme = q.get('theme') === 'light' ? 'light' : 'dark';
  const compact = q.get('compact') === '1';
  root.dataset.theme = theme;
  root.classList.toggle('compact', compact);
  const $ = (s) => root.querySelector(s);
  const labels = {
    es: { loading:'Consultando…', confidence:'Confianza', updated:'Actualizado', open:'ABIERTO', closed:'CERRADO', uncertain:'INCIERTO', view:'Ver evidencias →' },
    en: { loading:'Checking…', confidence:'Confidence', updated:'Updated', open:'OPEN', closed:'CLOSED', uncertain:'UNCERTAIN', view:'View evidence →' }
  }[lang];
  $('[data-state]').textContent = labels.loading;
  $('[data-confidence-label]').textContent = labels.confidence;
  $('[data-updated-label]').textContent = labels.updated;
  $('[data-view]').textContent = labels.view;
  $('[data-view]').href = (lang === 'en' ? '/en.html' : '/') + '?utm_source=embed&utm_medium=widget&utm_campaign=live_status';
  fetch('/status.json?widget=' + Date.now(), {cache:'no-store'})
    .then(r => { if(!r.ok) throw new Error(r.status); return r.json(); })
    .then(data => {
      const status = data.status || 'INCIERTO';
      const operational = lang === 'en' ? data.operational_label_en : data.operational_label_es;
      $('[data-state]').textContent = operational || labels[status === 'ABIERTO' ? 'open' : status === 'CERRADO' ? 'closed' : 'uncertain'];
      $('[data-state]').classList.add(status === 'ABIERTO' ? 'g4-status-open' : status === 'CERRADO' ? 'g4-status-closed' : 'g4-status-uncertain');
      $('[data-summary]').textContent = lang === 'en' ? data.summary_en : data.summary_es;
      $('[data-confidence]').textContent = data.confidence || '—';
      const date = data.checked_at ? new Date(data.checked_at) : null;
      $('[data-updated]').textContent = date && !Number.isNaN(date.valueOf()) ? new Intl.DateTimeFormat(lang === 'en' ? 'en-GB':'es-ES',{dateStyle:'short',timeStyle:'short'}).format(date) : '—';
    })
    .catch(() => { $('[data-state]').textContent = labels.uncertain; $('[data-summary]').textContent = lang === 'en' ? 'Live data is temporarily unavailable.' : 'Los datos en directo no están disponibles temporalmente.'; });
})();
