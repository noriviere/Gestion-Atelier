// Statistiques des meules : reprise de la page Statistiques de l'application suivi-usure-meules.
// Les lignes (une par meule démontée) sont dans la page ; filtres, détail et courbe sont calculés ici.
(function () {
  "use strict";
  var racine = document.querySelector("[data-statistiques-meules]");
  var source = document.getElementById("lignes-statistiques");
  if (!racine || !source) return;
  var LIGNES = JSON.parse(source.textContent);
  var COEFFICIENT_ELOIGNE = Number(racine.dataset.coefficientEloigne) || 3;
  var MINIMUM_ECARTER = 8;   // on n'écarte rien dans un groupe de moins de 8 valeurs
  var MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  var SVGNS = "http://www.w3.org/2000/svg";

  function element(balise, attributs) {
    var noeud = document.createElement(balise);
    Object.keys(attributs || {}).forEach(function (cle) {
      var valeur = attributs[cle];
      if (valeur === null || valeur === undefined || valeur === false) return;
      if (cle === "text") noeud.textContent = valeur;
      else if (cle === "class") noeud.className = valeur;
      else noeud.setAttribute(cle, valeur === true ? "" : valeur);
    });
    for (var position = 2; position < arguments.length; position++) {
      if (arguments[position] !== null && arguments[position] !== undefined) noeud.append(arguments[position]);
    }
    return noeud;
  }
  function elementSvg(balise, attributs, texte) {
    var noeud = document.createElementNS(SVGNS, balise);
    Object.keys(attributs || {}).forEach(function (cle) { noeud.setAttribute(cle, attributs[cle]); });
    if (texte !== undefined) noeud.textContent = texte;
    return noeud;
  }
  var estNombre = function (valeur) { return typeof valeur === "number" && isFinite(valeur); };
  var formater = function (nombre, decimales) {
    if (nombre === null || nombre === undefined || !isFinite(nombre)) return "—";
    return nombre.toLocaleString("fr-FR", { maximumFractionDigits: decimales === undefined ? 2 : decimales });
  };

  // --- Statistiques ------------------------------------------------------------------------------
  // Quantile « inclusive », comme QUARTILE.INC d'Excel.
  function quantile(triees, proportion) {
    if (!triees.length) return null;
    var position = (triees.length - 1) * proportion, bas = Math.floor(position), fraction = position - bas;
    return bas + 1 < triees.length ? triees[bas] + fraction * (triees[bas + 1] - triees[bas]) : triees[bas];
  }
  function resumer(valeurs) {
    var triees = valeurs.filter(estNombre).sort(function (a, b) { return a - b; });
    var effectif = triees.length;
    if (!effectif) return { effectif: 0 };
    var moyenne = triees.reduce(function (somme, valeur) { return somme + valeur; }, 0) / effectif;
    var ecartType = effectif > 1 ? Math.sqrt(triees.reduce(function (somme, valeur) {
      return somme + Math.pow(valeur - moyenne, 2);
    }, 0) / (effectif - 1)) : null;
    return { effectif: effectif, moyenne: moyenne, ecartType: ecartType, mediane: quantile(triees, 0.5),
             q1: quantile(triees, 0.25), q3: quantile(triees, 0.75), min: triees[0], max: triees[effectif - 1] };
  }
  function fiabilite(effectif) {
    if (effectif < 5) return ["trop peu de données", "alerte"];
    if (effectif < 20) return ["indicatif", "attention"];
    return ["fiable", "ok"];
  }
  // Valeurs très éloignées : hors de la zone de Tukey avec le coefficient du contrôle qualité.
  function sansValeursEloignees(valeurs) {
    if (valeurs.length < MINIMUM_ECARTER) return valeurs;
    var triees = valeurs.slice().sort(function (a, b) { return a - b; });
    var q1 = quantile(triees, 0.25), q3 = quantile(triees, 0.75), ecart = q3 - q1;
    return valeurs.filter(function (valeur) {
      return valeur >= q1 - COEFFICIENT_ELOIGNE * ecart && valeur <= q3 + COEFFICIENT_ELOIGNE * ecart;
    });
  }

  // --- Critères et grandeurs -----------------------------------------------------------------------
  var annee = function (ligne) { return Number(ligne.date.slice(0, 4)); };
  var mois = function (ligne) { return Number(ligne.date.slice(5, 7)); };
  var DIMENSIONS = [
    { id: "format", libelle: "Format", lire: function (ligne) { return ligne.format; } },
    { id: "matiere", libelle: "Matière", lire: function (ligne) { return ligne.matiere; } },
    { id: "machine", libelle: "Machine", lire: function (ligne) { return ligne.machine; } },
    { id: "article", libelle: "N° article meule", lire: function (ligne) { return ligne.article; } },
    { id: "face", libelle: "Face", lire: function (ligne) { return ligne.face; } },
    { id: "fournisseur", libelle: "Fournisseur", lire: function (ligne) { return ligne.fournisseur; } },
    { id: "annee", libelle: "Année", lire: annee },
    { id: "mois", libelle: "Mois", lire: mois, afficher: function (numero) { return MOIS[numero - 1]; } },
  ];
  var GRANDEURS = [
    ["faces_89", "Nb de faces par meule de 89 mm"],
    ["usure_par_face", "Hauteur usée par face (mm)"],
    ["faces_mm", "Nb de faces par mm"],
    ["compteur_fin", "Compteur fin"],
    ["usure", "Hauteur usée totale (mm)"],
  ];
  var etat = { filtres: {}, detail: "", grandeur: GRANDEURS[0][0], seuilFiabilite: 5, inclureNonFinies: true,
               ecarter: false, pas: "mois" };

  function comparer(a, b) {
    return estNombre(a) && estNombre(b) ? a - b : String(a).localeCompare(String(b), "fr", { numeric: true });
  }
  function valeursPossibles(dimension) {
    var vues = {};
    LIGNES.forEach(function (ligne) {
      var valeur = dimension.lire(ligne);
      if (valeur !== null && valeur !== undefined && valeur !== "") vues[valeur] = valeur;
    });
    return Object.keys(vues).map(function (cle) { return vues[cle]; }).sort(comparer);
  }
  function libelleDe(dimension, valeur) { return dimension.afficher ? dimension.afficher(valeur) : String(valeur); }

  // --- Barre des critères -------------------------------------------------------------------------
  var listes = {};
  var barreCriteres = element("div", { class: "barre-statistiques" });
  DIMENSIONS.forEach(function (dimension) {
    var liste = element("select", { name: "critere-" + dimension.id }, element("option", { value: "", text: "Tous" }));
    valeursPossibles(dimension).forEach(function (valeur) {
      liste.append(element("option", { value: String(valeur), text: libelleDe(dimension, valeur) }));
    });
    liste.addEventListener("change", function () { etat.filtres[dimension.id] = liste.value; mettreAJour(); });
    listes[dimension.id] = liste;
    barreCriteres.append(element("label", {}, dimension.libelle, liste));
  });

  var listeGrandeur = element("select", { name: "grandeur" });
  GRANDEURS.forEach(function (grandeur) { listeGrandeur.append(element("option", { value: grandeur[0], text: grandeur[1] })); });
  listeGrandeur.addEventListener("change", function () { etat.grandeur = listeGrandeur.value; mettreAJour(); });
  var listeDetail = element("select", { name: "detail" }, element("option", { value: "", text: "Aucun (ensemble)" }));
  DIMENSIONS.forEach(function (dimension) { listeDetail.append(element("option", { value: dimension.id, text: dimension.libelle })); });
  listeDetail.addEventListener("change", function () { etat.detail = listeDetail.value; mettreAJour(); });
  var listePas = element("select", { name: "pas" }, element("option", { value: "mois", text: "Mois" }),
    element("option", { value: "trimestre", text: "Trimestre" }), element("option", { value: "annee", text: "Année" }));
  listePas.addEventListener("change", function () { etat.pas = listePas.value; mettreAJour(); });
  var champSeuil = element("input", { type: "number", name: "seuil", min: "1", max: "100", value: "5", class: "champ-court" });
  champSeuil.addEventListener("input", function () { etat.seuilFiabilite = Math.max(1, Number(champSeuil.value) || 1); mettreAJour(); });
  var caseNonFinies = element("input", { type: "checkbox", name: "non-finies", checked: true });
  caseNonFinies.addEventListener("change", function () { etat.inclureNonFinies = caseNonFinies.checked; mettreAJour(); });
  var caseEcarter = element("input", { type: "checkbox", name: "ecarter" });
  caseEcarter.addEventListener("change", function () { etat.ecarter = caseEcarter.checked; mettreAJour(); });
  var boutonRaz = element("button", { type: "button", class: "bouton secondaire", text: "Tout réinitialiser" });
  boutonRaz.addEventListener("click", function () {
    Object.keys(listes).forEach(function (id) { listes[id].value = ""; });
    etat.filtres = {};
    listeDetail.value = "";
    etat.detail = "";
    mettreAJour();
  });
  var barreOptions = element("div", { class: "barre-statistiques" },
    element("label", {}, "Grandeur étudiée", listeGrandeur),
    element("label", {}, "Détailler par", listeDetail),
    element("label", {}, "Évolution par", listePas),
    element("label", {}, "Seuil de fiabilité (n min.)", champSeuil),
    element("label", { class: "case" }, caseNonFinies, "Inclure les meules démontées avant usure (X)"),
    element("label", { class: "case" }, caseEcarter, "Écarter les valeurs très éloignées"));

  var zoneResume = element("div"), zoneDetail = element("div"), zoneEvolution = element("div");
  racine.replaceChildren(
    element("p", { class: "discret", text: "Choisissez un ou plusieurs critères : seules les lignes qui respectent TOUS " +
      "les critères sont prises en compte. Ex. Format N8 seul = tout le format N8 ; Format N8 + Machine S2 + Année 2026 = " +
      "uniquement ces lignes." }),
    barreCriteres, barreOptions, element("div", { class: "actions" }, boutonRaz), zoneResume,
    element("h2", { text: "Détail par référence" }), zoneDetail,
    element("h2", { text: "Évolution de la médiane dans le temps" }), zoneEvolution);

  // --- Calculs ------------------------------------------------------------------------------------
  function lignesRetenues() {
    var actifs = DIMENSIONS.filter(function (dimension) { return etat.filtres[dimension.id]; });
    return LIGNES.filter(function (ligne) {
      return actifs.every(function (dimension) { return String(dimension.lire(ligne)) === etat.filtres[dimension.id]; })
        && (etat.inclureNonFinies || !ligne.x);
    });
  }
  function valeursDe(lignes) {
    return lignes.map(function (ligne) { return ligne[etat.grandeur]; }).filter(estNombre);
  }
  function tuile(titre, valeur, precision) {
    return element("div", { class: "tuile" }, element("div", { class: "libelle", text: titre }),
      element("div", { class: "valeur", text: valeur }), precision ? element("div", { class: "libelle", text: precision }) : null);
  }
  function pastilleFiabilite(effectif) {
    var niveau = fiabilite(effectif);
    return element("span", { class: "etiquette " + niveau[1], text: niveau[0] });
  }

  function mettreAJour() {
    var lignes = lignesRetenues();
    var avecValeur = valeursDe(lignes);
    var valeurs = etat.ecarter ? sansValeursEloignees(avecValeur) : avecValeur;
    var resume = resumer(valeurs);
    zoneResume.replaceChildren(
      element("div", { class: "grille grille-compacte grille-statistiques" },
        tuile("Lignes retenues", formater(lignes.length, 0), formater(avecValeur.length, 0) + " avec une valeur"),
        tuile("Valeurs utilisées (n)", formater(resume.effectif, 0),
          etat.ecarter && avecValeur.length !== resume.effectif ? (avecValeur.length - resume.effectif) + " écartée(s)" : null),
        tuile("Médiane", formater(resume.mediane)), tuile("Moyenne", formater(resume.moyenne)),
        tuile("Écart type", formater(resume.ecartType)),
        tuile("Min – Max", resume.effectif ? formater(resume.min) + " – " + formater(resume.max) : "—"),
        tuile("Q1 – Q3", resume.effectif ? formater(resume.q1) + " – " + formater(resume.q3) : "—", "50 % des valeurs")),
      element("p", { class: "discret" }, "Fiabilité : ", pastilleFiabilite(resume.effectif),
        " (moins de 5 valeurs = trop peu ; 5 à 19 = indicatif ; 20 et plus = fiable)"));
    dessinerDetail(lignes);
    dessinerEvolution(lignes);
  }

  function dessinerDetail(lignes) {
    if (!etat.detail) {
      zoneDetail.replaceChildren(element("p", { class: "vide", text: "Choisissez « Détailler par » (format, article, machine…) pour comparer les références." }));
      return;
    }
    var dimension = DIMENSIONS.filter(function (candidate) { return candidate.id === etat.detail; })[0];
    var groupes = new Map();
    lignes.forEach(function (ligne) {
      var cle = dimension.lire(ligne);
      if (cle === null || cle === undefined || cle === "") return;
      if (!groupes.has(cle)) groupes.set(cle, []);
      groupes.get(cle).push(ligne);
    });
    var references = [];
    groupes.forEach(function (lignesDuGroupe, cle) {
      var valeurs = valeursDe(lignesDuGroupe);
      var resume = resumer(etat.ecarter ? sansValeursEloignees(valeurs) : valeurs);
      if (resume.effectif) references.push({ cle: cle, resume: resume });
    });
    references.sort(function (a, b) { return b.resume.effectif - a.resume.effectif; });
    var entete = element("tr");
    [dimension.libelle, "n", "Médiane", "Moyenne", "Écart type", "Min", "Max", "Fiabilité"].forEach(function (titre, position) {
      entete.append(element("th", { class: position && position < 7 ? "nombre" : null, text: titre }));
    });
    var tableau = element("table", {}, entete);
    references.forEach(function (reference) {
      var resume = reference.resume;
      var ligne = element("tr", { class: "cliquable", tabindex: "0", title: "Cliquer pour filtrer sur cette référence" },
        element("td", { text: libelleDe(dimension, reference.cle) }));
      [formater(resume.effectif, 0), formater(resume.mediane), formater(resume.moyenne), formater(resume.ecartType),
       formater(resume.min), formater(resume.max)].forEach(function (texte) {
        ligne.append(element("td", { class: "nombre", text: texte }));
      });
      ligne.append(element("td", {}, pastilleFiabilite(resume.effectif)));
      var filtrer = function () {
        listes[dimension.id].value = String(reference.cle);
        etat.filtres[dimension.id] = String(reference.cle);
        listeDetail.value = "";
        etat.detail = "";
        mettreAJour();
      };
      ligne.addEventListener("click", filtrer);
      ligne.addEventListener("keydown", function (evenement) { if (evenement.key === "Enter") filtrer(); });
      tableau.append(ligne);
    });
    zoneDetail.replaceChildren(element("div", { class: "tableau" }, tableau),
      element("p", { class: "discret", text: references.length + " référence(s). Cliquez sur une ligne pour filtrer dessus." }));
  }

  // --- Courbe de la médiane par période ---------------------------------------------------------
  function periodeDe(ligne) {
    var numero = mois(ligne) - 1;
    if (etat.pas === "annee") return annee(ligne) * 12;
    if (etat.pas === "trimestre") return annee(ligne) * 12 + Math.floor(numero / 3) * 3;
    return annee(ligne) * 12 + numero;
  }
  function libellePeriode(rang) {
    var anneeDuRang = Math.floor(rang / 12), moisDuRang = rang % 12;
    if (etat.pas === "annee") return String(anneeDuRang);
    if (etat.pas === "trimestre") return "T" + (moisDuRang / 3 + 1) + " " + anneeDuRang;
    return MOIS[moisDuRang] + " " + anneeDuRang;
  }

  function dessinerEvolution(lignes) {
    var groupes = new Map();
    lignes.forEach(function (ligne) {
      var valeur = ligne[etat.grandeur];
      if (!estNombre(valeur)) return;
      var periode = periodeDe(ligne);
      if (!groupes.has(periode)) groupes.set(periode, []);
      groupes.get(periode).push(valeur);
    });
    var points = [];
    groupes.forEach(function (valeurs, periode) {
      var resume = resumer(etat.ecarter ? sansValeursEloignees(valeurs) : valeurs);
      if (resume.effectif) { resume.periode = periode; points.push(resume); }
    });
    points.sort(function (a, b) { return a.periode - b.periode; });
    if (!points.length) {
      zoneEvolution.replaceChildren(element("p", { class: "vide", text: "Aucune donnée datée pour ces critères." }));
      return;
    }

    var LARGEUR = 1000, HAUTEUR = 340, gauche = 58, droite = 16, haut = 14, bas = 64, hauteurBarres = 46;
    var premiere = points[0].periode, derniere = points[points.length - 1].periode, etendue = Math.max(1, derniere - premiere);
    var x = function (periode) {
      return gauche + (points.length === 1 ? (LARGEUR - gauche - droite) / 2 : (periode - premiere) / etendue * (LARGEUR - gauche - droite));
    };
    var maximum = Math.max.apply(null, points.map(function (point) { return Math.max(point.q3, point.mediane); }));
    var minimum = Math.min.apply(null, points.map(function (point) { return Math.min(point.q1, point.mediane); }));
    var y0 = Math.min(0, minimum), y1 = maximum * 1.08 || 1;
    var hauteurCourbe = HAUTEUR - haut - bas - hauteurBarres;
    var y = function (valeur) { return haut + (1 - (valeur - y0) / (y1 - y0)) * hauteurCourbe; };
    var effectifMaximum = Math.max.apply(null, points.map(function (point) { return point.effectif; }));
    var seuil = etat.seuilFiabilite;
    var svg = elementSvg("svg", { class: "graphique-mediane", viewBox: "0 0 " + LARGEUR + " " + HAUTEUR, role: "img",
                                  "aria-label": "Évolution de la médiane" });

    for (var graduation = 0; graduation <= 4; graduation++) {
      var valeurAxe = y0 + (y1 - y0) * graduation / 4, positionY = y(valeurAxe);
      svg.append(elementSvg("line", { class: "grille-axe", x1: gauche, x2: LARGEUR - droite, y1: positionY, y2: positionY }),
        elementSvg("text", { x: gauche - 8, y: positionY + 4, "text-anchor": "end" }, formater(valeurAxe, 1)));
    }
    var fiables = points.filter(function (point) { return point.effectif >= seuil; });
    if (fiables.length > 1) {   // bande Q1–Q3 sur les périodes fiables
      var dessus = fiables.map(function (point) { return x(point.periode) + "," + y(point.q3); });
      var dessous = fiables.slice().reverse().map(function (point) { return x(point.periode) + "," + y(point.q1); });
      svg.append(elementSvg("polygon", { class: "bande", points: dessus.concat(dessous).join(" ") }));
    }
    for (var rang = 1; rang < points.length; rang++) {   // ligne pleine entre périodes fiables, pointillée sinon
      var precedent = points[rang - 1], courant = points[rang];
      var solide = precedent.effectif >= seuil && courant.effectif >= seuil;
      svg.append(elementSvg("line", { class: "ligne" + (solide ? "" : " pointillee"), x1: x(precedent.periode),
        y1: y(precedent.mediane), x2: x(courant.periode), y2: y(courant.mediane) }));
    }
    var baseBarres = HAUTEUR - bas, dernierLibelle = -1e9, dernierEffectif = -1e9;
    points.forEach(function (point) {
      var hauteurBarre = point.effectif / effectifMaximum * (hauteurBarres - 12), positionX = x(point.periode);
      svg.append(elementSvg("rect", { class: "barre-effectif", x: positionX - 6, y: baseBarres + hauteurBarres - 4 - hauteurBarre - 14,
                                      width: 12, height: hauteurBarre }));
      var cercle = elementSvg("circle", { class: "point" + (point.effectif >= seuil ? "" : " faible"), cx: positionX,
                                          cy: y(point.mediane), r: 5 });
      cercle.append(elementSvg("title", {}, libellePeriode(point.periode) + " : médiane " + formater(point.mediane) +
        " (n = " + point.effectif + (point.effectif >= seuil ? "" : ", peu fiable") + ") — Q1 " + formater(point.q1) +
        " / Q3 " + formater(point.q3)));
      svg.append(cercle);
      if (positionX - dernierLibelle >= 62) {
        dernierLibelle = positionX;
        svg.append(elementSvg("text", { x: positionX, y: HAUTEUR - 6, "text-anchor": "middle" }, libellePeriode(point.periode)));
      }
      if (positionX - dernierEffectif >= 44) {
        dernierEffectif = positionX;
        svg.append(elementSvg("text", { x: positionX, y: baseBarres + hauteurBarres - 18 - hauteurBarre, "text-anchor": "middle" },
          "n=" + point.effectif));
      }
    });
    zoneEvolution.replaceChildren(element("div", { class: "graphique-defilant" }, svg),
      element("div", { class: "legende-graphique" },
        element("span", { text: "● point plein : au moins " + seuil + " valeurs" }),
        element("span", { text: "○ point creux / ligne pointillée : trop peu de valeurs pour conclure" }),
        element("span", { text: "bande bleue : 50 % des valeurs (Q1–Q3)" }),
        element("span", { text: "barres grises : nombre de valeurs par période" })));
  }

  mettreAJour();
})();
