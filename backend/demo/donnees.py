"""Données fictives de la démo, sur la base décrite par Noel.

Machines S1 à S8, MAD1 et MAD2 ; produits N2 à N12 ; pour chaque produit un jeu d'outils
(chargeur, outillage face, pince, outillage dos) qui porte des pièces d'usure
(patin, porte-lame, tige, peigne) ; consommables : huile, bandes et meules.

Machines S1 à S8 : meules ; MAD1 et MAD2 : bandes.
Pièces d'usure : certaines sont partagées entre produits d'une même taille (P, M, G),
d'autres sont propres à un produit :
- patin et tige : partagés par taille ;
- porte-lame : partagé pour les tailles P et M, propre au produit pour N10 à N12 ;
- peigne : propre à chaque produit.
Modifier ce fichier puis relancer `python manage.py charger_demo` suffit pour changer la démo.
Les dates de dernier inventaire sont exprimées en « il y a N jours ».
"""

COMPTES = [
    # identifiant, prénom, nom, profil
    ("admin", "Admin", "", "Admin"),
    ("methode", "Noël", "Méthodes", "Méthode et management"),
    ("chef", "Chef", "d'équipe", "Méthode et management"),
    ("regleur", "Régleur", "Équipe A", "Régleur"),
    ("intendante", "Intendante", "", "Intendant"),
    ("operateur", "Opérateur", "(compte partagé)", "Opérateur"),
]

FOURNISSEURS = [
    # nom, contact, téléphone
    ("Mécanique Précision Sud", "Service commercial", "04 00 00 00 01"),
    ("Usinage Martin", "M. Martin", "04 00 00 00 02"),
    ("Abrasifs Industriels", "Comptoir", "04 00 00 00 03"),
    ("Meules et Bandes Diffusion", "Mme Petit", "04 00 00 00 04"),
    ("Lubrifiants de l'Ouest", "Service client", "04 00 00 00 05"),
]

TYPES_INVENTAIRE = [
    # nom, description
    ("Magasin pièces d'usure", "Patins, porte-lames, tiges et peignes"),
    ("Abrasifs", "Bandes et meules"),
    ("Huiles", "Bidons en zone de stockage"),
]

# Taille de pièce d'usure utilisée par chaque produit.
TAILLES = {"N2": "P", "N3": "P", "N4": "P", "N5": "P",
           "N6": "M", "N7": "M", "N8": "M", "N9": "M",
           "N10": "G", "N11": "G", "N12": "G"}
PRODUITS_LISTE = list(TAILLES)

