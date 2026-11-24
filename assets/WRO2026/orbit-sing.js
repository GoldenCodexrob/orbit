(function () {
  "use strict";

  const baseOpen = window.openApp;

  function go(url) {
    window.location.href = url;
  }

  window.openApp = function (name) {
    name = String(name || "");
    if (name === "idioma" || name === "aprender") return go("../aprender/aprende-con-orbit.html");
    if (name === "home" || name === "launcher") return go("../inicio/index.html");
    return baseOpen.apply(this, arguments);
  };

  window.goToHome = function () {
    try { window.openApp("canta"); } catch (_) {}
  };

  window.goToMenu = function () {
    go("../inicio/index.html");
  };

  window.showLanguageSelect = function () {
    go("../aprender/aprende-con-orbit.html");
  };

  window.chooseLearningLanguage = function (lang) {
    const value = String(lang || "").toLowerCase()
      .replace(/[â€™']/g, "")
      .replace(/í/g, "i")
      .replace(/á/g, "a")
      .replace(/ñ/g, "n");
    if (value !== "karina" && value !== "taino") return false;
    try { localStorage.setItem("orbit.learning.lang.v1", value); } catch (_) {}
    go("../aprender/aprende-con-orbit.html");
    return true;
  };

  window.addEventListener("DOMContentLoaded", function () {
    window.setTimeout(function () {
      window.openApp("canta");
    }, 0);
  });
})();
