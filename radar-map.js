(() => {
  "use strict";

  const english = document.documentElement.lang === "en";
  const copy = english
    ? {
        loading: "Loading the AIS radar inside this page…",
        inserted: "External viewer inserted. If the map is missing or shows an error, use the alternative MarineTraffic link.",
        failed: "The embedded map could not be loaded. Use the alternative MarineTraffic link.",
        retry: "Try loading the radar again",
        title: "Live AIS map of the Strait of Hormuz"
      }
    : {
        loading: "Cargando el radar AIS dentro de la página…",
        inserted: "Visor externo insertado. Si no aparece el mapa o muestra un error, utiliza el enlace alternativo de MarineTraffic.",
        failed: "No se pudo cargar el mapa integrado. Utiliza el enlace alternativo de MarineTraffic.",
        retry: "Intentar cargar el radar de nuevo",
        title: "Mapa AIS en directo del estrecho de Ormuz"
      };

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-load-ais-map]");
    if (!button) return;

    const container = document.getElementById("marineMapContainer");
    const placeholder = document.getElementById("marineMapPlaceholder");
    const toolbar = document.getElementById("marineMapToolbar");
    const status = document.getElementById("marineMapStatus");

    if (
      !container ||
      container.dataset.aisLoading === "true" ||
      container.dataset.aisInserted === "true"
    ) {
      return;
    }

    container.dataset.aisLoading = "true";
    button.disabled = true;
    button.textContent = copy.loading;
    if (status) status.textContent = copy.loading;

    Object.assign(window, {
      mst_width: "100%",
      mst_height: "520px",
      mst_border: "0",
      mst_map_style: "simple",
      mst_lat: "26.55",
      mst_lng: "56.32",
      mst_zoom: "7",
      mst_show_names: "1",
      mst_scroll_wheel: "false",
      mst_show_menu: "true"
    });

    const script = document.createElement("script");
    script.id = "myshiptrackingscript";
    script.src = "https://www.myshiptracking.com/js/widgetApi.js";
    script.async = true;

    let settled = false;
    let timeout;
    const fail = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeout);
      container.dataset.aisLoading = "false";
      button.disabled = false;
      button.textContent = copy.retry;
      if (status) status.textContent = copy.failed;
      script.remove();
    };

    script.addEventListener("error", fail, { once: true });
    script.addEventListener(
      "load",
      () => {
        if (settled) return;
        const frame = container.querySelector("iframe");
        if (!frame) {
          fail();
          return;
        }

        frame.classList.add("traffic-map-frame");
        frame.style.height = "";
        frame.title = copy.title;
        frame.loading = "eager";
        frame.referrerPolicy = "strict-origin-when-cross-origin";

        settled = true;
        window.clearTimeout(timeout);
        container.dataset.aisLoading = "false";
        container.dataset.aisInserted = "true";
        button.disabled = false;
        button.textContent = copy.retry;
        if (placeholder) placeholder.hidden = true;
        if (toolbar) toolbar.hidden = false;
        // A cross-origin iframe load event also fires for error pages (including HTTP 500).
        // Insertion is observable; supplier availability and AIS coverage are not verified here.
        if (status) status.textContent = copy.inserted;
      },
      { once: true }
    );

    timeout = window.setTimeout(fail, 15000);
    container.insertBefore(script, toolbar || null);
  });
})();