ARTICLES = [
    # référence, désignation, catégorie (usure / conso), type d'inventaire, emplacement, unité,
    # stock, stock mini, mini de commande, fréquence d'inventaire (jours), dernier inventaire (il y a N jours)
    ("PAT-P", "Patin taille P", "usure", "Magasin pièces d'usure", "A1-01", "pièce", 14, 10, 20, 90, 30),
    ("PAT-M", "Patin taille M", "usure", "Magasin pièces d'usure", "A1-02", "pièce", 6, 10, 20, 90, 100),
    ("PAT-G", "Patin taille G", "usure", "Magasin pièces d'usure", "A1-03", "pièce", 12, 8, 16, 90, 30),
    ("PL-P", "Porte-lame taille P", "usure", "Magasin pièces d'usure", "A2-01", "pièce", 5, 4, 4, 180, 60),
    ("PL-M", "Porte-lame taille M", "usure", "Magasin pièces d'usure", "A2-02", "pièce", 3, 4, 4, 180, 200),
    ("TIG-P", "Tige taille P", "usure", "Magasin pièces d'usure", "A3-01", "pièce", 22, 12, 24, 90, 95),
    ("TIG-M", "Tige taille M", "usure", "Magasin pièces d'usure", "A3-02", "pièce", 18, 12, 24, 90, 20),
    ("TIG-G", "Tige taille G", "usure", "Magasin pièces d'usure", "A3-03", "pièce", 9, 10, 20, 90, 20),
    *[(f"PL-{produit}", f"Porte-lame spécifique {produit}", "usure", "Magasin pièces d'usure", f"A2-{produit}", "pièce", stock, 2, 2, 180, 60)
      for produit, stock in (("N10", 3), ("N11", 2), ("N12", 1))],
    *[(f"PEI-{produit}", f"Peigne spécifique {produit}", "usure", "Magasin pièces d'usure", f"A4-{produit}", "pièce", stock, 2, 4, 120, inventorie_il_y_a)
      for produit, stock, inventorie_il_y_a in (("N2", 5, 40), ("N3", 4, 40), ("N4", 6, 130), ("N5", 3, 40), ("N6", 2, 40), ("N7", 5, 130),
                               ("N8", 4, 40), ("N9", 6, 40), ("N10", 3, 40), ("N11", 1, 40), ("N12", 4, 130))],
    ("HUI-01", "Bidon d'huile de coupe 20 L", "conso", "Huiles", "C1", "bidon", 3, 4, 6, 30, 35),
    ("BAN-40", "Bande abrasive grain 40", "conso", "Abrasifs", "B1-01", "bande", 35, 20, 50, 30, 10),
    ("BAN-80", "Bande abrasive grain 80", "conso", "Abrasifs", "B1-02", "bande", 18, 20, 50, 30, 10),
    ("BAN-120", "Bande abrasive grain 120", "conso", "Abrasifs", "B1-03", "bande", 42, 20, 50, 30, 40),
    ("BAN-240", "Bande abrasive grain 240 finition", "conso", "Abrasifs", "B1-04", "bande", 25, 10, 25, 30, 10),
    ("MEU-200", "Meule Ø200 corindon", "conso", "Abrasifs", "B2-01", "meule", 6, 4, 6, 60, 20),
    ("MEU-300", "Meule Ø300 corindon", "conso", "Abrasifs", "B2-02", "meule", 2, 3, 4, 60, 70),
    ("MEU-CBN", "Meule CBN de finition", "conso", "Abrasifs", "B2-03", "meule", 3, 2, 2, 60, 20),
]

# Les pièces d'usure sont des designs internes, usinées par les fournisseurs sur plan :
# elles n'ont pas de référence fournisseur. Huile, bandes et meules sont des articles achetés.
PLANS = {
    reference: f"PL-{numero:04d} ind. A"
    for numero, (reference, *_reste) in enumerate((article for article in ARTICLES if article[2] == "usure"), start=1101)
}

PRIX = [
    # référence article, fournisseur, référence fournisseur (vide pour un design interne), prix (€), délai (jours), préféré
    *[(f"PAT-{taille}", "Mécanique Précision Sud", "", 18.0, 10, True) for taille in "PMG"],
    *[(f"PAT-{taille}", "Usinage Martin", "", 21.0, 6, False) for taille in "PMG"],
    *[(f"PL-{taille}", "Usinage Martin", "", 145.0, 15, True) for taille in "PM"],
    *[(f"PL-{produit}", "Usinage Martin", "", 180.0, 20, True) for produit in ("N10", "N11", "N12")],
    *[(f"TIG-{taille}", "Mécanique Précision Sud", "", 9.5, 10, True) for taille in "PMG"],
    *[(f"PEI-N{numero}", "Usinage Martin", "", 62.0, 15, True) for numero in range(2, 13)],
    *[(f"PEI-N{numero}", "Mécanique Précision Sud", "", 58.0, 25, False) for numero in range(2, 13)],
    ("HUI-01", "Lubrifiants de l'Ouest", "LO-HC20", 92.0, 4, True),
    *[(f"BAN-{grain}", "Abrasifs Industriels", f"AI-B{grain}", 6.8, 5, True) for grain in (40, 80, 120, 240)],
    *[(f"BAN-{grain}", "Meules et Bandes Diffusion", f"MBD-{grain}", 7.4, 3, False) for grain in (40, 80, 120, 240)],
    ("MEU-200", "Meules et Bandes Diffusion", "MBD-M200", 85.0, 10, True),
    ("MEU-300", "Meules et Bandes Diffusion", "MBD-M300", 140.0, 10, True),
    ("MEU-CBN", "Meules et Bandes Diffusion", "MBD-CBN", 690.0, 30, True),
]

