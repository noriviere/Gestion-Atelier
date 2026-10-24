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
    ("regleur", "Régleur", "Équipe A", "Régleur et opérateur"),
    ("intendante", "Intendante", "", "Intendant"),
    ("operateur", "Opérateur", "(compte partagé)", "Régleur et opérateur"),
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
]

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
for _produit, _machines, _cadence in _AFFECTATIONS:
    _taille = TAILLES[_produit]
    for _machine in _machines:
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

MOUVEMENTS = [
    # référence article, type (entree / sortie), quantité, identifiant, commentaire
    ("PAT-M", "sortie", 4, "regleur", "Changement patins chargeur N7"),
    ("BAN-80", "sortie", 6, "operateur", "MAD1 poste du matin"),
    ("PEI-N11", "sortie", 1, "regleur", "Peigne cassé outillage face N11"),
    ("BAN-120", "entree", 50, "intendante", "Réception commande"),
    ("HUI-01", "sortie", 1, "operateur", "S2"),
    ("MEU-300", "sortie", 1, "regleur", "S7 changement de meule"),
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
