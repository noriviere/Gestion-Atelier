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

// Formulaires de fiche : lignes de paramètres et de consommables ajoutées à la volée, filtre des outils,
// zone de dépôt de fichier.
(function () {
  document.querySelectorAll("[data-formset]").forEach(function (zone) {
    var prefixe = zone.dataset.formset;
    var champTotal = zone.querySelector("[name=" + prefixe + "-TOTAL_FORMS]");
    var corps = zone.querySelector("[data-lignes]");
    var modele = zone.querySelector("template[data-modele]");

    zone.querySelector('[data-action="ajouter-ligne"]').addEventListener("click", function () {
      var numero = parseInt(champTotal.value, 10);
      var conteneur = document.createElement("tbody");
      conteneur.innerHTML = modele.innerHTML.replace(/__prefix__/g, numero);
      var nouvelleLigne = conteneur.firstElementChild;
      corps.appendChild(nouvelleLigne);
      champTotal.value = numero + 1;
      var premierChamp = nouvelleLigne.querySelector("input:not([type=hidden]), select");
      if (premierChamp) premierChamp.focus();
    });

    // Une ligne pas encore enregistrée se vide simplement : Django ignore les lignes vides.
    corps.addEventListener("click", function (evenement) {
      var bouton = evenement.target.closest('[data-action="retirer-ligne"]');
      if (!bouton) return;
      var ligne = bouton.closest("tr");
      ligne.querySelectorAll("input:not([type=hidden]), select").forEach(function (champ) {
        champ.value = "";
      });
      ligne.hidden = true;
    });
  });

  document.querySelectorAll("[data-filtre-choix]").forEach(function (champFiltre) {
    var liste = document.querySelector(champFiltre.dataset.filtreChoix);
    if (!liste) return;
    champFiltre.addEventListener("input", function () {
      var texte = champFiltre.value.trim().toLowerCase();
      liste.querySelectorAll("label").forEach(function (option) {
        var coche = option.querySelector("input").checked;
        option.parentElement.hidden = !coche && texte !== "" && option.textContent.toLowerCase().indexOf(texte) === -1;
      });
    });
  });

  document.querySelectorAll(".zone-depot").forEach(function (zone) {
    var champFichier = zone.querySelector("input[type=file]");
    var texte = zone.querySelector("span");
    var texteInitial = texte.innerHTML;
    var champTitre = zone.closest("form").querySelector("[name=titre]");
    champFichier.addEventListener("change", function () {
      var fichier = champFichier.files[0];
      if (!fichier) {
        texte.innerHTML = texteInitial;
        return;
      }
      texte.textContent = fichier.name;
      zone.classList.add("fichier-choisi");
      // Le nom du fichier sert de titre par défaut.
      if (champTitre && !champTitre.value) champTitre.value = fichier.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ");
    });
    ["dragenter", "dragover"].forEach(function (nom) {
      zone.addEventListener(nom, function () { zone.classList.add("survol-depot"); });
    });
    ["dragleave", "drop"].forEach(function (nom) {
      zone.addEventListener(nom, function () { zone.classList.remove("survol-depot"); });
    });
  });
})();