MACHINES = [
    # code, nom, description
    *[(f"S{numero}", f"Machine S{numero}", "Machine à meule") for numero in range(1, 9)],
    ("MAD1", "Machine à bandes 1", "Machine à bandes"),
    ("MAD2", "Machine à bandes 2", "Machine à bandes"),
]

# Chaque produit a son jeu d'outils : un outil principal et quatre sous-ensembles.
SOUS_ENSEMBLES = [
    # numéro (ordre d'affichage), nom, pièces d'usure montées (préfixe de référence, quantité)
    ("1", "Chargeur", [("PAT", 2), ("TIG", 2)]),
    ("2", "Outillage face", [("PL", 1), ("PEI", 1)]),
    ("3", "Pince", [("PAT", 2)]),
    ("4", "Outillage dos", [("PL", 1), ("PEI", 1), ("TIG", 1)]),
]

def _piece(prefixe, produit):
    """Référence de la pièce d'usure montée sur le jeu d'outils d'un produit."""
    if prefixe == "PEI" or (prefixe == "PL" and TAILLES[produit] == "G"):
        return f"{prefixe}-{produit}"
    return f"{prefixe}-{TAILLES[produit]}"


OUTILS = [
    # code, nom, code de l'outil parent (vide si outil principal), description
]
PIECES_OUTILS = [
    # code outil, référence article, quantité montée
]
for _produit in PRODUITS_LISTE:
    OUTILS.append((f"OUT-{_produit}", f"Jeu d'outils {_produit}", "", f"Jeu complet pour le produit {_produit} (taille {TAILLES[_produit]})."))
    for _suffixe, _nom, _pieces_montees in SOUS_ENSEMBLES:
        OUTILS.append((f"OUT-{_produit}-{_suffixe}", f"{_nom} {_produit}", f"OUT-{_produit}", ""))
        for _prefixe, _quantite in _pieces_montees:
            PIECES_OUTILS.append((f"OUT-{_produit}-{_suffixe}", _piece(_prefixe, _produit), _quantite))

PRODUITS = [
    # référence, désignation, client, notes générales
    (produit, f"Produit {produit}", "", "Contrôle visuel en début de série et toutes les 2 heures.")
    for produit in PRODUITS_LISTE
] + [("N13", "Produit N13", "", "Nouveau produit en industrialisation : outillage à l'étude.")]

# Produit, machines, cadence (pièces/h)
_AFFECTATIONS = [
    ("N2", ["S1", "S2"], 480), ("N3", ["S1", "S2"], 460), ("N4", ["S3"], 450), ("N5", ["S3", "S4"], 420),
    ("N6", ["S4"], 380), ("N7", ["S5", "MAD1"], 360), ("N8", ["S5", "S6"], 340), ("N9", ["S6", "MAD1"], 320),
    ("N10", ["S7", "MAD2"], 280), ("N11", ["S7", "S8"], 260), ("N12", ["S8", "MAD2"], 240),
]
_BANDE_PAR_TAILLE = {"P": "BAN-120", "M": "BAN-80", "G": "BAN-40"}
_MEULE_PAR_TAILLE = {"P": "MEU-200", "M": "MEU-200", "G": "MEU-300"}

