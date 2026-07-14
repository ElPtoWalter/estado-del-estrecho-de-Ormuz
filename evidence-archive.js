(() => {
  "use strict";
  const lang = document.documentElement.lang === "en" ? "en" : "es";
  const locale = lang === "es" ? "es-ES" : "en-GB";
  const text = lang === "es" ? {
    loadErrorTitle: "No se pudo cargar el archivo",
    loadErrorBody: "El estado actual sigue disponible. Recarga la página para intentar recuperar las evidencias.",
    emptyTitle: "No hay evidencias que coincidan",
    emptyBody: "Prueba con otra fuente o elimina el texto de búsqueda.",
    noArchiveTitle: "El archivo aún no contiene evidencias",
    noArchiveBody: "Se completará automáticamente a medida que el motor procese nuevas comprobaciones.",
    allSources: "Todas las fuentes",
    result: "resultado", results: "resultados",
    source: "fuente", sources: "fuentes",
    published: "Publicada", observed: "Detectada",
    openSource: "Abrir fuente ↗",
    official: "Fuente oficial",
    tier: "Nivel",
    relevant: "Señal relevante",
    operational: "Tráfico operativo",
    restriction: "Restricción o riesgo",
    closure: "Cierre o interrupción",
    incident: "Incidente",
    checked: "Última comprobación",
    retained: "Ventana de conservación",
    days: "días",
    archiveSize: "Evidencias conservadas",
    uniqueSources: "Fuentes distintas"
  } : {
    loadErrorTitle: "The archive could not be loaded",
    loadErrorBody: "The current status remains available. Reload the page to retrieve the evidence.",
    emptyTitle: "No evidence matches these filters",
    emptyBody: "Try another source or clear the search field.",
    noArchiveTitle: "The archive does not contain evidence yet",
    noArchiveBody: "It will fill automatically as the engine completes new checks.",
    allSources: "All sources",
    result: "result", results: "results",
    source: "source", sources: "sources",
    published: "Published", observed: "Observed",
    openSource: "Open source ↗",
    official: "Official source",
    tier: "Tier",
    relevant: "Relevant signal",
    operational: "Operational traffic",
    restriction: "Restriction or risk",
    closure: "Closure or disruption",
    incident: "Incident",
    checked: "Latest check",
    retained: "Retention window",
    days: "days",
    archiveSize: "Evidence retained",
    uniqueSources: "Distinct sources"
  };

  const state = { items: [], query: "", source: "all", checkedAt: null, days: 14 };
  const list = document.getElementById("archiveList");
  const search = document.getElementById("archiveSearch");
  const sourceSelect = document.getElementById("archiveSource");
  const reset = document.getElementById("archiveReset");
  const summary = document.getElementById("archiveSummary");

  function parseDate(value) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  function formatDate(value, includeTime = false) {
    const date = parseDate(value);
    if (!date) return "—";
    const options = includeTime
      ? { dateStyle: "medium", timeStyle: "short", timeZone: lang === "es" ? "Europe/Madrid" : "UTC" }
      : { dateStyle: "medium", timeZone: lang === "es" ? "Europe/Madrid" : "UTC" };
    return new Intl.DateTimeFormat(locale, options).format(date) + (lang === "en" && includeTime ? " UTC" : "");
  }
  function normalise(value) {
    return String(value || "").toLocaleLowerCase(locale).normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }
  function classifySignal(value) {
    const signal = normalise(value);
    if (/clos|block|shut|interrup|cerr/.test(signal)) return { label: text.closure, className: "is-critical" };
    if (/restrict|risk|threat|escort|desvi|restric|riesgo/.test(signal)) return { label: text.restriction, className: "is-warning" };
    if (/incident|attack|seiz|explos|incidente|ataque/.test(signal)) return { label: text.incident, className: "is-warning" };
    if (/open|operat|traffic|transit|abiert|trafico|transito/.test(signal)) return { label: text.operational, className: "" };
    return { label: text.relevant, className: "" };
  }
  function cleanedItems(data) {
    const archive = Array.isArray(data?.evidence_archive) ? data.evidence_archive : [];
    const fallback = Array.isArray(data?.evidence) ? data.evidence : [];
    const items = archive.length ? archive : fallback;
    const seen = new Set();
    return items.filter(item => item && typeof item === "object").filter(item => {
      const key = `${normalise(item.source_name)}|${normalise(item.title)}|${item.source_url || ""}`;
      if (!item.title && !item.source_url || seen.has(key)) return false;
      seen.add(key); return true;
    }).sort((a,b) => (parseDate(b.published_at || b.observed_at)?.getTime() || 0) - (parseDate(a.published_at || a.observed_at)?.getTime() || 0));
  }
  function makeBadge(label, className = "") {
    const el = document.createElement("span");
    el.className = `archive-badge ${className}`.trim();
    el.textContent = label;
    return el;
  }
  function renderMetrics() {
    const sources = new Set(state.items.map(item => item.source_name).filter(Boolean));
    const values = {
      archiveMetricChecked: formatDate(state.checkedAt, true),
      archiveMetricDays: `${state.days} ${text.days}`,
      archiveMetricCount: String(state.items.length),
      archiveMetricSources: String(sources.size)
    };
    Object.entries(values).forEach(([id,value]) => { const el = document.getElementById(id); if (el) el.textContent = value; });
  }
  function fillSources() {
    const sources = [...new Set(state.items.map(item => String(item.source_name || "").trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b, locale));
    sourceSelect.replaceChildren();
    const all = document.createElement("option"); all.value = "all"; all.textContent = text.allSources; sourceSelect.append(all);
    sources.forEach(source => { const option = document.createElement("option"); option.value = source; option.textContent = source; sourceSelect.append(option); });
  }
  function filteredItems() {
    const query = normalise(state.query.trim());
    return state.items.filter(item => {
      if (state.source !== "all" && item.source_name !== state.source) return false;
      if (!query) return true;
      return normalise(`${item.title} ${item.source_name} ${item.signal}`).includes(query);
    });
  }
  function renderSummary(items) {
    const sourceCount = new Set(items.map(item => item.source_name).filter(Boolean)).size;
    summary.replaceChildren();
    const strong = document.createElement("strong"); strong.textContent = String(items.length);
    summary.append(strong, document.createTextNode(` ${items.length === 1 ? text.result : text.results}`));
    const separator = document.createElement("span"); separator.textContent = "·"; summary.append(separator);
    const sourceStrong = document.createElement("strong"); sourceStrong.textContent = String(sourceCount);
    summary.append(sourceStrong, document.createTextNode(` ${sourceCount === 1 ? text.source : text.sources}`));
  }
  function renderEmpty(title, body, error = false) {
    list.replaceChildren();
    const box = document.createElement("div"); box.className = error ? "archive-error" : "archive-empty";
    const strong = document.createElement("strong"); strong.textContent = title;
    const p = document.createElement("span"); p.textContent = body;
    box.append(strong,p); list.append(box);
  }
  function render() {
    const items = filteredItems(); renderSummary(items); list.replaceChildren();
    if (!state.items.length) { renderEmpty(text.noArchiveTitle, text.noArchiveBody); return; }
    if (!items.length) { renderEmpty(text.emptyTitle, text.emptyBody); return; }
    const fragment = document.createDocumentFragment();
    items.forEach(item => {
      const article = document.createElement("article"); article.className = "archive-item";
      const date = document.createElement("div"); date.className = "archive-date";
      const publishedLabel = document.createElement("span"); publishedLabel.textContent = text.published;
      const published = document.createElement("strong"); published.textContent = formatDate(item.published_at || item.observed_at);
      date.append(publishedLabel, published);
      if (item.observed_at && item.observed_at !== item.published_at) {
        const observed = document.createElement("span"); observed.textContent = `${text.observed}: ${formatDate(item.observed_at)}`; date.append(observed);
      }
      const main = document.createElement("div"); main.className = "archive-item-main";
      const badges = document.createElement("div"); badges.className = "archive-badges";
      const signal = classifySignal(item.signal); badges.append(makeBadge(signal.label, signal.className));
      if (item.official) badges.append(makeBadge(text.official, "is-official"));
      if (item.tier !== undefined && item.tier !== null && String(item.tier).trim()) badges.append(makeBadge(`${text.tier} ${item.tier}`));
      const h2 = document.createElement("h2");
      if (item.source_url) { const link = document.createElement("a"); link.href = item.source_url; link.target = "_blank"; link.rel = "noopener noreferrer nofollow"; link.textContent = item.title || item.source_url; h2.append(link); }
      else h2.textContent = item.title || text.relevant;
      const source = document.createElement("p"); source.className = "archive-item-source"; source.textContent = item.source_name || new URL(item.source_url).hostname;
      main.append(badges,h2,source);
      const action = document.createElement("div"); action.className = "archive-item-action";
      if (item.source_url) { const link = document.createElement("a"); link.href = item.source_url; link.target = "_blank"; link.rel = "noopener noreferrer nofollow"; link.textContent = text.openSource; action.append(link); }
      article.append(date,main,action); fragment.append(article);
    });
    list.append(fragment);
  }
  async function load() {
    try {
      const response = await fetch(`/status.json?v=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      state.items = cleanedItems(data); state.checkedAt = data.checked_at || null;
      state.days = Number(data?.diagnostics?.evidence_archive_days || 14);
      renderMetrics(); fillSources(); render();
    } catch (error) {
      console.error(error); renderEmpty(text.loadErrorTitle, text.loadErrorBody, true);
      summary.textContent = "";
    }
  }
  search?.addEventListener("input", event => { state.query = event.target.value; render(); });
  sourceSelect?.addEventListener("change", event => { state.source = event.target.value; render(); });
  reset?.addEventListener("click", () => { state.query = ""; state.source = "all"; search.value = ""; sourceSelect.value = "all"; render(); search.focus(); });
  document.addEventListener("DOMContentLoaded", load);
})();
