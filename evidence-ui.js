(() => {
  "use strict";

  const lang = document.documentElement.lang === "en" ? "en" : "es";

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat(lang === "es" ? "es-ES" : "en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: lang === "es" ? "Europe/Madrid" : "UTC"
    }).format(date) + (lang === "en" ? " UTC" : "");
  }

  function ensureBadge(container) {
    let badge = document.getElementById("evidenceContextBadge");
    if (!badge) {
      badge = document.createElement("span");
      badge.id = "evidenceContextBadge";
      badge.className = "evidence-context-badge";
      container.append(badge);
    }
    return badge;
  }

  function renderContext(data) {
    const section = document.querySelector(".evidence-section");
    if (!section) return;

    const heading = document.getElementById("evidenceHeading") || section.querySelector("h2");
    const intro = document.getElementById("evidenceIntro") || section.querySelector(".section-heading p");
    const context = data && typeof data.evidence_context === "object" ? data.evidence_context : null;
    const mode = context?.mode || (Array.isArray(data?.evidence) && data.evidence.length ? "current" : "none");

    const headingText = lang === "es" ? context?.heading_es : context?.heading_en;
    const description = lang === "es" ? context?.description_es : context?.description_en;
    if (heading && headingText) heading.textContent = headingText;
    if (intro && description) intro.textContent = description;

    section.classList.toggle("is-carried-evidence", mode === "carried");
    const headingContainer = heading?.parentElement;
    if (!headingContainer) return;

    const badge = ensureBadge(headingContainer);
    if (mode === "current") {
      const count = Number(context?.current_cycle_count || data?.evidence?.length || 0);
      badge.textContent = lang === "es"
        ? `${count} señal${count === 1 ? "" : "es"} del último ciclo`
        : `${count} signal${count === 1 ? "" : "s"} from the latest cycle`;
      badge.hidden = false;
      return;
    }

    if (mode === "carried") {
      const date = formatDate(context?.as_of);
      badge.textContent = lang === "es"
        ? `Evidencias anteriores${date ? ` · hasta ${date}` : ""}`
        : `Earlier evidence${date ? ` · through ${date}` : ""}`;
      badge.hidden = false;
      return;
    }

    badge.hidden = true;
  }

  async function loadContext() {
    try {
      const response = await fetch(`/status.json?v=${Date.now()}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      renderContext(await response.json());
    } catch (error) {
      console.debug("Evidence context could not be loaded", error);
    }
  }

  document.addEventListener("DOMContentLoaded", loadContext);
})();