FABRICATIONS = [
    # référence produit, code machine, cadence (pièces/h), codes outils, notes de réglage
]
CONSOMMATIONS = [
    # référence produit, code machine, référence article, quantité / fréquence
]
PARAMETRES = [
    # référence produit, code machine, paramètre, valeur, unité (dans l'ordre d'affichage)
]
DOCUMENTS = [
    # référence produit, code machine (vide : document du produit), titre, nom du fichier, nature (plan / photo)
]
_DIAMETRE_MEULE = {"MEU-200": "200", "MEU-300": "300"}
_PARAMETRES_PAR_TAILLE = {
    # taille : (vitesse meule m/s, avance mm/min, prise de passe mm, vitesse bande m/s, pression bar, hauteur peigne mm)
    "P": ("35", "140", "0,03", "28", "2,5", "8"),
    "M": ("32", "120", "0,05", "25", "3", "12"),
    "G": ("30", "90", "0,08", "22", "3,5", "16"),
}
for _produit, _machines, _cadence in _AFFECTATIONS:
    _taille = TAILLES[_produit]
    _vitesse_meule, _avance, _passe, _vitesse_bande, _pression, _peigne = _PARAMETRES_PAR_TAILLE[_taille]
    DOCUMENTS.append((_produit, "", f"Plan {_produit} indice A", f"plan-{_produit}.pdf", "plan"))
    for _machine in _machines:
        DOCUMENTS.append((_produit, _machine, f"Réglage {_produit} sur {_machine}", f"reglage-{_produit}-{_machine}.svg", "photo"))
        if _machine.startswith("S"):
            PARAMETRES += [(_produit, _machine, "Vitesse meule", _vitesse_meule, "m/s"),
                           (_produit, _machine, "Avance", _avance, "mm/min"),
                           (_produit, _machine, "Prise de passe", _passe, "mm"),
                           (_produit, _machine, "Diamètre meule", _DIAMETRE_MEULE[_MEULE_PAR_TAILLE[_taille]], "mm")]
        else:
            PARAMETRES += [(_produit, _machine, "Vitesse bande", _vitesse_bande, "m/s"),
                           (_produit, _machine, "Pression de contact", _pression, "bar"),
                           (_produit, _machine, "Grain ébauche", _BANDE_PAR_TAILLE[_taille].split("-")[1], ""),
                           (_produit, _machine, "Hauteur du peigne", _peigne, "mm")]
        if _machine.startswith("S"):
            FABRICATIONS.append((_produit, _machine, _cadence, [f"OUT-{_produit}"],
                                 f"Meule {_MEULE_PAR_TAILLE[_taille]}, dresser la meule toutes les 2 h.\nVérifier le serrage de la pince à chaque prise de poste."))
            CONSOMMATIONS += [(_produit, _machine, _MEULE_PAR_TAILLE[_taille], "1 meule / semaine"), (_produit, _machine, "MEU-CBN", "finition, selon usure"),
                              (_produit, _machine, "HUI-01", "1 bidon / semaine")]
        else:
            FABRICATIONS.append((_produit, _machine, round(_cadence * 1.2), [f"OUT-{_produit}"],
                                 f"Bande {_BANDE_PAR_TAILLE[_taille]} en ébauche, BAN-240 en finition.\nRégler la hauteur du peigne avant démarrage.\nVérifier le serrage de la pince à chaque prise de poste."))
            CONSOMMATIONS += [(_produit, _machine, _BANDE_PAR_TAILLE[_taille], "1 bande / poste"), (_produit, _machine, "BAN-240", "1 bande / 2 postes"),
                              (_produit, _machine, "HUI-01", "1 bidon / 2 semaines")]

# Cases de la matrice produits × machines en plus des fabrications programmées ci-dessus.
# « À faire » s'affiche « à sécuriser » quand le produit tourne déjà sur une autre machine.
_PETITS = [produit for produit, taille in TAILLES.items() if taille == "P"]
_GRANDS = [produit for produit, taille in TAILLES.items() if taille == "G"] + ["N13"]
ETATS_MATRICE = [
    # référence produit, code machine, état (a_faire / non_faisable)
    ("N4", "S4", "a_faire"), ("N6", "S3", "a_faire"), ("N10", "S8", "a_faire"),
    ("N13", "S8", "a_faire"), ("N13", "MAD2", "a_faire"),
    # Les petites meules de S1 et S2 ne prennent pas la taille G ; MAD2 n'a pas de pince pour la taille P.
    *[(produit, machine, "non_faisable") for produit in _GRANDS for machine in ("S1", "S2")],
    *[(produit, "MAD2", "non_faisable") for produit in _PETITS],
]

