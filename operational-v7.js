(() => {
  "use strict";
  const lang = document.documentElement.lang === "en" ? "en" : "es";
  const endpoint = "/operational-intelligence.json?v=";

  function familyClass(family) {
    if (family === "OPEN") return "is-open";
    if (family === "CLOSED") return "is-closed";
    return "is-uncertain";
  }

  function confidenceText(value) {
    const labels = {
      es: { ALTA: "Alta", MEDIA: "Media", BAJA: "Baja" },
      en: { ALTA: "High", MEDIA: "Medium", BAJA: "Low" }
    };
    return labels[lang][value] || value || "—";
  }

  function apply(data) {
    if (!data || !data.state) return;
    const hero = document.getElementById("statusHero");
    const word = document.getElementById("statusWord");
    const operational = document.getElementById("operationalLabel");
    const summary = document.getElementById("statusSummary");
    const confidence = document.getElementById("confidence");
    const valid = document.getElementById("lastValidAt");

    if (hero) {
      hero.classList.remove("is-loading", "is-open", "is-closed", "is-uncertain", "is-provisional");
      hero.classList.add(familyClass(data.family));
      hero.dataset.intelligenceState = data.state;
      hero.dataset.status = data.family === "OPEN" ? "ABIERTO" : data.family === "CLOSED" ? "CERRADO" : "INCIERTO";
    }
    if (word) {
      word.textContent = lang === "es" ? data.label_es : data.label_en;
      word.classList.toggle("is-long-status", String(word.textContent).length > 18);
    }
    if (operational) operational.textContent = lang === "es" ? data.operational_label_es : data.operational_label_en;
    if (summary) summary.textContent = lang === "es" ? data.summary_es : data.summary_en;
    if (confidence) {
      confidence.textContent = confidenceText(data.confidence);
      confidence.className = data.confidence === "ALTA" ? "confidence-high" : data.confidence === "MEDIA" ? "confidence-medium" : "confidence-low";
    }
    if (valid && data.latest_confirmed_transit_at) {
      const d = new Date(data.latest_confirmed_transit_at);
      if (!Number.isNaN(d.valueOf())) {
        valid.textContent = new Intl.DateTimeFormat(
          lang === "es" ? "es-ES" : "en-GB",
          { dateStyle: "long", timeStyle: "short", timeZone: lang === "es" ? "Europe/Madrid" : "UTC" }
        ).format(d) + (lang === "en" ? " UTC" : "");
      }
    }

    const block = document.querySelector("[data-opintel-state]");
    if (block) {
      block.dataset.opintelState = data.state;
      const label = block.querySelector("[data-opintel-label]");
      const conf = block.querySelector("[data-opintel-confidence]");
      const sum = block.querySelector("[data-opintel-summary]");
      if (label) label.textContent = lang === "es" ? data.label_es : data.label_en;
      if (conf) conf.textContent = (lang === "es" ? "Confianza: " : "Confidence: ") + confidenceText(data.confidence);
      if (sum) sum.textContent = lang === "es" ? data.summary_es : data.summary_en;
      const dimensionLabels = lang === "es" ? data.dimension_labels_es : data.dimension_labels_en;
      ["passage", "traffic", "access", "risk"].forEach(key => {
        const el = block.querySelector(`[data-opintel-${key}]`);
        if (el && dimensionLabels) el.textContent = dimensionLabels[key] || "—";
      });
    }
  }

  function load() {
    fetch(endpoint + Date.now(), { cache: "no-store" })
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(apply)
      .catch(err => console.debug("Operational Intelligence V7 unavailable", err));
  }

  window.addEventListener("load", () => {
    window.setTimeout(load, 120);
    window.setTimeout(load, 1800);
  });
})();
