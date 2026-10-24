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

// Formulaires à confirmer avant envoi (suppression d'un outil, par exemple).
(function () {
  document.querySelectorAll("form[data-confirmation]").forEach(function (formulaire) {
    formulaire.addEventListener("submit", function (evenement) {
      if (!window.confirm(formulaire.dataset.confirmation)) {
        evenement.preventDefault();
        evenement.stopImmediatePropagation();
      }
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

// Fiche article : le numéro de plan n'est demandé que pour un design interne.
(function () {
  var choixOrigine = document.querySelectorAll('input[name="origine"]');
  var champPlan = document.querySelector(".champ-plan");
  if (!choixOrigine.length || !champPlan) return;

  function afficherChampPlan() {
    var origineChoisie = document.querySelector('input[name="origine"]:checked');
    champPlan.hidden = !origineChoisie || origineChoisie.value !== "interne";
  }

  choixOrigine.forEach(function (choix) {
    choix.addEventListener("change", afficherChampPlan);
  });
  afficherChampPlan();
})();