MOUVEMENTS = [
    # référence article, type (entree / sortie), quantité, identifiant, commentaire
    ("PAT-M", "sortie", 4, "regleur", "Changement patins chargeur N7"),
    ("BAN-80", "sortie", 6, "operateur", "MAD1 poste du matin"),
    ("PEI-N11", "sortie", 1, "regleur", "Peigne cassé outillage face N11"),
    ("BAN-120", "entree", 50, "intendante", "Réception commande"),
    ("HUI-01", "sortie", 1, "operateur", "S2"),
    ("MEU-300", "sortie", 1, "regleur", "S7 changement de meule"),
]

COMPTAGES = [
    # référence article, stock théorique, quantité comptée, compté il y a N jours (les mêmes que le dernier inventaire)
    ("BAN-40", 37, 35, 10), ("BAN-80", 24, 24, 10), ("BAN-240", 25, 25, 10), ("TIG-M", 20, 18, 20),
    ("TIG-G", 9, 9, 20), ("MEU-200", 6, 6, 20), ("MEU-CBN", 3, 3, 20), ("PAT-P", 13, 14, 30), ("PAT-G", 12, 12, 30),
    ("HUI-01", 4, 3, 35), ("PEI-N2", 5, 5, 40), ("PEI-N3", 5, 4, 40), ("PEI-N5", 3, 3, 40), ("BAN-120", 45, 42, 40),
    ("PL-P", 5, 5, 60), ("PL-N10", 3, 3, 60), ("MEU-300", 3, 3, 70),
]

COMMANDES = [
    # fournisseur, état (attente / passee / recue / receptionnee / annulee), créée il y a N jours,
    # passée il y a N jours, livraison prévue dans N jours (négatif : date dépassée), reçue il y a N jours,
    # n° de confirmation du fournisseur, lignes [(référence article, quantité commandée, quantité reçue)], notes
    # Les dates vides valent None. Rangées de la plus ancienne à la plus récente : la numérotation suit cet ordre.
    ("Usinage Martin", "annulee", 70, None, None, None, "", [("PEI-N4", 4, None)], "Doublon avec une commande passée par téléphone."),
    ("Mécanique Précision Sud", "receptionnee", 45, 44, -34, 33, "AR-58122", [("TIG-P", 24, 20)], "Livraison partielle : 4 tiges en reliquat."),
    ("Usinage Martin", "passee", 26, 25, -10, None, "UM-2026-311", [("PL-M", 4, None), ("PL-N11", 2, None), ("PL-N12", 2, None)],
     "Relancé par téléphone, nouvelle date non confirmée."),
    ("Abrasifs Industriels", "receptionnee", 21, 20, -15, 15, "AI-77045", [("BAN-120", 50, 50)], ""),
    ("Mécanique Précision Sud", "recue", 13, 12, -2, 1, "AR-58301", [("PAT-M", 20, None)], "Colis au quai, à contrôler."),
    ("Lubrifiants de l'Ouest", "passee", 7, 6, -2, None, "", [("HUI-01", 6, None)], ""),
    ("Meules et Bandes Diffusion", "passee", 5, 4, 6, None, "MBD-4410", [("MEU-300", 4, None)], ""),
    ("Abrasifs Industriels", "attente", 0, None, None, None, "", [("BAN-80", 50, None)], "À regrouper avec le prochain besoin en bandes."),
]

# --- Remontées terrain : suivi d'usure des meules -------------------------------------------------
MATRICULES = [
    # numéro, nom (facultatif)
    ("0534", "Équipe A"), ("0612", "Équipe A"), ("0718", "Équipe B"), ("0841", "Équipe B"), ("0907", "Équipe C"),
    ("1023", "Équipe C"),
]

