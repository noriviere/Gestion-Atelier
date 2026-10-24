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
    var afficherMenu = function (menuOuvert) {
      entete.classList.toggle("menu-ouvert", menuOuvert);
      boutonMenu.setAttribute("aria-expanded", menuOuvert ? "true" : "false");
      boutonMenu.setAttribute("aria-label", menuOuvert ? "Fermer le menu" : "Ouvrir le menu");
    };
    boutonMenu.addEventListener("click", function () {
      afficherMenu(!entete.classList.contains("menu-ouvert"));
    });
    // Échap referme le menu et rend le focus au bouton, pour qui navigue au clavier.
    document.addEventListener("keydown", function (evenement) {
      if (evenement.key === "Escape" && entete.classList.contains("menu-ouvert")) {
        afficherMenu(false);
        boutonMenu.focus();
      }
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

// Recherche globale : filtre les résultats à la frappe, sans recharger la page.
(function () {
  var champRecherche = document.querySelector("[data-recherche-globale]");
  if (!champRecherche) return;
  var bilan = document.querySelector("[data-recherche-bilan]");
  var messageVide = document.querySelector("[data-recherche-vide]");
  var groupes = document.querySelectorAll("[data-groupe-resultats]");

  // Même règle que la recherche côté serveur : minuscules, sans accents.
  function normaliser(texte) {
    return texte.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  function filtrerResultats() {
    var mots = normaliser(champRecherche.value).split(/\s+/).filter(Boolean);
    var nombreTotal = 0;
    groupes.forEach(function (groupe) {
      var nombreDansLeGroupe = 0;
      groupe.querySelectorAll("li[data-texte]").forEach(function (ligne) {
        var visible = mots.every(function (mot) {
          return ligne.dataset.texte.indexOf(mot) !== -1;
        });
        ligne.hidden = !visible;
        if (visible) nombreDansLeGroupe += 1;
      });
      groupe.hidden = nombreDansLeGroupe === 0;
      groupe.querySelector("[data-nombre-resultats]").textContent = "(" + nombreDansLeGroupe + ")";
      nombreTotal += nombreDansLeGroupe;
    });
    if (messageVide) messageVide.hidden = nombreTotal > 0;
    if (bilan) bilan.textContent = mots.length ? nombreTotal + " résultat" + (nombreTotal > 1 ? "s" : "") : "";
  }

  // Sur la démo statique, la page reçoit la recherche par l'adresse et non par le serveur.
  var texteDansLAdresse = new URLSearchParams(window.location.search).get("q");
  if (texteDansLAdresse && !champRecherche.value) champRecherche.value = texteDansLAdresse;

  champRecherche.addEventListener("input", filtrerResultats);
  filtrerResultats();
})();
