"""Données fictives de la démo, sur la base décrite par Noel.

Machines S1 à S8, MAD1 et MAD2 ; produits N2 à N12 ; pour chaque produit un jeu d'outils
(chargeur, outillage face, pince, outillage dos) qui porte des pièces d'usure
(patin, porte-lame, tige, peigne) ; consommables : huile, bandes et meules.

Les pièces d'usure existent en trois tailles (P, M, G) partagées entre produits voisins :
une même pièce apparaît donc dans plusieurs outils, comme dans la réalité.
Modifier ce fichier puis relancer `python manage.py charger_demo` suffit pour changer la démo.
Les dates de dernier inventaire sont exprimées en « il y a N jours ».
"""

COMPTES = [
    # identifiant, prénom, nom, profil
    ("admin", "Admin", "", "Admin"),
    ("methode", "Noël", "Méthodes", "Méthode et management"),
    ("chef", "Chef", "d'équipe", "Méthode et management"),
    ("regleur", "Régleur", "Équipe A", "Régleur et opérateur"),
    ("intendante", "Intendante", "", "Régleur et opérateur"),
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
    ("PL-G", "Porte-lame taille G", "usure", "Magasin pièces d'usure", "A2-03", "pièce", 6, 3, 3, 180, 60),
    ("TIG-P", "Tige taille P", "usure", "Magasin pièces d'usure", "A3-01", "pièce", 22, 12, 24, 90, 95),
    ("TIG-M", "Tige taille M", "usure", "Magasin pièces d'usure", "A3-02", "pièce", 18, 12, 24, 90, 20),
    ("TIG-G", "Tige taille G", "usure", "Magasin pièces d'usure", "A3-03", "pièce", 9, 10, 20, 90, 20),
    ("PEI-P", "Peigne taille P", "usure", "Magasin pièces d'usure", "A4-01", "pièce", 7, 4, 6, 120, 40),
    ("PEI-M", "Peigne taille M", "usure", "Magasin pièces d'usure", "A4-02", "pièce", 8, 4, 6, 120, 130),
    ("PEI-G", "Peigne taille G", "usure", "Magasin pièces d'usure", "A4-03", "pièce", 2, 3, 6, 120, 40),
    ("HUI-01", "Bidon d'huile de coupe 20 L", "conso", "Huiles", "C1", "bidon", 3, 4, 6, 30, 35),
    ("BAN-40", "Bande abrasive grain 40", "conso", "Abrasifs", "B1-01", "bande", 35, 20, 50, 30, 10),
    ("BAN-80", "Bande abrasive grain 80", "conso", "Abrasifs", "B1-02", "bande", 18, 20, 50, 30, 10),
    ("BAN-120", "Bande abrasive grain 120", "conso", "Abrasifs", "B1-03", "bande", 42, 20, 50, 30, 40),
    ("BAN-240", "Bande abrasive grain 240 finition", "conso", "Abrasifs", "B1-04", "bande", 25, 10, 25, 30, 10),
    ("MEU-200", "Meule Ø200 corindon", "conso", "Abrasifs", "B2-01", "meule", 6, 4, 6, 60, 20),
    ("MEU-300", "Meule Ø300 corindon", "conso", "Abrasifs", "B2-02", "meule", 2, 3, 4, 60, 70),
    ("MEU-CBN", "Meule CBN de finition", "conso", "Abrasifs", "B2-03", "meule", 3, 2, 2, 60, 20),
]

PRIX = [
    # référence article, fournisseur, référence fournisseur, prix (€), délai (jours), préféré
    *[(f"PAT-{t}", "Mécanique Précision Sud", f"MPS-PAT{t}", 18.0, 10, True) for t in "PMG"],
    *[(f"PAT-{t}", "Usinage Martin", f"UM-P{t}", 21.0, 6, False) for t in "PMG"],
    *[(f"PL-{t}", "Usinage Martin", f"UM-PL{t}", 145.0, 15, True) for t in "PMG"],
    *[(f"TIG-{t}", "Mécanique Précision Sud", f"MPS-TG{t}", 9.5, 10, True) for t in "PMG"],
    *[(f"PEI-{t}", "Usinage Martin", f"UM-PE{t}", 62.0, 15, True) for t in "PMG"],
    *[(f"PEI-{t}", "Mécanique Précision Sud", f"MPS-PE{t}", 58.0, 25, False) for t in "PMG"],
    ("HUI-01", "Lubrifiants de l'Ouest", "LO-HC20", 92.0, 4, True),
    *[(f"BAN-{g}", "Abrasifs Industriels", f"AI-B{g}", 6.8, 5, True) for g in (40, 80, 120, 240)],
    *[(f"BAN-{g}", "Meules et Bandes Diffusion", f"MBD-{g}", 7.4, 3, False) for g in (40, 80, 120, 240)],
    ("MEU-200", "Meules et Bandes Diffusion", "MBD-M200", 85.0, 10, True),
    ("MEU-300", "Meules et Bandes Diffusion", "MBD-M300", 140.0, 10, True),
    ("MEU-CBN", "Meules et Bandes Diffusion", "MBD-CBN", 690.0, 30, True),
]

