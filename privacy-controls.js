(() => {
  "use strict";

  window.googlefc = window.googlefc || {};
  window.googlefc.callbackQueue = window.googlefc.callbackQueue || [];

  const language = document.documentElement.lang === "en" ? "en" : "es";
  const fallback = language === "en" ? "/en-cookies.html#preferences" : "/cookies.html#preferencias";

  function openGooglePrivacyMessage(event) {
    const trigger = event.target.closest("[data-google-consent]");
    if (!trigger) return;

    event.preventDefault();

    if (
      window.googlefc &&
      Array.isArray(window.googlefc.callbackQueue) &&
      typeof window.googlefc.showRevocationMessage === "function"
    ) {
      window.googlefc.callbackQueue.push(window.googlefc.showRevocationMessage);
      return;
    }

    if (window.location.pathname !== fallback.split("#")[0]) {
      window.location.href = fallback;
    }
  }

  document.addEventListener("click", openGooglePrivacyMessage);
})();
