// Comportements communs à toutes les pages : bouton de thème et boutons d'impression.
(function () {
  var CLE_THEME = "gestion-atelier-theme";
  var racine = document.documentElement;

  function enregistrerTheme(theme) {
    try {
      window.localStorage.setItem(CLE_THEME, theme);
    } catch (stockageIndisponible) {
      // Navigation privée ou stockage bloqué : le thème s'applique sans être mémorisé.
    }
  }

  function basculerTheme() {
    var nouveauTheme = racine.getAttribute("data-theme") === "sombre" ? "clair" : "sombre";
    racine.classList.add("changement-theme");
    racine.setAttribute("data-theme", nouveauTheme);
    enregistrerTheme(nouveauTheme);
    window.setTimeout(function () {
      racine.classList.remove("changement-theme");
    }, 350);
  }

  document.querySelectorAll('[data-action="changer-theme"]').forEach(function (bouton) {
    bouton.addEventListener("click", basculerTheme);
  });

  document.querySelectorAll('[data-action="imprimer"]').forEach(function (bouton) {
    bouton.addEventListener("click", function () {
      window.print();
    });
  });
})();