# Table « Formats et matière » : le format est le produit. Seules les machines à meule (S1 à S8) sont prévues.
_PRODUITS_PEUT_ETRE_MA5 = ("N4", "N8")
FORMATS_MEULE = [
    # produit, matière (I inox / C carbone), code lame, MA5 (oui / non / peut_etre), meules prévues, machines prévues
]
for _produit, _machines, _cadence in _AFFECTATIONS:
    _machines_a_meule = [machine for machine in _machines if machine.startswith("S")]
    for _matiere in ("I", "C"):
        if _matiere == "C":
            _ma5 = "non"
        elif _produit in _PRODUITS_PEUT_ETRE_MA5:
            _ma5 = "peut_etre"
        else:
            _ma5 = "oui" if TAILLES[_produit] == "G" else "non"
        FORMATS_MEULE.append((_produit, _matiere, f"L{_produit[1:]}{_matiere}", _ma5,
                              [_MEULE_PAR_TAILLE[TAILLES[_produit]]], _machines_a_meule))

# Historique fictif : nombre de meules démontées, sur environ 4 mois, et durée de vie typique de chaque meule.
NOMBRE_MEULES_DEMONTEES = 90
FACES_PAR_MM = {"MEU-200": 95, "MEU-300": 120}
# Meules montées et pas encore démontées : machine, produit, matière, face, montée il y a N jours.
MEULES_MONTEES = [("S3", "N4", "I", "A", 2), ("S5", "N7", "C", "B", 1), ("S7", "N10", "I", "A", 0)]


def saisies_meules_historique(alea):
    """Saisies démontées fictives, tirées avec le générateur `alea` (graine fixe : la démo est toujours la même).

    Renvoie des dicts : produit, matière, machine, face, il y a N jours, réglages, hauteurs, compteur fin, retour."""
    formats = [(produit, matiere, machines) for produit, matiere, _, _, _, machines in FORMATS_MEULE]
    saisies = []
    for numero in range(NOMBRE_MEULES_DEMONTEES):
        produit, matiere, machines = alea.choice(formats)
        taille = TAILLES[produit]
        vitesse_meule, avance = (int(valeur) for valeur in _PARAMETRES_PAR_TAILLE[taille][:2])
        hauteur_initiale = round(alea.uniform(98, 105), 1)
        tirage = alea.random()
        probleme, themes, commentaire = False, [], ""
        if tirage < 0.04:
            hauteur_finale = round(alea.uniform(25, 60), 1)
            probleme, themes = True, ["Meule cassée ou fissurée"]
            commentaire = "Constat : fissure sur le flanc après un choc au chargement.\nAction : meule démontée et mise de côté."
        elif tirage < 0.12:
            hauteur_finale = round(alea.uniform(4, 20), 1)
            commentaire = alea.choice(["Changement de série : format suivant sur une autre meule.",
                                       "Usure irrégulière, la qualité de coupe se dégradait."])
            if "irrégulière" in commentaire:
                probleme, themes = True, ["Usure irrégulière", "Mauvaise qualité de coupe"]
        else:
            hauteur_finale = round(alea.uniform(0, 1.5), 1)
        meule = _MEULE_PAR_TAILLE[taille]
        faces = round((hauteur_initiale - hauteur_finale) * FACES_PAR_MM[meule] * alea.uniform(0.85, 1.15))
        saisies.append({
            "produit": produit, "matiere": matiere, "machine": alea.choice(machines), "face": alea.choice("AB"),
            "meule": meule, "monte_il_y_a": 3 + round(numero * 1.3), "duree_jours": alea.randint(1, 3),
            "pression": 0 if alea.random() < 0.05 else alea.choice([5, 6, 6, 6, 7]),
            "vitesse_rotation": vitesse_meule, "vitesse_avance": avance, "hauteur_initiale": hauteur_initiale,
            "hauteur_finale": hauteur_finale, "compteur_fin": faces, "probleme": probleme, "themes": themes,
            "commentaire": commentaire,
        })
    return saisies
