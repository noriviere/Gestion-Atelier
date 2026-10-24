"""Entrées du menu principal, adaptées au profil de l'utilisateur."""
from django.urls import reverse

from . import roles

# nom de l'entrée : (libellé, page de destination, pages où l'entrée est signalée comme courante)
ENTREES = {
    "accueil": ("Accueil", "accueil", {"accueil"}),
    "stock": ("Stock", "articles", {"articles", "article"}),
    "a_commander": ("À commander", "a_commander", {"a_commander"}),
    "commandes": ("Commandes", "commandes", {"commandes", "commande"}),
    "inventaires": ("Inventaires", "inventaires", {"inventaires", "comptage", "feuille_comptage"}),
    "outillage": ("Outillage", "outils", {"outils", "outil"}),
    "produits": ("Produits", "produits", {"produits", "produit", "fiche"}),
    "machines": ("Machines", "machines", {"machines", "machine"}),
}

# Bureau (admin, méthode et management) : le stock et les commandes d'abord.
ORDRE_BUREAU = ["accueil", "stock", "a_commander", "commandes", "inventaires", "outillage", "produits", "machines"]
# Atelier : les fiches de production d'abord ; il suit les commandes (réceptions) mais ne les prépare pas.
ORDRE_ATELIER = ["accueil", "produits", "machines", "outillage", "stock", "inventaires", "commandes"]


def entrees_menu(user, page_courante):
    """Liste de dicts (libelle, url, actif) dans l'ordre d'affichage pour ce profil."""
    ordre = ORDRE_ATELIER if roles.profil(user) == roles.ATELIER else ORDRE_BUREAU
    entrees = []
    for nom in ordre:
        libelle, page_destination, pages_actives = ENTREES[nom]
        entrees.append({
            "libelle": libelle,
            "url": reverse(page_destination),
            "actif": page_courante in pages_actives,
        })
    return entrees