MACHINES = [
    # code, nom, description
    *[(f"S{i}", f"Ligne S{i}", "Ligne de production à bandes") for i in range(1, 9)],
    ("MAD1", "Machine à meule 1", "Rectification à la meule"),
    ("MAD2", "Machine à meule 2", "Rectification à la meule"),
]

# Chaque produit a son jeu d'outils : un outil principal et quatre sous-ensembles.
SOUS_ENSEMBLES = [
    # numéro (ordre d'affichage), nom, pièces d'usure montées (préfixe de référence, quantité)
    ("1", "Chargeur", [("PAT", 2), ("TIG", 2)]),
    ("2", "Outillage face", [("PL", 1), ("PEI", 1)]),
    ("3", "Pince", [("PAT", 2)]),
    ("4", "Outillage dos", [("PL", 1), ("PEI", 1), ("TIG", 1)]),
]

OUTILS = [
    # code, nom, code de l'outil parent (vide si outil principal), description
]
PIECES_OUTILS = [
    # code outil, référence article, quantité montée
]
for _p in PRODUITS_LISTE:
    OUTILS.append((f"OUT-{_p}", f"Jeu d'outils {_p}", "", f"Jeu complet pour le produit {_p} (taille {TAILLES[_p]})."))
    for _suffixe, _nom, _pieces in SOUS_ENSEMBLES:
        OUTILS.append((f"OUT-{_p}-{_suffixe}", f"{_nom} {_p}", f"OUT-{_p}", ""))
        for _prefixe, _qte in _pieces:
            PIECES_OUTILS.append((f"OUT-{_p}-{_suffixe}", f"{_prefixe}-{TAILLES[_p]}", _qte))

PRODUITS = [
    # référence, désignation, client, notes générales
    (p, f"Produit {p}", "", "Contrôle visuel en début de série et toutes les 2 heures.")
    for p in PRODUITS_LISTE
]

# Produit, machines, cadence (pièces/h)
_AFFECTATIONS = [
    ("N2", ["S1", "S2"], 480), ("N3", ["S1", "S2"], 460), ("N4", ["S3"], 450), ("N5", ["S3", "S4"], 420),
    ("N6", ["S4"], 380), ("N7", ["S5", "MAD1"], 360), ("N8", ["S5", "S6"], 340), ("N9", ["S6", "MAD1"], 320),
    ("N10", ["S7", "MAD2"], 280), ("N11", ["S7", "S8"], 260), ("N12", ["S8", "MAD2"], 240),
]
_BANDE = {"P": "BAN-120", "M": "BAN-80", "G": "BAN-40"}
_MEULE = {"P": "MEU-200", "M": "MEU-200", "G": "MEU-300"}

FABRICATIONS = [
    # référence produit, code machine, cadence (pièces/h), codes outils, notes de réglage
]
CONSOMMATIONS = [
    # référence produit, code machine, référence article, quantité / fréquence
]
for _p, _machines, _cadence in _AFFECTATIONS:
    _t = TAILLES[_p]
    for _m in _machines:
        if _m.startswith("MAD"):
            FABRICATIONS.append((_p, _m, round(_cadence * 0.8), [f"OUT-{_p}"],
                                 f"Meule {_MEULE[_t]}, dresser la meule toutes les 2 h.\nVérifier le serrage de la pince à chaque prise de poste."))
            CONSOMMATIONS += [(_p, _m, _MEULE[_t], "1 meule / semaine"), (_p, _m, "MEU-CBN", "finition, selon usure"),
                              (_p, _m, "HUI-01", "1 bidon / semaine")]
        else:
            FABRICATIONS.append((_p, _m, _cadence, [f"OUT-{_p}"],
                                 f"Bande {_BANDE[_t]} en ébauche, BAN-240 en finition.\nRégler la hauteur du peigne avant démarrage.\nVérifier le serrage de la pince à chaque prise de poste."))
            CONSOMMATIONS += [(_p, _m, _BANDE[_t], "1 bande / poste"), (_p, _m, "BAN-240", "1 bande / 2 postes"),
                              (_p, _m, "HUI-01", "1 bidon / 2 semaines")]

MOUVEMENTS = [
    # référence article, type (entree / sortie), quantité, identifiant, commentaire
    ("PAT-M", "sortie", 4, "regleur", "Changement patins chargeur N7"),
    ("BAN-80", "sortie", 6, "operateur", "S5 poste du matin"),
    ("PEI-G", "sortie", 1, "regleur", "Peigne cassé outillage face N11"),
    ("BAN-120", "entree", 50, "intendante", "Réception commande"),
    ("HUI-01", "sortie", 1, "operateur", "S2"),
]
