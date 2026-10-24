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

// Affichage sur téléphone : menu repliable et tableaux présentés en fiches.
(function () {
  var boutonMenu = document.querySelector('[data-action="ouvrir-menu"]');
  if (boutonMenu) {
    var entete = boutonMenu.closest("header");
    boutonMenu.addEventListener("click", function () {
      var menuOuvert = entete.classList.toggle("menu-ouvert");
      boutonMenu.setAttribute("aria-expanded", menuOuvert ? "true" : "false");
      boutonMenu.setAttribute("aria-label", menuOuvert ? "Fermer le menu" : "Ouvrir le menu");
    });
  }

  // Chaque cellule reçoit le titre de sa colonne, affiché devant la valeur sur petit écran.
  document.querySelectorAll("main table").forEach(function (tableau) {
    var ligneEntete = tableau.rows[0];
    if (!ligneEntete || !ligneEntete.querySelector("th")) return;
    var titresColonnes = Array.prototype.map.call(ligneEntete.cells, function (cellule) {
      return cellule.textContent.trim();
    });
    ligneEntete.classList.add("ligne-entete");
    Array.prototype.slice.call(tableau.rows, 1).forEach(function (ligne) {
      Array.prototype.forEach.call(ligne.cells, function (cellule, position) {
        if (titresColonnes[position] && cellule.colSpan === 1) {
          cellule.setAttribute("data-titre", titresColonnes[position]);
        }
      });
    });
  });
})();

// Comptage d'inventaire : écart avec le stock théorique, affiché pendant la saisie.
(function () {
  function lireNombre(texte) {
    return parseFloat(String(texte).replace(",", "."));
  }

  function afficherEcart(champ) {
    var celluleEcart = champ.closest("tr").querySelector(".ecart-saisi");
    if (!celluleEcart) return;
    var quantiteComptee = lireNombre(champ.value);
    celluleEcart.innerHTML = "";
    if (champ.value.trim() === "" || isNaN(quantiteComptee)) return;
    var ecart = Math.round((quantiteComptee - lireNombre(champ.dataset.stockTheorique)) * 100) / 100;
    var etiquette = document.createElement("span");
    etiquette.className = "etiquette " + (ecart < 0 ? "alerte" : ecart > 0 ? "attention" : "ok");
    etiquette.textContent = (ecart > 0 ? "+" : ecart < 0 ? "−" : "") + Math.abs(ecart).toLocaleString("fr-FR");
    celluleEcart.appendChild(etiquette);
  }

  document.querySelectorAll("input.compte[data-stock-theorique]").forEach(function (champ) {
    champ.addEventListener("input", function () {
      afficherEcart(champ);
    });
  });
})();
