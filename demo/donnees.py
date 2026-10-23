"""Données fictives de la démo.

Tout est décrit ici sous forme de listes simples : modifier ce fichier puis relancer
`python manage.py charger_demo` suffit pour changer le contenu de la démo.
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
    ("Outillage Durand", "M. Durand", "04 72 00 00 01"),
    ("Mécaprécis", "Service commercial", "04 72 00 00 02"),
    ("Ressorts du Rhône", "Mme Martin", "04 72 00 00 03"),
    ("Fournitures Industrielles Lyonnaises", "Comptoir", "04 72 00 00 04"),
]

TYPES_INVENTAIRE = [
    # nom, description
    ("Magasin outillage", "Pièces d'usure rangées au magasin"),
    ("Consommables atelier", "Armoire consommables en bord de ligne"),
    ("EPI", "Équipements de protection individuelle"),
]

ARTICLES = [
    # référence, désignation, catégorie (usure / conso), type d'inventaire, emplacement, unité,
    # stock, stock mini, mini de commande, fréquence d'inventaire (jours), dernier inventaire (il y a N jours)
    ("PU-0001", "Poinçon Ø6 carbure", "usure", "Magasin outillage", "A1-01", "pièce", 4, 6, 10, 90, 20),
    ("PU-0002", "Poinçon Ø10 carbure", "usure", "Magasin outillage", "A1-02", "pièce", 12, 4, 6, 90, 20),
    ("PU-0003", "Matrice Ø6", "usure", "Magasin outillage", "A1-03", "pièce", 3, 2, 2, 90, 120),
    ("PU-0004", "Ressort de dévêtisseur 20x60", "usure", "Magasin outillage", "A2-01", "pièce", 30, 20, 50, 60, 70),
    ("PU-0005", "Colonne de guidage Ø25", "usure", "Magasin outillage", "A2-02", "pièce", 2, 2, 4, 180, 30),
    ("PU-0006", "Bague de guidage Ø25", "usure", "Magasin outillage", "A2-03", "pièce", 8, 4, 4, 180, 30),
    ("PU-0007", "Lame de cisaille 300 mm", "usure", "Magasin outillage", "A3-01", "pièce", 1, 2, 2, 90, 100),
    ("PU-0008", "Pilote de centrage Ø8", "usure", "Magasin outillage", "A3-02", "pièce", 15, 5, 10, 90, 10),
    ("PU-0009", "Vérin azote 750 daN", "usure", "Magasin outillage", "A3-03", "pièce", 3, 2, 2, 180, 200),
    ("CO-0001", "Huile de frappe (bidon 20 L)", "conso", "Consommables atelier", "B1", "bidon", 2, 3, 4, 30, 40),
    ("CO-0002", "Graisse de guidage (cartouche)", "conso", "Consommables atelier", "B1", "cartouche", 18, 6, 12, 30, 5),
    ("CO-0003", "Chiffons d'essuyage (sac 10 kg)", "conso", "Consommables atelier", "B2", "sac", 4, 2, 5, 30, 5),
    ("CO-0004", "Bombe dégrippant", "conso", "Consommables atelier", "B2", "bombe", 5, 6, 12, 30, 35),
    ("CO-0005", "Gants anti-coupure T9", "conso", "EPI", "C1", "paire", 40, 30, 50, 30, 10),
    ("CO-0006", "Bouchons d'oreille (boîte 200)", "conso", "EPI", "C1", "boîte", 1, 2, 4, 60, 65),
]

PRIX = [
    # référence article, fournisseur, référence fournisseur, prix (€), délai (jours), préféré
    ("PU-0001", "Outillage Durand", "OD-P6C", 48.00, 10, True),
    ("PU-0001", "Mécaprécis", "MP-6-CARB", 52.50, 5, False),
    ("PU-0002", "Outillage Durand", "OD-P10C", 61.00, 10, True),
    ("PU-0003", "Outillage Durand", "OD-M6", 95.00, 15, True),
    ("PU-0004", "Ressorts du Rhône", "RR-20-60", 3.20, 7, True),
    ("PU-0005", "Mécaprécis", "MP-COL25", 74.00, 12, True),
    ("PU-0006", "Mécaprécis", "MP-BAG25", 38.00, 12, True),
    ("PU-0007", "Outillage Durand", "OD-L300", 210.00, 20, True),
    ("PU-0008", "Mécaprécis", "MP-PIL8", 12.40, 5, True),
    ("PU-0009", "Mécaprécis", "MP-AZ750", 320.00, 21, True),
    ("CO-0001", "Fournitures Industrielles Lyonnaises", "FIL-HF20", 89.00, 3, True),
    ("CO-0002", "Fournitures Industrielles Lyonnaises", "FIL-GR400", 7.90, 3, True),
    ("CO-0003", "Fournitures Industrielles Lyonnaises", "FIL-CH10", 24.00, 3, True),
    ("CO-0004", "Fournitures Industrielles Lyonnaises", "FIL-DEG", 6.50, 3, True),
    ("CO-0005", "Fournitures Industrielles Lyonnaises", "FIL-GAC9", 4.80, 3, True),
    ("CO-0006", "Fournitures Industrielles Lyonnaises", "FIL-BO200", 29.00, 3, True),
]

MACHINES = [
    # code, nom, description
    ("PR-01", "Presse 250 t", "Presse mécanique, ligne 1"),
    ("PR-02", "Presse 400 t", "Presse hydraulique, ligne 2"),
    ("CI-01", "Cisaille guillotine", "Débit des flans"),
]

OUTILS = [
    # code, nom, code de l'outil parent (vide si outil principal), description
    ("OUT-101", "Outil à suivre support moteur", "", "Outil 6 postes. Changement de bande : voir notice dans l'armoire."),
    ("OUT-101-A", "Bloc poinçons", "OUT-101", ""),
    ("OUT-101-B", "Bloc matrice", "OUT-101", ""),
    ("OUT-101-C", "Guidage", "OUT-101", ""),
    ("OUT-205", "Outil de découpe flasque", "", "Outil simple, découpe et poinçonnage."),
    ("OUT-205-A", "Ensemble poinçon central", "OUT-205", ""),
    ("OUT-301", "Jeu de lames cisaille", "", ""),
]

PIECES_OUTILS = [
    # code outil, référence article, quantité montée
    ("OUT-101-A", "PU-0001", 4),
    ("OUT-101-A", "PU-0002", 2),
    ("OUT-101-A", "PU-0008", 2),
    ("OUT-101-B", "PU-0003", 4),
    ("OUT-101-B", "PU-0004", 8),
    ("OUT-101-C", "PU-0005", 4),
    ("OUT-101-C", "PU-0006", 4),
    ("OUT-205", "PU-0009", 4),
    ("OUT-205-A", "PU-0002", 1),
    ("OUT-205-A", "PU-0004", 6),
    ("OUT-301", "PU-0007", 2),
]

PRODUITS = [
    # référence, désignation, client, notes générales
    ("P-1001", "Support moteur gauche", "Client A", "Pièce de sécurité : contrôle visuel 100 %."),
    ("P-1002", "Support moteur droit", "Client A", "Pièce de sécurité : contrôle visuel 100 %."),
    ("P-2001", "Flasque Ø120", "Client B", ""),
    ("F-0001", "Flan 300 x 150 ép. 3", "Interne", "Flan pour P-1001 et P-1002."),
]

FABRICATIONS = [
    # référence produit, code machine, cadence (pièces/h), codes outils, notes de réglage
    ("P-1001", "PR-01", 900, ["OUT-101"], "Hauteur de fermeture 312 mm.\nAvance bande 85 mm.\nGraisser les colonnes à chaque prise de poste."),
    ("P-1002", "PR-01", 900, ["OUT-101"], "Même outil que P-1001, retourner l'insert du poste 4."),
    ("P-1001", "PR-02", 600, ["OUT-101"], "Secours uniquement. Hauteur de fermeture 318 mm."),
    ("P-2001", "PR-02", 1200, ["OUT-205"], "Vérifier la pression des vérins azote au démarrage."),
    ("F-0001", "CI-01", 400, ["OUT-301"], "Jeu de lames 0,3 mm pour ép. 3."),
]

CONSOMMATIONS = [
    # référence produit, code machine, référence article, quantité / fréquence
    ("P-1001", "PR-01", "CO-0001", "1 bidon / semaine"),
    ("P-1001", "PR-01", "CO-0002", "1 cartouche / poste"),
    ("P-1002", "PR-01", "CO-0001", "1 bidon / semaine"),
    ("P-1002", "PR-01", "CO-0002", "1 cartouche / poste"),
    ("P-2001", "PR-02", "CO-0001", "2 bidons / semaine"),
    ("P-2001", "PR-02", "CO-0004", "selon besoin"),
    ("F-0001", "CI-01", "CO-0003", "1 sac / semaine"),
]

MOUVEMENTS = [
    # référence article, type (entree / sortie), quantité, identifiant, commentaire
    ("PU-0001", "sortie", 4, "regleur", "Changement poinçons OUT-101 poste 2"),
    ("CO-0001", "sortie", 1, "operateur", ""),
    ("PU-0004", "entree", 50, "intendante", "Réception commande"),
    ("PU-0007", "sortie", 1, "regleur", "Lame ébréchée"),
]
