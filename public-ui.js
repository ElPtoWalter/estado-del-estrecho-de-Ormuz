/* Public interactions use only the content already rendered on the page. */
(() => {
  "use strict";
  const es = document.documentElement.lang !== "en";
  const nav = document.getElementById("site-nav");
  const toggle = document.querySelector(".nav-toggle");
  const closeMenu = () => {
    nav?.classList.remove("is-open");
    toggle?.setAttribute("aria-expanded", "false");
  };
  toggle?.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    nav?.classList.toggle("is-open", open);
  });
  nav?.addEventListener("click", event => { if (event.target.closest("a")) closeMenu(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") closeMenu(); });
  const year = document.getElementById("currentYear");
  if (year) year.textContent = String(new Date().getFullYear());

  const normalize = value => String(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  const search = document.getElementById("archiveSearch");
  const source = document.getElementById("archiveSource");
  const cards = [...document.querySelectorAll("[data-archive-item]")];
  function filterArchive() {
    const query = normalize(search?.value || "").trim();
    const selected = source?.value || "all";
    let count = 0;
    cards.forEach(card => {
      card.hidden = !(normalize(card.textContent).includes(query) && (selected === "all" || card.dataset.source === selected));
      if (!card.hidden) count++;
    });
    const summary = document.getElementById("archiveSummary");
    if (summary) summary.textContent = `${count} ${es ? "resultados" : "results"}`;
    const empty = document.querySelector("[data-archive-empty]");
    if (empty) empty.hidden = count !== 0;
  }
  search?.addEventListener("input", filterArchive);
  source?.addEventListener("change", filterArchive);
  document.getElementById("archiveReset")?.addEventListener("click", () => {
    if (search) search.value = "";
    if (source) source.value = "all";
    filterArchive(); search?.focus();
  });

  document.addEventListener("click", async event => {
    const button = event.target.closest("[data-copy], [data-copy-rss], [data-copy-target]");
    if (!button) return;
    const target = button.dataset.copyTarget ? document.querySelector(button.dataset.copyTarget) : null;
    const value = button.dataset.copy || (button.hasAttribute("data-copy-rss") ? new URL("/feed.xml", location.href).href : target?.value || target?.textContent || "");
    if (!value) return;
    let feedback = button.parentElement.querySelector(".copy-feedback");
    if (!feedback) {
      feedback = document.createElement("span"); feedback.className = "copy-feedback";
      feedback.setAttribute("role", "status"); button.after(feedback);
    }
    try {
      await navigator.clipboard.writeText(value);
      feedback.textContent = es ? "Copiado" : "Copied";
    } catch (_) {
      feedback.textContent = es ? "No se pudo copiar. Selecciona y copia el texto mostrado." : "Could not copy. Select and copy the displayed text.";
    }
  });
})();
