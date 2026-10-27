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
  // Les messages de la démo font remonter en haut de la page, où ils s'affichent.
  function afficherMessage(texte, estUneErreur) {
    window.Atelier.afficherMessage(texte, estUneErreur, true);
  }

  var lireNombre = window.Atelier.lireNombre;

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

  // Le paramétrage des comptes et des listes de référence passe par l'administration, absente de la démo statique.
  document.querySelectorAll("[data-demo-parametrage]").forEach(function (lien) {
    lien.addEventListener("click", function (evenement) {
      evenement.preventDefault();
      afficherMessage("Démo : le paramétrage (comptes, types d'inventaire, listes de référence) se fait dans l'interface " +
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
    var typeChoisi = formulaire.querySelector("[name=type]:checked");
    var typeMouvement = typeChoisi && typeChoisi.value === "entree" ? "Entrée" : "Sortie";
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
    var ecarts = [];
    champsRemplis.forEach(function (champ) {
      var quantiteComptee = lireNombre(champ.value);
      var ecart = Math.round((quantiteComptee - stockActuel(champ.dataset.article)) * 100) / 100;
      if (ecart) {
        var reference = champ.closest("tr").querySelector("a").textContent.trim();
        ecarts.push(reference + " " + (ecart > 0 ? "+" : "−") + formaterNombre(Math.abs(ecart)));
      }
      enregistrerMouvement(champ.dataset.article, "Comptage d'inventaire", quantiteComptee);
      document.querySelectorAll('[data-dernier-comptage="' + champ.dataset.article + '"]').forEach(function (cellule) {
        cellule.textContent = etatDemo.comptages[champ.dataset.article];
      });
      champ.dataset.stockTheorique = quantiteComptee;
      champ.value = "";
      champ.dispatchEvent(new Event("input"));
    });
    var bilanEcarts = ecarts.length ? " " + ecarts.length + " écart(s) : " + ecarts.join(", ") + "." : " Aucun écart.";
    afficherMessage(champsRemplis.length + " comptage(s) enregistré(s), stocks corrigés." + bilanEcarts + MENTION_DEMO);
  }

  // Dépôt d'une photo ou d'un document sur une fiche : le fichier choisi s'affiche, sans être envoyé.
  function simulerDepotDocument(formulaire) {
    var champFichier = formulaire.querySelector("input[type=file]");
    var fichier = champFichier.files[0];
    if (!fichier) {
      afficherMessage("Choisissez d'abord un fichier.", true);
      return;
    }
    var titre = formulaire.querySelector("[name=titre]").value.trim() || fichier.name;
    var adresse = URL.createObjectURL(fichier);
    if (/^image\//.test(fichier.type)) {
      var section = document.querySelector(".section-photos");
      var figure = document.createElement("figure");
      var image = document.createElement("img");
      var legende = document.createElement("figcaption");
      image.src = adresse;
      image.alt = titre;
      legende.textContent = titre;
      figure.appendChild(image);
      figure.appendChild(legende);
      section.querySelector("[data-galerie]").appendChild(figure);
      section.hidden = false;
      mettreEnEvidence(figure);
    } else {
      var liste = document.querySelector("[data-liste-documents]");
      var aucun = liste.querySelector(".aucun-document");
      if (aucun) aucun.remove();
      var element = document.createElement("li");
      var lien = document.createElement("a");
      lien.href = adresse;
      lien.target = "_blank";
      lien.rel = "noopener";
      lien.textContent = titre;
      element.appendChild(lien);
      liste.appendChild(element);
      mettreEnEvidence(element);
    }
    formulaire.reset();
    formulaire.querySelector(".zone-depot").classList.remove("fichier-choisi");
    champFichier.dispatchEvent(new Event("change"));
    afficherMessage("« " + titre + " » ajouté à la fiche." + MENTION_DEMO);
  }

  // Lien « Créer la fiche » de la matrice : la machine choisie arrive dans l'adresse.
  var machineDemandee = new URLSearchParams(window.location.search).get("machine");
  var listeMachines = document.querySelector("form select[name=machine]");
  if (machineDemandee && listeMachines && !listeMachines.disabled) listeMachines.value = machineDemandee;

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

  // Rapport de production : les saisies du shift sont vérifiées par le navigateur, sans être enregistrées.
  function simulerSaisieProduction(formulaire) {
    if (!formulaire.reportValidity()) return;
    afficherMessage(formulaire.dataset.demoTexte + " (Démo : rien n'est enregistré.)");
  }

  // Montage et démontage d'une meule : les champs obligatoires sont vérifiés par le navigateur ;
  // les contrôles et calculs du serveur ne tournent que sur la version installée.
  function simulerSaisieMeule(formulaire) {
    if (!formulaire.reportValidity()) return;
    messageApresRedirection(formulaire.dataset.demoTexte + " (Démo : rien n'est enregistré.)", adresseDeRetour(formulaire));
  }

  var simulations = {
    "mouvement": simulerMouvementDeStock,
    "saisie-meule": simulerSaisieMeule,
    "production": simulerSaisieProduction,
    "sortie-piece": simulerSortieDePiece,
    "comptage": simulerComptage,
    "outil": simulerEnregistrementOutil,
    "suppression-outil": function (formulaire) {
      messageApresRedirection("Démo : l'outil serait supprimé, avec ses sous-ensembles ; les articles restent dans le stock.",
        adresseDeRetour(formulaire));
    },
  };

  // demo.js est chargé après atelier.js : une confirmation refusée (data-confirmation) arrête l'envoi
  // avant ce gestionnaire, grâce à stopImmediatePropagation.
  document.querySelectorAll("form[method=post]").forEach(function (formulaire) {
    formulaire.addEventListener("submit", function (evenement) {
      evenement.preventDefault();
      if (formulaire.classList.contains("depot-document")) {
        simulerDepotDocument(formulaire);
      } else if (formulaire.hasAttribute("data-simulation-locale")) {
        // Formulaire simulé par le script de sa page (matrice.js).
      } else if (formulaire.dataset.demoMessage) {
        // Commandes : le changement d'état est seulement annoncé.
        afficherMessage(formulaire.dataset.demoMessage + " (Démo : rien n'est enregistré.)");
      } else if (simulations[formulaire.dataset.demo]) {
        simulations[formulaire.dataset.demo](formulaire);
      } else {
        afficherMessage("Démo : cette saisie n'est possible que sur la version installée.");
      }
    });
  });

  // Filtres et recherches : appliqués directement sur les lignes du tableau.
  document.querySelectorAll("form.filtres:not([method=post])").forEach(function (formulaire) {
    // data-tableau : quand la page a plusieurs tableaux, celui que les filtres concernent.
    var tableau = document.querySelector(formulaire.dataset.tableau || "main table");
    if (!tableau) return;
    var champRecherche = formulaire.querySelector("[type=search]");
    var listesDeroulantes = formulaire.querySelectorAll("select");
    var casesACocher = formulaire.querySelectorAll("[type=checkbox]");

    // Ligne « Aucun… » du gabarit (une seule cellule sur toute la largeur) : ce n'est pas une donnée à filtrer.
    function estUneLigneVide(ligne) {
      return ligne.cells.length === 1 && ligne.cells[0].colSpan > 1;
    }
    var lignesDeDonnees = Array.prototype.slice.call(tableau.rows, 1).filter(function (ligne) {
      return !estUneLigneVide(ligne);
    });
    var ligneAucunResultat = null;
    if (lignesDeDonnees.length) {
      ligneAucunResultat = tableau.insertRow(-1);
      var cellule = ligneAucunResultat.insertCell(0);
      cellule.colSpan = tableau.rows[0].cells.length;
      cellule.className = "discret";
      cellule.textContent = "Aucune ligne ne correspond aux filtres.";
      ligneAucunResultat.hidden = true;
    }

    function filtrerLignes(evenement) {
      if (evenement) evenement.preventDefault();
      var texteRecherche = champRecherche ? champRecherche.value.trim().toLowerCase() : "";
      lignesDeDonnees.forEach(function (ligne) {
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
      if (ligneAucunResultat) {
        ligneAucunResultat.hidden = lignesDeDonnees.some(function (ligne) { return !ligne.hidden; });
      }
    }

    // La page exportée contient toutes les lignes : le filtre par défaut est appliqué à l'ouverture.
    if (formulaire.hasAttribute("data-filtrer-au-chargement")) filtrerLignes();
    formulaire.addEventListener("submit", filtrerLignes);
    formulaire.addEventListener("change", filtrerLignes);
    formulaire.addEventListener("input", filtrerLignes);
  });
})();
