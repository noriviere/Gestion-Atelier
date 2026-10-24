// Démo statique (GitHub Pages) : simule dans le navigateur ce que fait le serveur.
// Rien n'est enregistré : les changements disparaissent au rechargement de la page.
(function () {
  var MENTION_DEMO = " (Démo : rien n'est enregistré.)";

  function afficherMessage(texte, estUneErreur) {
    var zonePrincipale = document.querySelector("main");
    var listeMessages = zonePrincipale.querySelector("ul.messages");
    if (!listeMessages) {
      listeMessages = document.createElement("ul");
      listeMessages.className = "messages";
      zonePrincipale.insertBefore(listeMessages, zonePrincipale.firstChild);
    }
    listeMessages.innerHTML = "";
    var message = document.createElement("li");
    if (estUneErreur) message.className = "error";
    message.textContent = texte;
    listeMessages.appendChild(message);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function lireNombre(texte) {
    return parseFloat(String(texte).replace(",", "."));
  }

  function formaterNombre(valeur) {
    return (Math.round(valeur * 100) / 100).toLocaleString("fr-FR");
  }

  function mettreEnEvidence(element) {
    element.classList.remove("mis-a-jour");
    void element.offsetWidth; // relance l'animation si elle vient d'être jouée
    element.classList.add("mis-a-jour");
  }

  // Le paramétrage passe par l'interface d'administration, absente de la démo statique.
  document.querySelectorAll("[data-demo-parametrage]").forEach(function (lien) {
    lien.addEventListener("click", function (evenement) {
      evenement.preventDefault();
      afficherMessage("Démo : le paramétrage (création et modification des articles, outils, produits, comptes) " +
        "se fait dans l'interface d'administration, disponible sur la version installée.");
    });
  });

  function simulerMouvementDeStock(formulaire, zoneStock) {
    var quantite = lireNombre(formulaire.querySelector("[name=quantite]").value);
    if (!(quantite > 0)) {
      afficherMessage("Saisissez une quantité positive.", true);
      return;
    }
    var typeMouvement = formulaire.querySelector("[name=type]:checked").value;
    var nouveauStock = lireNombre(zoneStock.dataset.stock) + (typeMouvement === "sortie" ? -quantite : quantite);
    var sousLeMini = nouveauStock <= lireNombre(zoneStock.dataset.mini);
    zoneStock.dataset.stock = nouveauStock;
    zoneStock.innerHTML = '<span class="etiquette ' + (sousLeMini ? "alerte" : "ok") + '">' +
      formaterNombre(nouveauStock) + " " + zoneStock.dataset.unite + (sousLeMini ? " – à commander" : "") + "</span>";
    mettreEnEvidence(zoneStock);
    formulaire.reset();
    afficherMessage((typeMouvement === "sortie" ? "Sortie" : "Entrée") + " de " + formaterNombre(quantite) +
      " simulée : nouveau stock " + formaterNombre(nouveauStock) + "." + MENTION_DEMO);
  }

  function simulerComptage(formulaire) {
    var champsRemplis = Array.prototype.filter.call(formulaire.querySelectorAll("input.compte"), function (champ) {
      return champ.value.trim() !== "";
    });
    if (!champsRemplis.length) {
      afficherMessage("Rien à enregistrer.", true);
      return;
    }
    var aujourdhui = new Date().toLocaleDateString("fr-FR");
    champsRemplis.forEach(function (champ) {
      var ligne = champ.closest("tr");
      var celluleStock = ligne.cells[2];
      var unite = celluleStock.textContent.trim().split(" ").slice(1).join(" ");
      celluleStock.textContent = champ.value.trim() + " " + unite;
      ligne.cells[3].textContent = aujourdhui;
      mettreEnEvidence(celluleStock);
      champ.value = "";
    });
    afficherMessage(champsRemplis.length + " comptage(s) simulé(s), stocks corrigés à l'écran." + MENTION_DEMO);
  }

  var zoneStock = document.getElementById("stock-actuel");
  document.querySelectorAll("form[method=post]").forEach(function (formulaire) {
    formulaire.addEventListener("submit", function (evenement) {
      evenement.preventDefault();
      if (formulaire.dataset.demoMessage) {
        // Commandes : le changement d'état est seulement annoncé.
        afficherMessage(formulaire.dataset.demoMessage + MENTION_DEMO);
      } else if (zoneStock && formulaire.querySelector("[name=quantite]")) {
        simulerMouvementDeStock(formulaire, zoneStock);
      } else {
        simulerComptage(formulaire);
      }
    });
  });

  // Filtres et recherches : appliqués directement sur les lignes du tableau.
  document.querySelectorAll("form.filtres").forEach(function (formulaire) {
    var tableau = document.querySelector("main table");
    if (!tableau) return;
    var champRecherche = formulaire.querySelector("[type=search]");
    var listesDeroulantes = formulaire.querySelectorAll("select");
    var casesACocher = formulaire.querySelectorAll("[type=checkbox]");

    function filtrerLignes(evenement) {
      if (evenement) evenement.preventDefault();
      var texteRecherche = champRecherche ? champRecherche.value.trim().toLowerCase() : "";
      Array.prototype.slice.call(tableau.rows, 1).forEach(function (ligne) {
        var visible = !texteRecherche || ligne.textContent.toLowerCase().indexOf(texteRecherche) !== -1;
        listesDeroulantes.forEach(function (liste) {
          // Une ligne peut porter plusieurs valeurs séparées par des espaces (ex. « passee en_cours »).
          var valeursDeLaLigne = (ligne.dataset[liste.name] || "").split(" ");
          if (liste.value && valeursDeLaLigne.indexOf(liste.value) === -1) visible = false;
        });
        casesACocher.forEach(function (caseACocher) {
          if (caseACocher.checked && ligne.dataset[caseACocher.name] !== "1") visible = false;
        });
        ligne.hidden = !visible;
      });
    }

    // La page exportée contient toutes les lignes : le filtre par défaut est appliqué à l'ouverture.
    if (formulaire.hasAttribute("data-filtrer-au-chargement")) filtrerLignes();
    formulaire.addEventListener("submit", filtrerLignes);
    formulaire.addEventListener("change", filtrerLignes);
    formulaire.addEventListener("input", filtrerLignes);
  });
})();
