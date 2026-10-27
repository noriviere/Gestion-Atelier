// Saisie des meules : valeurs déduites du format et aides du formulaire, comme dans l'application suivi-usure-meules.
// Le serveur refait tous les contrôles : ce script ne fait qu'aider la personne qui saisit.
(function () {
  var lireNombre = window.Atelier.lireNombre;
  var LIBELLES_MA5 = { oui: "Oui", non: "Non" };

  // --- Montage : code lame, MA5 et meule prévue d'après le format et la matière ---------------
  var tableFormats = document.getElementById("table-formats");
  var formulaireMontage = tableFormats && document.querySelector(".formulaire-meule");
  if (formulaireMontage) {
    var formats = JSON.parse(tableFormats.textContent);
    var listeProduits = formulaireMontage.querySelector("[name=produit]");
    var listeMeules = formulaireMontage.querySelector("[name=meule]");
    var zoneCodeLame = formulaireMontage.querySelector("[data-code-lame]");
    var zoneMa5Automatique = formulaireMontage.querySelector("[data-ma5-auto]");
    var champMa5 = formulaireMontage.querySelector(".champ-ma5");

    var formatChoisi = function () {
      var matiereChoisie = formulaireMontage.querySelector("[name=matiere]:checked");
      var matieres = formats[listeProduits.value];
      return matieres && matiereChoisie ? matieres[matiereChoisie.value] || null : null;
    };

    var afficherValeursDeduites = function (proposerMeule) {
      var format = formatChoisi();
      zoneCodeLame.textContent = format ? format.code_lame || "—" : "—";
      var ma5AChoisir = !format || format.ma5 === "peut_etre";
      champMa5.hidden = !ma5AChoisir;
      zoneMa5Automatique.textContent = ma5AChoisir ? "" : "MA5 : " + LIBELLES_MA5[format.ma5] + " (automatique).";
      // Au changement de format, la meule prévue est proposée si la meule choisie n'en fait pas partie.
      if (proposerMeule && format && format.meules.length && format.meules.indexOf(listeMeules.value) === -1) {
        listeMeules.value = format.meules[0];
      }
    };
    formulaireMontage.addEventListener("change", function (evenement) {
      if (evenement.target === listeProduits || evenement.target.name === "matiere") afficherValeursDeduites(true);
    });
    afficherValeursDeduites(false);
  }

  // --- Démontage : meule non finie, thèmes du problème et aide à la rédaction --------------------
  var formulaireDemontage = document.querySelector(".formulaire-meule[data-seuil-non-finie]");
  if (formulaireDemontage) {
    var seuil = lireNombre(formulaireDemontage.dataset.seuilNonFinie);
    var champHauteurFinale = formulaireDemontage.querySelector("[name=hauteur_finale]");
    var alerteNonFinie = formulaireDemontage.querySelector("[data-alerte-non-finie]");
    var zoneThemes = formulaireDemontage.querySelector("[data-themes]");
    var champCommentaire = formulaireDemontage.querySelector("[name=commentaire]");

    var signalerMeuleNonFinie = function () {
      alerteNonFinie.hidden = !(lireNombre(champHauteurFinale.value) > seuil);
    };
    var afficherThemes = function () {
      var reponse = formulaireDemontage.querySelector("[name=probleme]:checked");
      zoneThemes.hidden = !(reponse && reponse.value === "oui");
    };
    champHauteurFinale.addEventListener("input", signalerMeuleNonFinie);
    formulaireDemontage.addEventListener("change", afficherThemes);
    signalerMeuleNonFinie();
    afficherThemes();

    formulaireDemontage.querySelectorAll("[data-amorce]").forEach(function (bouton) {
      bouton.addEventListener("click", function () {
        var texte = champCommentaire.value.replace(/\s+$/, "");
        champCommentaire.value = (texte ? texte + "\n" : "") + bouton.dataset.amorce;
        champCommentaire.focus();
      });
    });
  }
})();
