// Applique le thème (clair ou sombre) avant l'affichage de la page, pour éviter un clignotement.
// Choix enregistré dans le navigateur ; à défaut, on suit le réglage du système.
// Espace commun aux scripts de l'application (complété par atelier.js) : évite les variables globales en vrac.
window.Atelier = { CLE_THEME: "gestion-atelier-theme" };

(function appliquerThemeEnregistre() {
  var CLE_THEME = window.Atelier.CLE_THEME;
  var themeEnregistre = null;
  try {
    themeEnregistre = window.localStorage.getItem(CLE_THEME);
  } catch (stockageIndisponible) {
    themeEnregistre = null;
  }
  var systemeEnSombre = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  var theme = themeEnregistre || (systemeEnSombre ? "sombre" : "clair");
  document.documentElement.setAttribute("data-theme", theme);
  // Sans JavaScript, le menu reste déplié sur téléphone : le repli ne s'applique qu'avec la classe « js ».
  document.documentElement.classList.add("js");
})();
