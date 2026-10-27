// Saisie des meules : valeurs déduites du format et contrôles en direct sous chaque champ, comme dans
// l'application suivi-usure-meules. Le serveur refait tous les contrôles à l'enregistrement : ce script
// prévient plus tôt, il ne remplace pas les vérifications du serveur.
(function () {
  var lireNombre = window.Atelier.lireNombre;
  var LIBELLES_MA5 = { oui: "Oui", non: "Non" };
  var LONGUEUR_MATRICULE = 4;
  var MINIMUM_FIABLE = 5;

  var sourceControles = document.getElementById("controles-meules");
  var CONTROLES = sourceControles ? JSON.parse(sourceControles.textContent) : null;
  var regleActive = function (code) { return !CONTROLES || CONTROLES.actives[code] !== false; };

  var formater = function (nombre, decimales) {
    return nombre.toLocaleString("fr-FR", { maximumFractionDigits: decimales === undefined ? 2 : decimales });
  };
  var euros = function (nombre) { return formater(nombre, 0) + " €"; };
  var aujourdhui = function () {
    var date = new Date();
    return date.getFullYear() + "-" + String(date.getMonth() + 1).padStart(2, "0") + "-" + String(date.getDate()).padStart(2, "0");
  };
  // Nombre saisi dans un champ, ou null s'il est vide ou illisible.
  var nombreDe = function (champ) {
    if (!champ || champ.value.trim() === "") return null;
    var nombre = lireNombre(champ.value);
    return isNaN(nombre) ? null : nombre;
  };

  // --- Message sous un champ : erreur (bloquera l'enregistrement), alerte, ok ou simple information ---
  function afficherMessage(champ, texte, niveau) {
    if (!champ) return;
    var bloc = champ.closest(".champ");
    if (!bloc) return;
    var zone = bloc.querySelector(".message-champ");
    if (!zone) {
      zone = document.createElement("span");
      zone.className = "message-champ";
      zone.setAttribute("aria-live", "polite");
      bloc.appendChild(zone);
    }
    zone.textContent = texte || "";
    zone.hidden = !texte;
    zone.className = "message-champ" + (niveau ? " " + niveau : "");
    bloc.classList.toggle("signal-erreur", !!texte && niveau === "erreur");
    bloc.classList.toggle("signal-alerte", !!texte && niveau === "alerte");
  }

  // Limite bloquante puis valeur inhabituelle (zone de Tukey calculée par le serveur sur l'historique).
  function controlerNombre(champ, nom) {
    var valeur = nombreDe(champ);
    if (valeur === null) return null;
    var limite = CONTROLES.limites[nom];
    if (limite && valeur > limite.maximum) {
      return ["Dépasse le maximum de " + formater(limite.maximum) + " " + limite.unite + " : la saisie sera refusée.", "erreur"];
    }
    var zone = CONTROLES.zones[nom];
    if (zone && (valeur < zone.bas || valeur > zone.haut)) {
      return ["⚠ Valeur inhabituelle : la plupart des saisies sont entre " + formater(zone.q1) + " et " + formater(zone.q3) +
              ". Vérifiez.", "alerte"];
    }
    return null;
  }

  // « 534 » -> « 0534 », comme le serveur.
  function normaliserMatricule(champ) {
    var texte = champ.value.trim();
    if (/^\d+$/.test(texte) && texte.length < LONGUEUR_MATRICULE) champ.value = texte.padStart(LONGUEUR_MATRICULE, "0");
  }
  function controlerMatricule(champ) {
    var texte = champ.value.trim();
    if (!texte) return afficherMessage(champ, "");
    var complet = /^\d+$/.test(texte) && texte.length <= LONGUEUR_MATRICULE;
    if (!complet) return afficherMessage(champ, "Un matricule a " + LONGUEUR_MATRICULE + " chiffres.", "erreur");
    var numero = texte.padStart(LONGUEUR_MATRICULE, "0");
    if (regleActive("nouveau_matricule") && CONTROLES.matricules.indexOf(numero) === -1) {
      return afficherMessage(champ, "⚠ Matricule " + numero + " jamais utilisé : il sera ajouté à la liste. " +
                                    "Vérifiez qu'il n'y a pas de faute de frappe.", "alerte");
    }
    afficherMessage(champ, "");
  }

  // « Il reste à renseigner » près du bouton, comme dans l'ancienne application.
  function libelleDuChamp(champ) {
    var bloc = champ.closest(".champ");
    var libelle = bloc && bloc.querySelector("label, .libelle-champ");
    return libelle ? libelle.textContent.replace(/\s*\*\s*$/, "").trim() : champ.name;
  }
  function afficherManquants(formulaire) {
    var zone = formulaire.querySelector("[data-manque]");
    if (!zone) return;
    var manquants = [], vus = {};
    formulaire.querySelectorAll("input[required], select[required], textarea[required]").forEach(function (champ) {
      if (vus[champ.name] || champ.closest("[hidden]")) return;
      vus[champ.name] = true;
      var vide = champ.type === "radio"
        ? !formulaire.querySelector("[name='" + champ.name + "']:checked")
        : champ.value.trim() === "";
      if (vide) manquants.push(libelleDuChamp(champ));
    });
    zone.textContent = manquants.length
      ? "Il reste à renseigner : " + manquants.slice(0, 3).join(", ") + (manquants.length > 3 ? " … (+" + (manquants.length - 3) + ")" : "")
      : "Tout est prêt : vérifiez, puis enregistrez.";
    zone.classList.toggle("pret", !manquants.length);
  }

  // Liste déroulante en deux groupes : ce qui est prévu pour le format, puis le reste (avec avertissement).
  function regrouper(liste, prevues, titrePrevues, titreAutres) {
    if (!liste.optionsDOrigine) {
      liste.optionsDOrigine = Array.prototype.filter.call(liste.options, function (option) { return option.value !== ""; });
      liste.optionVide = Array.prototype.filter.call(liste.options, function (option) { return option.value === ""; })[0];
    }
    var valeur = liste.value;
    liste.replaceChildren();
    if (liste.optionVide) liste.append(liste.optionVide);
    if (!prevues.length) {
      liste.optionsDOrigine.forEach(function (option) { liste.append(option); });
    } else {
      var groupePrevu = document.createElement("optgroup"), groupeAutre = document.createElement("optgroup");
      groupePrevu.label = titrePrevues;
      groupeAutre.label = titreAutres;
      liste.optionsDOrigine.forEach(function (option) {
        (prevues.indexOf(option.value) !== -1 ? groupePrevu : groupeAutre).append(option);
      });
      liste.append(groupePrevu);
      if (groupeAutre.children.length) liste.append(groupeAutre);
    }
    liste.value = valeur;
  }
  var texteOption = function (liste, valeur) {
    var option = Array.prototype.filter.call(liste.options, function (candidate) { return candidate.value === valeur; })[0];
    // « S7 – Machine S7 » -> « S7 » : le code suffit dans les messages.
    return option ? option.textContent.trim().split(" – ")[0] : valeur;
  };

  // --- Montage -------------------------------------------------------------------------------------
  var tableFormats = document.getElementById("table-formats");
  var formulaireMontage = tableFormats && document.querySelector(".formulaire-meule");
  if (formulaireMontage) {
    var formats = JSON.parse(tableFormats.textContent);
    var champ = function (nom) { return formulaireMontage.querySelector("[name=" + nom + "]"); };
    var listeProduits = champ("produit"), listeMeules = champ("meule"), listeMachines = champ("machine");
    var zoneCodeLame = formulaireMontage.querySelector("[data-code-lame]");
    var zoneMa5Automatique = formulaireMontage.querySelector("[data-ma5-auto]");
    var champMa5 = formulaireMontage.querySelector(".champ-ma5");
    var zoneMediane = formulaireMontage.querySelector("[data-mediane-attendue]");
    var choix = function (nom) { var coche = formulaireMontage.querySelector("[name=" + nom + "]:checked"); return coche ? coche.value : ""; };

    var formatChoisi = function () {
      var matieres = formats[listeProduits.value];
      return matieres && choix("matiere") ? matieres[choix("matiere")] || null : null;
    };

    var afficherValeursDeduites = function (proposerMeule) {
      var format = formatChoisi();
      zoneCodeLame.textContent = format ? format.code_lame || "—" : "—";
      var ma5AChoisir = !format || format.ma5 === "peut_etre";
      champMa5.hidden = !ma5AChoisir;
      zoneMa5Automatique.textContent = ma5AChoisir ? (format ? "À choisir : ce format peut être MA5 ou non." : "")
        : "MA5 : " + LIBELLES_MA5[format.ma5] + " (déterminé automatiquement d'après le format et la matière).";
      regrouper(listeMeules, format ? format.meules : [], "Prévues pour ce format", "Autres meules (avertissement)");
      regrouper(listeMachines, format ? format.machines : [], "Prévues pour ce format", "Autres machines (avertissement)");
      // Au changement de format, la meule prévue est proposée si la meule choisie n'en fait pas partie.
      if (proposerMeule && format && format.meules.length && format.meules.indexOf(listeMeules.value) === -1) {
        listeMeules.value = format.meules[0];
      }
    };

    // Médiane de faces pour 89 mm des meules identiques : critère élargi s'il y a moins de 5 cas.
    var medianeDe = function (valeurs) {
      var triees = valeurs.slice().sort(function (a, b) { return a - b; }), milieu = Math.floor(triees.length / 2);
      return triees.length % 2 ? triees[milieu] : (triees[milieu - 1] + triees[milieu]) / 2;
    };
    var medianeAttendue = function (meule, machine, matiere, face) {
      var niveaux = [
        ["meule + machine + matière", function (ligne) { return ligne[1] === machine && ligne[2] === matiere; }],
        ["meule + matière", function (ligne) { return ligne[2] === matiere; }],
        ["meule seule", function () { return true; }],
      ];
      var repli = null;
      for (var position = 0; position < niveaux.length; position++) {
        var valeurs = CONTROLES.durees.filter(function (ligne) {
          return ligne[0] === meule && ligne[3] === face && niveaux[position][1](ligne);
        }).map(function (ligne) { return ligne[4]; });
        if (!valeurs.length) continue;
        var resultat = { mediane: medianeDe(valeurs), nombre: valeurs.length, critere: niveaux[position][0],
                         fiable: valeurs.length >= MINIMUM_FIABLE };
        if (resultat.fiable) return resultat;
        repli = repli || resultat;
      }
      return repli;
    };
    var afficherMediane = function () {
      var meule = Number(listeMeules.value), machine = Number(listeMachines.value), matiere = choix("matiere");
      zoneMediane.hidden = !(meule && machine && matiere);
      if (zoneMediane.hidden) return;
      var tuiles = ["A", "B"].map(function (face) {
        var resultat = medianeAttendue(meule, machine, matiere, face);
        var tuile = document.createElement("div");
        tuile.className = "tuile" + (choix("face") === face ? " choisie" : "");
        var libelle = document.createElement("div"), valeur = document.createElement("div"), detail = document.createElement("div");
        libelle.className = detail.className = "libelle";
        valeur.className = "valeur";
        libelle.textContent = "Face " + face;
        valeur.textContent = resultat ? formater(Math.round(resultat.mediane), 0) : "—";
        detail.textContent = resultat ? resultat.nombre + " cas · " + resultat.critere + (resultat.fiable ? "" : " · peu fiable")
                                      : "pas de données";
        tuile.append(libelle, valeur, detail);
        return tuile;
      });
      zoneMediane.querySelector("[data-faces]").replaceChildren.apply(zoneMediane.querySelector("[data-faces]"), tuiles);
    };

    var controlerMontage = function () {
      var format = formatChoisi();
      controlerMatricule(champ("matricule_monteur"));

      var date = champ("date_montage");
      afficherMessage(date, regleActive("date_futur") && date.value > aujourdhui()
        ? "⚠ Date dans le futur : vérifiez." : "", "alerte");

      var machineNonPrevue = false;
      if (format && format.machines.length && listeMachines.value && regleActive("machine_non_prevue")) {
        machineNonPrevue = format.machines.indexOf(listeMachines.value) === -1;
        var prevues = format.machines.map(function (valeur) { return texteOption(listeMachines, valeur); }).join(", ");
        afficherMessage(listeMachines, machineNonPrevue
          ? "⚠ Machine non prévue pour ce format (prévues : " + prevues + "). Une explication sera demandée dans le commentaire."
          : "✔ Machine prévue pour ce format", machineNonPrevue ? "alerte" : "ok");
      } else {
        afficherMessage(listeMachines, "");
      }
      var commentaire = champ("commentaire_montage");
      afficherMessage(commentaire, machineNonPrevue && !commentaire.value.trim()
        ? "Obligatoire : expliquez pourquoi " + texteOption(listeMachines, listeMachines.value) + " est utilisée pour ce format."
        : "", "erreur");

      if (format && format.meules.length && listeMeules.value && regleActive("meule_non_prevue")) {
        var meulePrevue = format.meules.indexOf(listeMeules.value) !== -1;
        var references = format.meules.map(function (valeur) { return texteOption(listeMeules, valeur); }).join(", ");
        afficherMessage(listeMeules, meulePrevue ? "✔ Meule prévue pour ce format"
          : "⚠ Meule différente de celle prévue pour ce format (" + references + ").", meulePrevue ? "ok" : "alerte");
      } else {
        afficherMessage(listeMeules, "");
      }

      var pression = champ("pression_arrosage");
      if (nombreDe(pression) === 0) {
        afficherMessage(pression, "0 : manomètre hors service, la pression n'est pas contrôlée.", "info");
      } else {
        var resultatPression = controlerNombre(pression, "pression_arrosage");
        afficherMessage(pression, resultatPression && resultatPression[0], resultatPression && resultatPression[1]);
      }
      ["vitesse_rotation", "vitesse_avance", "hauteur_initiale"].forEach(function (nom) {
        var resultat = controlerNombre(champ(nom), nom);
        afficherMessage(champ(nom), resultat && resultat[0], resultat && resultat[1]);
      });
      var compteur = champ("compteur_debut");
      afficherMessage(compteur, nombreDe(compteur) ? "Normalement 0 : vérifiez que le compteur n'a pas été remis à zéro." : "",
                      "info");
      afficherMediane();
      afficherManquants(formulaireMontage);
    };

    formulaireMontage.addEventListener("change", function (evenement) {
      if (evenement.target === listeProduits || evenement.target.name === "matiere") afficherValeursDeduites(true);
      if (evenement.target.name === "matricule_monteur") normaliserMatricule(evenement.target);
      controlerMontage();
    });
    formulaireMontage.addEventListener("input", controlerMontage);
    afficherValeursDeduites(false);
    controlerMontage();
  }

  // --- Démontage ----------------------------------------------------------------------------------
  var formulaireDemontage = document.querySelector(".formulaire-meule[data-seuil-non-finie]");
  if (formulaireDemontage) {
    var champDemontage = function (nom) { return formulaireDemontage.querySelector("[name=" + nom + "]"); };
    var saisie = CONTROLES.saisie;
    var seuil = CONTROLES.seuil_non_finie;
    var questionNonFinie = formulaireDemontage.querySelector("[data-alerte-non-finie]");
    var noteDefaut = formulaireDemontage.querySelector("[data-note-defaut]");
    var zoneThemes = formulaireDemontage.querySelector("[data-themes]");
    var champCommentaire = champDemontage("commentaire");
    var reponseRienASignaler = formulaireDemontage.querySelector("[name=probleme][value=non]");
    var reponseRemarque = formulaireDemontage.querySelector("[name=probleme][value=oui]");

    var controlerDemontage = function () {
      controlerMatricule(champDemontage("matricule_demonteur"));

      var compteur = champDemontage("compteur_fin"), compteurFin = nombreDe(compteur);
      if (compteurFin === null) {
        afficherMessage(compteur, "");
      } else if (compteurFin < saisie.compteur_debut) {
        afficherMessage(compteur, "Doit être supérieur ou égal au compteur au montage (" + saisie.compteur_debut + ").", "erreur");
      } else if (compteurFin === saisie.compteur_debut) {
        afficherMessage(compteur, "⚠ Aucune face : le compteur n'a pas bougé depuis le montage.", "alerte");
      } else {
        var resultat = controlerNombre(compteur, "compteur_fin");
        afficherMessage(compteur, resultat ? resultat[0] : "= " + formater(compteurFin - saisie.compteur_debut, 0) + " faces",
                        resultat ? resultat[1] : "info");
      }

      var hauteur = champDemontage("hauteur_finale"), hauteurFinale = nombreDe(hauteur);
      var nonFinie = hauteurFinale !== null && hauteurFinale > seuil;
      if (hauteurFinale === null) {
        afficherMessage(hauteur, "");
      } else if (hauteurFinale > saisie.hauteur_initiale) {
        afficherMessage(hauteur, "Ne peut pas dépasser la hauteur initiale (" + formater(saisie.hauteur_initiale) + " mm).", "erreur");
        nonFinie = false;
      } else if (hauteurFinale > 0) {
        var perte = hauteurFinale / saisie.hauteur_initiale * CONTROLES.prix_meule;
        var texte = "💶 " + formater(hauteurFinale) + " mm non utilisés ≈ " + euros(perte) + " perdus (meule moyenne à " +
                    euros(CONTROLES.prix_meule) + ") · cumul " + CONTROLES.annee + " : " + euros(CONTROLES.perte_annee + perte);
        if (nonFinie) texte += " · ⚠ meule marquée « démontée avant usure totale » (X)";
        afficherMessage(hauteur, texte, "alerte");
      } else {
        afficherMessage(hauteur, "✔ Meule finie.", "ok");
      }

      // Meule non finie : une explication est exigée, « Oui, rien à signaler » n'est plus possible.
      var explicationExigee = nonFinie && regleActive("non_finie");
      questionNonFinie.hidden = !explicationExigee;
      questionNonFinie.textContent = explicationExigee
        ? "❓ Il reste " + formater(hauteurFinale) + " mm de meule : elle est démontée avant usure totale. Pourquoi ?" : "";
      if (explicationExigee) reponseRemarque.checked = true;
      reponseRienASignaler.disabled = explicationExigee;
      zoneThemes.hidden = !reponseRemarque.checked;
      afficherMessage(champCommentaire, explicationExigee && !champCommentaire.value.trim()
        ? "Obligatoire : expliquez pourquoi la meule n'est pas finie." : "", "erreur");

      var defautCoche = formulaireDemontage.querySelector("[name=themes][value='" + CONTROLES.theme_defaut.replace(/'/g, "\\'") + "']:checked");
      noteDefaut.hidden = !(nonFinie && reponseRemarque.checked && defautCoche);
      afficherManquants(formulaireDemontage);
    };

    formulaireDemontage.addEventListener("change", function (evenement) {
      if (evenement.target.name === "matricule_demonteur") normaliserMatricule(evenement.target);
      controlerDemontage();
    });
    formulaireDemontage.addEventListener("input", controlerDemontage);
    controlerDemontage();

    formulaireDemontage.querySelectorAll("[data-amorce]").forEach(function (bouton) {
      bouton.addEventListener("click", function () {
        var texte = champCommentaire.value.replace(/\s+$/, "");
        champCommentaire.value = (texte ? texte + "\n" : "") + bouton.dataset.amorce;
        champCommentaire.focus();
        controlerDemontage();
      });
    });
  }
})();
