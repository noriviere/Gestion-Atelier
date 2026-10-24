// Démo statique (GitHub Pages) : simule dans le navigateur ce que fait le serveur.
// Les mouvements de stock (sorties, entrées, comptages) sont gardés dans le navigateur
// et réaffichés sur toutes les pages ; « Remettre à zéro » revient aux données de départ.
// Les créations et modifications d'outils sont vérifiées puis confirmées, sans être conservées.
(function () {
  var CLE_ETAT = "gestion-atelier-demo";
  var CLE_MESSAGE = "gestion-atelier-demo-message";
  var MENTION_DEMO = " (Démo : gardé dans votre navigateur.)";

  // --- Mémoire de la démo ------------------------------------------------------
  function lireEtat() {
    try {
      var etat = JSON.parse(window.localStorage.getItem(CLE_ETAT) || "{}");
      return { stocks: etat.stocks || {}, comptages: etat.comptages || {}, mouvements: etat.mouvements || {} };
    } catch (stockageIndisponible) {
      return { stocks: {}, comptages: {}, mouvements: {} };
    }
  }

  function enregistrerEtat(etat) {
    try {
      window.localStorage.setItem(CLE_ETAT, JSON.stringify(etat));
    } catch (stockageIndisponible) {
      // Navigation privée : la saisie reste visible sur la page, sans être gardée.
    }
  }

  var etatDemo = lireEtat();

  // Message à afficher sur la page suivante, après une redirection simulée.
  function messageApresRedirection(texte, adresse) {
    try {
      window.sessionStorage.setItem(CLE_MESSAGE, texte);
    } catch (stockageIndisponible) {
      // Le message est perdu, la navigation se fait quand même.
    }
    window.location.href = adresse;
  }

  function lireMessageEnAttente() {
    try {
      var texte = window.sessionStorage.getItem(CLE_MESSAGE);
      window.sessionStorage.removeItem(CLE_MESSAGE);
      return texte;
    } catch (stockageIndisponible) {
      return null;
    }
  }

  // --- Affichage ----------------------------------------------------------------
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

  // Même rendu que le gabarit inventaire/_stock.html.
  function afficherStock(zoneStock, stock) {
    var sousLeMini = stock <= lireNombre(zoneStock.dataset.mini);
    var texte = zoneStock.dataset.prefixe + formaterNombre(stock) +
      (zoneStock.dataset.unite ? " " + zoneStock.dataset.unite : "");
    zoneStock.dataset.stock = stock;
    zoneStock.textContent = "";
    if (sousLeMini || zoneStock.dataset.etiquetteOk) {
      var etiquette = document.createElement("span");
      etiquette.className = "etiquette " + (sousLeMini ? "alerte" : "ok");
      etiquette.textContent = texte + (sousLeMini && zoneStock.dataset.mention ? " – à commander" : "");
      zoneStock.appendChild(etiquette);
    } else {
      zoneStock.textContent = texte;
    }
    var ligneDuTableau = zoneStock.closest("tr");
    if (ligneDuTableau && "alerte" in ligneDuTableau.dataset) ligneDuTableau.dataset.alerte = sousLeMini ? "1" : "";
  }

  function zonesStockDeLArticle(article) {
    return document.querySelectorAll('[data-stock-article="' + article + '"]');
  }

  function stockActuel(article) {
    if (article in etatDemo.stocks) return etatDemo.stocks[article];
    var zoneStock = zonesStockDeLArticle(article)[0];
    return zoneStock ? lireNombre(zoneStock.dataset.stock) : 0;
  }

  function afficherMouvement(liste, mouvement, enEvidence) {
    var videAvant = liste.querySelector(":scope > .discret");
    if (videAvant) videAvant.remove();
    var ligne = document.createElement("div");
    ligne.className = "ligne-mouvement";
    var titre = document.createElement("strong");
    titre.textContent = mouvement.type;
    var detail = document.createElement("span");
    detail.className = "discret";
    detail.textContent = mouvement.date + " · " + mouvement.utilisateur + (mouvement.commentaire ? " · " + mouvement.commentaire : "");
    ligne.appendChild(titre);
    ligne.appendChild(document.createTextNode(" " + formaterNombre(mouvement.quantite) + " → stock " + formaterNombre(mouvement.stockApres)));
    ligne.appendChild(document.createElement("br"));
    ligne.appendChild(detail);
    liste.insertBefore(ligne, liste.firstChild);
    if (enEvidence) mettreEnEvidence(ligne);
  }

  // Enregistre le mouvement dans la mémoire de la démo et met à jour la page ; renvoie le nouveau stock.
  function enregistrerMouvement(article, type, quantite, commentaire) {
    var nouveauStock = type === "Sortie" ? stockActuel(article) - quantite
      : type === "Entrée" ? stockActuel(article) + quantite
      : quantite;
    var nomUtilisateur = document.querySelector(".nom-utilisateur");
    var mouvement = {
      type: type,
      quantite: quantite,
      stockApres: nouveauStock,
      date: new Date().toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }),
      utilisateur: nomUtilisateur ? nomUtilisateur.textContent.trim() : "—",
      commentaire: commentaire || "",
    };
    etatDemo.stocks[article] = nouveauStock;
    (etatDemo.mouvements[article] = etatDemo.mouvements[article] || []).push(mouvement);
    if (type === "Comptage d'inventaire") etatDemo.comptages[article] = new Date().toLocaleDateString("fr-FR");
    enregistrerEtat(etatDemo);

    zonesStockDeLArticle(article).forEach(function (zoneStock) {
      afficherStock(zoneStock, nouveauStock);
      mettreEnEvidence(zoneStock);
    });
    document.querySelectorAll('[data-liste-mouvements="' + article + '"]').forEach(function (liste) {
      afficherMouvement(liste, mouvement, true);
    });
    return nouveauStock;
  }

  // --- Au chargement : réaffiche ce qui a été saisi sur les autres pages ----------
  Object.keys(etatDemo.stocks).forEach(function (article) {
    zonesStockDeLArticle(article).forEach(function (zoneStock) {
      afficherStock(zoneStock, etatDemo.stocks[article]);
    });
  });
  Object.keys(etatDemo.comptages).forEach(function (article) {
    document.querySelectorAll('[data-dernier-comptage="' + article + '"]').forEach(function (cellule) {
      cellule.textContent = etatDemo.comptages[article];
    });
  });
  document.querySelectorAll("[data-liste-mouvements]").forEach(function (liste) {
    (etatDemo.mouvements[liste.dataset.listeMouvements] || []).forEach(function (mouvement) {
      afficherMouvement(liste, mouvement, false);
    });
  });
  var messageEnAttente = lireMessageEnAttente();
  if (messageEnAttente) afficherMessage(messageEnAttente);

  document.querySelectorAll('[data-action="reinitialiser-demo"]').forEach(function (bouton) {
    bouton.addEventListener("click", function () {
      etatDemo = { stocks: {}, comptages: {}, mouvements: {} };
      enregistrerEtat(etatDemo);
      messageApresRedirection("Démo remise à zéro : stocks et mouvements de départ.", window.location.href);
    });
  });

  // Le paramétrage des articles, produits et comptes passe par l'administration, absente de la démo statique.
  document.querySelectorAll("[data-demo-parametrage]").forEach(function (lien) {
    lien.addEventListener("click", function (evenement) {
      evenement.preventDefault();
      afficherMessage("Démo : le paramétrage (articles, produits, comptes) se fait dans l'interface " +
        "d'administration, disponible sur la version installée.");
    });
  });

  // --- Saisies simulées ------------------------------------------------------------
  function simulerMouvementDeStock(formulaire) {
    var quantite = lireNombre(formulaire.querySelector("[name=quantite]").value);
    if (!(quantite > 0)) {
      afficherMessage("Saisissez une quantité positive.", true);
      return;
    }
    var typeMouvement = formulaire.querySelector("[name=type]:checked").value === "sortie" ? "Sortie" : "Entrée";
    var nouveauStock = enregistrerMouvement(formulaire.dataset.article, typeMouvement, quantite,
      formulaire.querySelector("[name=commentaire]").value.trim());
    formulaire.reset();
    afficherMessage(typeMouvement + " de " + formaterNombre(quantite) + " enregistrée : nouveau stock " +
      formaterNombre(nouveauStock) + "." + MENTION_DEMO);
  }

  function simulerSortieDePiece(formulaire) {
    var champQuantite = formulaire.querySelector("[name=quantite]");
    var quantite = lireNombre(champQuantite.value);
    if (!(quantite > 0)) {
      afficherMessage("Saisissez une quantité positive.", true);
      return;
    }
    var piece = formulaire.querySelector("[name=piece]").dataset;
    var nouveauStock = enregistrerMouvement(piece.article, "Sortie", quantite, "Remplacement sur " + piece.outil);
    champQuantite.value = champQuantite.defaultValue;
    afficherMessage("Sortie de " + formaterNombre(quantite) + " " + piece.reference + " enregistrée : nouveau stock " +
      formaterNombre(nouveauStock) + "." + MENTION_DEMO);
  }

  function simulerComptage(formulaire) {
    var champsRemplis = Array.prototype.filter.call(formulaire.querySelectorAll("input.compte"), function (champ) {
      return champ.value.trim() !== "";
    });
    if (!champsRemplis.length) {
      afficherMessage("Rien à enregistrer.", true);
      return;
    }
    var illisibles = champsRemplis.filter(function (champ) {
      return !(lireNombre(champ.value) >= 0);
    });
    if (illisibles.length) {
      afficherMessage("Quantité illisible : « " + illisibles[0].value + " ».", true);
      return;
    }
    champsRemplis.forEach(function (champ) {
      enregistrerMouvement(champ.dataset.article, "Comptage d'inventaire", lireNombre(champ.value));
      document.querySelectorAll('[data-dernier-comptage="' + champ.dataset.article + '"]').forEach(function (cellule) {
        cellule.textContent = etatDemo.comptages[champ.dataset.article];
      });
      champ.value = "";
    });
    afficherMessage(champsRemplis.length + " comptage(s) enregistré(s), stocks corrigés." + MENTION_DEMO);
  }

  function adresseDeRetour(formulaire) {
    return formulaire.querySelector("[data-lien-retour]").getAttribute("href");
  }

  function simulerEnregistrementOutil(formulaire) {
    var champsObligatoires = ["code", "nom"].map(function (nom) {
      return formulaire.querySelector("[name=" + nom + "]");
    });
    var champVide = champsObligatoires.filter(function (champ) {
      return !champ.value.trim();
    })[0];
    if (champVide) {
      afficherMessage("Le code et le nom de l'outil sont obligatoires.", true);
      champVide.focus();
      return;
    }
    var articlesChoisis = [];
    var doublon = null;
    formulaire.querySelectorAll("table.pieces-outil tr").forEach(function (ligne) {
      var listeArticles = ligne.querySelector("select");
      var caseRetirer = ligne.querySelector("input[type=checkbox]");
      if (!listeArticles || !listeArticles.value || (caseRetirer && caseRetirer.checked)) return;
      if (articlesChoisis.indexOf(listeArticles.value) !== -1) doublon = listeArticles.selectedOptions[0].textContent;
      articlesChoisis.push(listeArticles.value);
    });
    if (doublon) {
      afficherMessage("La pièce « " + doublon + " » est listée deux fois.", true);
      return;
    }
    messageApresRedirection("Outil " + champsObligatoires[0].value.trim() + " vérifié avec " + articlesChoisis.length +
      " pièce(s) d'usure. Démo : la modification des outils n'est pas conservée, seuls les mouvements de stock le sont.",
      adresseDeRetour(formulaire));
  }

  var simulations = {
    "mouvement": simulerMouvementDeStock,
    "sortie-piece": simulerSortieDePiece,
    "comptage": simulerComptage,
    "outil": simulerEnregistrementOutil,
    "suppression-outil": function (formulaire) {
      messageApresRedirection("Démo : l'outil serait supprimé, avec ses sous-ensembles ; les articles restent dans le stock.",
        adresseDeRetour(formulaire));
    },
  };

  document.querySelectorAll("form[data-demo], form[data-demo-message]").forEach(function (formulaire) {
    formulaire.addEventListener("submit", function (evenement) {
      evenement.preventDefault();
      if (formulaire.dataset.demoMessage) {
        // Commandes : le changement d'état est seulement annoncé.
        afficherMessage(formulaire.dataset.demoMessage + " (Démo : rien n'est enregistré.)");
      } else {
        simulations[formulaire.dataset.demo](formulaire);
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
