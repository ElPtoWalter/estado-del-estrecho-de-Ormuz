(() => {
  "use strict";

  const lang = document.documentElement.lang === "en" ? "en" : "es";
  const BASE = (() => {
    const script = document.currentScript;
    if (script && script.src) return new URL(".", script.src).href;
    return new URL(".", window.location.href).href;
  })();

  const labels = {
    es: {
      status: { ABIERTO: "ABIERTO", CERRADO: "CERRADO", INCIERTO: "INCIERTO" },
      confidence: { ALTA: "Alta", MEDIA: "Media", BAJA: "Baja" },
      signals: {
        OPEN_OPERATIONAL: "Tránsito operativo",
        CLOSED_OPERATIONAL: "Interrupción operativa",
        CLOSURE_DECLARED: "Declaración de cierre",
        RISK_RESTRICTION: "Riesgo o restricción"
      },
      source: "Fuente",
      official: "oficial",
      lastCheck: "Última comprobación",
      lastValid: "Última confirmación válida",
      unavailable: "No disponible",
      noEvidence: "No hay pruebas públicas suficientes para mostrar.",
      notificationEnabled: "Avisos activados. Esta pestaña comprobará cambios mientras permanezca abierta.",
      notificationDenied: "El navegador no ha concedido permiso para mostrar avisos.",
      notificationUnsupported: "Este navegador no admite notificaciones web.",
      copied: "Enlace copiado al portapapeles.",
      copyFailed: "No se pudo copiar automáticamente.",
      changedTitle: "Cambio en el estrecho de Ormuz",
      changedBody: "Nuevo estado: {status}. {summary}",
      checkFailed: "No se pudo cargar la actualización más reciente.",
      historyEvents: "Cambios registrados",
      historyLast: "Último cambio",
      historyCurrent: "Estado actual",
      none: "Ninguno"
    },
    en: {
      status: { ABIERTO: "OPEN", CERRADO: "CLOSED", INCIERTO: "UNCERTAIN" },
      confidence: { ALTA: "High", MEDIA: "Medium", BAJA: "Low" },
      signals: {
        OPEN_OPERATIONAL: "Operational transit",
        CLOSED_OPERATIONAL: "Operational interruption",
        CLOSURE_DECLARED: "Closure declaration",
        RISK_RESTRICTION: "Risk or restriction"
      },
      source: "Source",
      official: "official",
      lastCheck: "Last check",
      lastValid: "Last valid confirmation",
      unavailable: "Unavailable",
      noEvidence: "There is not enough public evidence to display.",
      notificationEnabled: "Alerts enabled. This tab will check for changes while it remains open.",
      notificationDenied: "The browser did not grant permission to display alerts.",
      notificationUnsupported: "This browser does not support web notifications.",
      copied: "Link copied to the clipboard.",
      copyFailed: "The link could not be copied automatically.",
      changedTitle: "Strait of Hormuz status change",
      changedBody: "New status: {status}. {summary}",
      checkFailed: "The latest update could not be loaded.",
      historyEvents: "Recorded changes",
      historyLast: "Last change",
      historyCurrent: "Current status",
      none: "None"
    }
  }[lang];

  const statusClass = status => ({ ABIERTO: "is-open", CERRADO: "is-closed", INCIERTO: "is-uncertain" }[status] || "is-uncertain");
  const confidenceClass = value => ({ ALTA: "confidence-high", MEDIA: "confidence-medium", BAJA: "confidence-low" }[value] || "confidence-low");

  function formatDate(value) {
    if (!value) return labels.unavailable;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return labels.unavailable;
    return new Intl.DateTimeFormat(lang === "es" ? "es-ES" : "en-GB", {
      dateStyle: "long",
      timeStyle: "short",
      timeZone: lang === "es" ? "Europe/Madrid" : "UTC"
    }).format(date) + (lang === "en" ? " UTC" : "");
  }

  async function fetchJson(file) {
    const response = await fetch(`${BASE}${file}?v=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
    return response.json();
  }

  function createEvidenceCard(item) {
    const article = document.createElement("article");
    article.className = "evidence-card";

    const meta = document.createElement("div");
    meta.className = "evidence-meta";
    const signal = document.createElement("span");
    const official = item.official ? ` · ${labels.official}` : "";
    signal.textContent = `${labels.signals[item.signal] || item.signal || "Signal"}${official}`;
    const time = document.createElement("time");
    time.dateTime = item.published_at || "";
    time.textContent = formatDate(item.published_at);
    meta.append(signal, time);

    const heading = document.createElement("h3");
    const link = document.createElement("a");
    link.href = item.source_url || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = item.title || labels.source;
    heading.append(link);

    const source = document.createElement("p");
    source.textContent = item.source_name || labels.source;
    article.append(meta, heading, source);
    return article;
  }

  function renderStatus(data) {
    const hero = document.getElementById("statusHero");
    if (!hero) return;
    const status = labels.status[data.status] ? data.status : "INCIERTO";
    hero.classList.remove("is-open", "is-closed", "is-uncertain");
    hero.classList.add(statusClass(status));
    hero.dataset.status = status;

    const word = document.getElementById("statusWord");
    const operational = document.getElementById("operationalLabel");
    const summary = document.getElementById("statusSummary");
    const checked = document.getElementById("checkedAt");
    const confidence = document.getElementById("confidence");
    const valid = document.getElementById("lastValidAt");
    const evidence = document.getElementById("evidenceList");

    if (word) word.textContent = labels.status[status];
    if (operational) operational.textContent = lang === "es" ? data.operational_label_es : data.operational_label_en;
    if (summary) summary.textContent = lang === "es" ? data.summary_es : data.summary_en;
    if (checked) checked.textContent = formatDate(data.checked_at);
    if (confidence) {
      confidence.textContent = labels.confidence[data.confidence] || labels.confidence.BAJA;
      confidence.className = confidenceClass(data.confidence);
    }
    if (valid) valid.textContent = data.last_valid_confirmation ? formatDate(data.last_valid_confirmation.at) : labels.unavailable;
    if (evidence) {
      evidence.replaceChildren();
      const items = Array.isArray(data.evidence) ? data.evidence.slice(0, 4) : [];
      if (!items.length) {
        const empty = document.createElement("p");
        empty.className = "empty-state";
        empty.textContent = labels.noEvidence;
        evidence.append(empty);
      } else {
        items.forEach(item => evidence.append(createEvidenceCard(item)));
      }
    }

    window.ormuzCurrentStatus = data;
  }

  function createHistoryItem(event) {
    const article = document.createElement("article");
    article.id = event.id || "";
    article.className = `timeline-item ${statusClass(event.status)}`;
    const marker = document.createElement("div");
    marker.className = "timeline-marker";
    marker.setAttribute("aria-hidden", "true");

    const content = document.createElement("div");
    content.className = "timeline-content";
    const head = document.createElement("div");
    head.className = "timeline-head";
    const strong = document.createElement("strong");
    strong.textContent = labels.status[event.status] || labels.status.INCIERTO;
    const time = document.createElement("time");
    time.dateTime = event.at || "";
    time.textContent = formatDate(event.at);
    head.append(strong, time);

    const operation = document.createElement("p");
    operation.className = "timeline-operation";
    operation.textContent = lang === "es" ? event.operational_label_es : event.operational_label_en;
    const summary = document.createElement("p");
    summary.textContent = lang === "es" ? event.summary_es : event.summary_en;
    content.append(head, operation, summary);

    if (event.source_url && event.source_name) {
      const source = document.createElement("a");
      source.href = event.source_url;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = `${labels.source}: ${event.source_name}`;
      content.append(source);
    }
    article.append(marker, content);
    return article;
  }

  function renderHistory(history, status) {
    const timeline = document.getElementById("historyTimeline");
    if (timeline) {
      timeline.replaceChildren();
      if (!Array.isArray(history) || !history.length) {
        const empty = document.createElement("p");
        empty.className = "empty-state";
        empty.textContent = labels.none;
        timeline.append(empty);
      } else {
        history.slice(0, 50).forEach(event => timeline.append(createHistoryItem(event)));
      }
    }

    const eventCount = document.getElementById("historyEventCount");
    const lastChange = document.getElementById("historyLastChange");
    const current = document.getElementById("historyCurrentStatus");
    if (eventCount) eventCount.textContent = Array.isArray(history) ? String(history.length) : "0";
    if (lastChange) lastChange.textContent = history && history[0] ? formatDate(history[0].at) : labels.none;
    if (current && status) current.textContent = labels.status[status.status] || labels.status.INCIERTO;
  }

  async function loadHome() {
    try {
      const [status, history] = await Promise.all([fetchJson("status.json"), fetchJson("history.json")]);
      renderStatus(status);
      renderRecentHistory(history);
      beginAlertPolling(status);
    } catch (error) {
      console.error(error);
      const summary = document.getElementById("statusSummary");
      if (summary) summary.textContent = labels.checkFailed;
    }
  }

  function renderRecentHistory(history) {
    const container = document.getElementById("recentHistory");
    if (!container) return;
    container.replaceChildren();
    const items = Array.isArray(history) ? history.slice(0, 3) : [];
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = labels.none;
      container.append(empty);
      return;
    }
    items.forEach(event => container.append(createHistoryItem(event)));
  }

  async function loadHistory() {
    try {
      const [history, status] = await Promise.all([fetchJson("history.json"), fetchJson("status.json")]);
      renderHistory(history, status);
    } catch (error) {
      console.error(error);
    }
  }

  function setAlertMessage(message) {
    const output = document.getElementById("alertStatus");
    if (output) output.textContent = message;
  }

  async function enableBrowserAlerts() {
    if (!("Notification" in window)) {
      setAlertMessage(labels.notificationUnsupported);
      return;
    }
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      setAlertMessage(labels.notificationDenied);
      return;
    }
    localStorage.setItem("ormuz-browser-alerts", "enabled");
    const status = window.ormuzCurrentStatus;
    if (status) {
      localStorage.setItem("ormuz-alert-last-key", `${status.status}|${status.operational_status}|${status.last_change_at || ""}`);
    }
    setAlertMessage(labels.notificationEnabled);
  }

  function beginAlertPolling(initialStatus) {
    if (localStorage.getItem("ormuz-browser-alerts") !== "enabled" || !("Notification" in window)) return;
    const initialKey = `${initialStatus.status}|${initialStatus.operational_status}|${initialStatus.last_change_at || ""}`;
    if (!localStorage.getItem("ormuz-alert-last-key")) localStorage.setItem("ormuz-alert-last-key", initialKey);
    window.setInterval(async () => {
      try {
        const latest = await fetchJson("status.json");
        const latestKey = `${latest.status}|${latest.operational_status}|${latest.last_change_at || ""}`;
        const previousKey = localStorage.getItem("ormuz-alert-last-key");
        if (previousKey && latestKey !== previousKey && Notification.permission === "granted") {
          const summary = lang === "es" ? latest.summary_es : latest.summary_en;
          const body = labels.changedBody
            .replace("{status}", labels.status[latest.status] || labels.status.INCIERTO)
            .replace("{summary}", summary || "");
          new Notification(labels.changedTitle, { body, icon: `${BASE}apple-touch-icon.png`, tag: "ormuz-status" });
        }
        localStorage.setItem("ormuz-alert-last-key", latestKey);
      } catch (error) {
        console.debug("Alert polling failed", error);
      }
    }, 5 * 60 * 1000);
  }

  async function copyValue(value) {
    try {
      await navigator.clipboard.writeText(value);
      setAlertMessage(labels.copied);
    } catch (error) {
      const textarea = document.createElement("textarea");
      textarea.value = value;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.append(textarea);
      textarea.select();
      const ok = document.execCommand("copy");
      textarea.remove();
      setAlertMessage(ok ? labels.copied : labels.copyFailed);
    }
  }

  function setupInteractions() {
    const navToggle = document.querySelector(".nav-toggle");
    const nav = document.querySelector(".site-nav");
    if (navToggle && nav) {
      navToggle.addEventListener("click", () => {
        const open = nav.classList.toggle("is-open");
        navToggle.setAttribute("aria-expanded", String(open));
      });
    }

    document.querySelectorAll("[data-enable-alerts]").forEach(button => button.addEventListener("click", enableBrowserAlerts));
    document.querySelectorAll("[data-copy-rss]").forEach(button => button.addEventListener("click", () => copyValue(`${BASE}feed.xml`)));
    document.querySelectorAll("[data-copy-api]").forEach(button => button.addEventListener("click", () => copyValue(`${BASE}status.json`)));
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupInteractions();
    const page = document.body.dataset.page;
    if (page === "home") loadHome();
    if (page === "history") loadHistory();
  });
})();
