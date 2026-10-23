// Applique le thème (clair ou sombre) avant l'affichage de la page, pour éviter un clignotement.
// Choix enregistré dans le navigateur ; à défaut, on suit le réglage du système.
(function appliquerThemeEnregistre() {
  var CLE_THEME = "gestion-atelier-theme";
  var themeEnregistre = null;
  try {
    themeEnregistre = window.localStorage.getItem(CLE_THEME);
  } catch (stockageIndisponible) {
    themeEnregistre = null;
  }
  var systemeEnSombre = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  var theme = themeEnregistre || (systemeEnSombre ? "sombre" : "clair");
  document.documentElement.setAttribute("data-theme", theme);
})();
