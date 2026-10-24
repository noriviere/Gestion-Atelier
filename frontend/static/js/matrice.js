// Matrice produits × machines : fenêtre d'une case, changement d'état sans recharger la page, copie de fiche.
// Dans la démo statique, les changements sont appliqués à l'écran seulement.
(function () {
  var tableau = document.querySelector("table.matrice");
  var dialogue = document.getElementById("dialogue-case");
  if (!tableau || !dialogue) return;

  var estLaDemo = document.body.hasAttribute("data-demo");
  var MENTION_DEMO = " (Démo : rien n'est enregistré.)";
  var LIBELLES = {
    programme: "Programmé",
    a_faire: "À faire",
    a_securiser: "À sécuriser",
    non_faisable: "Non faisable",
    vide: ""
  };
  var ETATS_AVEC_FICHE = ["programme", "a_faire"];

  var formulaireEtat = dialogue.querySelector("form.choix-etat");
  var formulaireCopie = dialogue.querySelector("form.copier-fiche");
  var zoneSources = formulaireCopie.querySelector(".sources-copie");
  var lienOuvrir = dialogue.querySelector('[data-role="ouvrir"]');
  var lienModifier = dialogue.querySelector('[data-role="modifier"]');
  var lienCreer = dialogue.querySelector('[data-role="creer"]');
  var caseOuverte = null;

  function annoncer(texte, estUneErreur) {
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
  }

  // « À faire » devient « à sécuriser » quand le produit est déjà programmé sur une autre machine ;
  // « possible » s'affiche comme une case vide. Même règle que backend/produits/matrice.py.
  function etatAffiche(etatEnregistre, nombreProgrammees) {
    if (etatEnregistre === "a_faire" && nombreProgrammees > 0) return "a_securiser";
    if (!etatEnregistre || etatEnregistre === "possible") return "vide";
    return etatEnregistre;
  }

  function casesDeLaLigne(ligne) {
    return Array.prototype.slice.call(ligne.querySelectorAll("td.case-matrice"));
  }

  function recalculerLigne(ligne) {
    var cases = casesDeLaLigne(ligne);
    var nombreProgrammees = cases.filter(function (cellule) {
      return cellule.dataset.etat === "programme";
    }).length;
    var aDesCasesAFaire = false;
    cases.forEach(function (cellule) {
      var affiche = etatAffiche(cellule.dataset.etat, nombreProgrammees);
      if (affiche === "a_faire" || affiche === "a_securiser") aDesCasesAFaire = true;
      cellule.className = "case-matrice etat-" + affiche;
      cellule.querySelector(".bouton-case").textContent = LIBELLES[affiche];
    });
    ligne.querySelector(".compte-programmees").textContent = nombreProgrammees;
    var vues = [];
    if (nombreProgrammees === 1) vues.push("non_securise");
    if (nombreProgrammees === 0) vues.push("sans_machine");
    if (aDesCasesAFaire) vues.push("a_faire");
    ligne.dataset.vue = vues.join(" ");
  }

  function afficherLien(lien, adresse) {
    lien.hidden = !adresse;
    lien.href = adresse || "#";
  }

  function ouvrirCase(cellule) {
    caseOuverte = cellule;
    var ligne = cellule.closest("tr");
    dialogue.querySelector("h2").textContent = ligne.dataset.reference + " sur " + cellule.dataset.codeMachine;
    formulaireEtat.querySelector("[name=produit]").value = ligne.dataset.produit;
    formulaireEtat.querySelector("[name=machine]").value = cellule.dataset.machine;
    var etatEnregistre = cellule.dataset.etat === "possible" ? "" : cellule.dataset.etat;
    formulaireEtat.querySelectorAll("[name=etat]").forEach(function (option) {
      option.checked = option.value === etatEnregistre;
    });

    afficherLien(lienOuvrir, cellule.dataset.urlFiche);
    afficherLien(lienModifier, cellule.dataset.urlModifier);
    afficherLien(lienCreer, cellule.dataset.urlFiche ? "" : ligne.dataset.urlNouvelle + "?machine=" + cellule.dataset.machine);

    // Copie possible depuis chaque fiche du produit sur une autre machine.
    zoneSources.innerHTML = "";
    casesDeLaLigne(ligne).forEach(function (source) {
      if (source === cellule || !source.dataset.urlDupliquer) return;
      var bouton = document.createElement("button");
      bouton.type = "submit";
      bouton.className = "bouton secondaire";
      bouton.formAction = source.dataset.urlDupliquer;
      bouton.dataset.codeMachine = source.dataset.codeMachine;
      bouton.textContent = "Copier la fiche " + source.dataset.codeMachine;
      zoneSources.appendChild(bouton);
    });
    formulaireCopie.hidden = !zoneSources.children.length;
    formulaireCopie.querySelector("[name=machine]").value = cellule.dataset.machine;

    dialogue.showModal();
  }

  function appliquerReponse(cellule, reponse) {
    cellule.dataset.etat = reponse.etat;
    ["fiche", "modifier", "dupliquer"].forEach(function (cle) {
      var attribut = "url" + cle.charAt(0).toUpperCase() + cle.slice(1);
      if (reponse[cle]) cellule.dataset[attribut] = reponse[cle];
      else delete cellule.dataset[attribut];
    });
    recalculerLigne(cellule.closest("tr"));
    cellule.classList.add("mis-a-jour");
  }

  function reponseSimulee(cellule, etat) {
    var avecFiche = ETATS_AVEC_FICHE.indexOf(etat) !== -1;
    return {
      etat: etat,
      fiche: avecFiche ? cellule.dataset.urlFiche : "",
      modifier: avecFiche ? cellule.dataset.urlModifier : "",
      dupliquer: avecFiche ? cellule.dataset.urlDupliquer : ""
    };
  }

  function enregistrerEtat() {
    var cellule = caseOuverte;
    var etat = formulaireEtat.querySelector("[name=etat]:checked").value;
    dialogue.close();
    if (estLaDemo) {
      appliquerReponse(cellule, reponseSimulee(cellule, etat));
      annoncer("État de la case changé." + MENTION_DEMO);
      return;
    }
    fetch(tableau.dataset.urlEtat, {
      method: "POST",
      body: new FormData(formulaireEtat),
      headers: { Accept: "application/json" },
      credentials: "same-origin"
    })
      .then(function (reponse) {
        // Une page d'erreur ou de connexion (session expirée) n'est pas du JSON : on garde un message clair.
        return reponse.json().catch(function () { return {}; }).then(function (donnees) {
          if (!reponse.ok || typeof donnees.etat !== "string") throw new Error(donnees.erreur || "Enregistrement refusé, rechargez la page.");
          return donnees;
        });
      })
      .then(function (donnees) {
        appliquerReponse(cellule, donnees);
      })
      .catch(function (erreur) {
        annoncer(erreur.message || "Enregistrement impossible, rechargez la page.", true);
      });
  }

  tableau.addEventListener("click", function (evenement) {
    var bouton = evenement.target.closest(".bouton-case");
    if (bouton) ouvrirCase(bouton.closest("td"));
  });

  // Au clavier, les flèches parcourent les états sans enregistrer ; Entrée valide l'état choisi.
  var choixAuClavier = false;
  formulaireEtat.addEventListener("keydown", function (evenement) {
    if (evenement.key.indexOf("Arrow") === 0) choixAuClavier = true;
    if (evenement.key === "Enter" && formulaireEtat.querySelector("[name=etat]:checked")) {
      evenement.preventDefault();
      enregistrerEtat();
    }
  });
  formulaireEtat.addEventListener("change", function () {
    if (choixAuClavier) {
      choixAuClavier = false;
      return;
    }
    enregistrerEtat();
  });
  formulaireEtat.addEventListener("submit", function (evenement) {
    evenement.preventDefault();
  });

  // Hors démo, la copie s'envoie normalement et ouvre la nouvelle fiche à ajuster.
  formulaireCopie.addEventListener("submit", function (evenement) {
    if (!estLaDemo) return;
    evenement.preventDefault();
    var cellule = caseOuverte;
    var source = evenement.submitter ? evenement.submitter.dataset.codeMachine : "";
    var etat = cellule.dataset.etat === "programme" ? "programme" : "a_faire";
    dialogue.close();
    appliquerReponse(cellule, reponseSimulee(cellule, etat));
    annoncer("Fiche copiée de " + source + " vers " + cellule.dataset.codeMachine +
      " : sur la version installée, elle s'ouvre pour ajuster la cadence et les paramètres." + MENTION_DEMO);
  });

  // Un clic sur le fond grisé ferme la fenêtre.
  dialogue.addEventListener("click", function (evenement) {
    if (evenement.target === dialogue) dialogue.close();
  });
})();
