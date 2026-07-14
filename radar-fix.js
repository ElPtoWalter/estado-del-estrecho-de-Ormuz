(() => {
  "use strict";

  const init = () => {
    const button = document.getElementById("loadTrafficMap");
    const placeholder = document.getElementById("trafficPlaceholder");

    if (!button || !placeholder || button.dataset.externalRadarReady === "true") {
      return;
    }

    button.dataset.externalRadarReady = "true";

    const isEnglish = document.documentElement.lang === "en";
    const liveMapUrl =
      "https://www.marinetraffic.com/en/ais/home/centerx:57.7/centery:25.8/zoom:6";

    const heading = placeholder.querySelector("h3");
    const description = placeholder.querySelector(
      ".traffic-placeholder-content > p:not(.traffic-consent)"
    );
    const consent = placeholder.querySelector(".traffic-consent");

    if (heading) {
      heading.textContent = isEnglish
        ? "MarineTraffic live AIS map"
        : "Mapa AIS en directo de MarineTraffic";
    }

    if (description) {
      description.textContent = isEnglish
        ? "The live maritime map will open in a new tab, centred on the Strait of Hormuz."
        : "El mapa marítimo en directo se abrirá en una pestaña nueva, centrado en el estrecho de Ormuz.";
    }

    if (consent) {
      consent.textContent = isEnglish
        ? "External MarineTraffic service. Its own privacy policy and terms apply."
        : "Servicio externo de MarineTraffic. Se aplican su política de privacidad y sus condiciones.";
    }

    button.textContent = isEnglish
      ? "Open live maritime radar ↗"
      : "Abrir radar marítimo en directo ↗";

    button.addEventListener("click", () => {
      const radarWindow = window.open(
        liveMapUrl,
        "_blank",
        "noopener,noreferrer"
      );

      if (!radarWindow) {
        window.location.href = liveMapUrl;
      }
    });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
