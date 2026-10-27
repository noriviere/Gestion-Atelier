"""Entrées du menu principal, adaptées au profil de l'utilisateur."""
from django.urls import reverse

from . import roles

from .droits import PAGES

# nom de l'entrée : (libellé, page de destination, pages où l'entrée est signalée comme courante)
ENTREES = {
    "accueil": ("Accueil", "accueil", {"accueil"}),
    "stock": ("Stock", "articles", {"articles", "article", "article_nouveau", "article_modifier", "import_articles"}),
    "a_commander": ("À commander", "a_commander", {"a_commander"}),
    "commandes": ("Commandes", "commandes", {"commandes", "commande"}),
    "fournisseurs": ("Fournisseurs", "fournisseurs", {"fournisseurs", "fournisseur", "fournisseur_nouveau", "fournisseur_modifier"}),
    "inventaires": ("Inventaires", "inventaires", {"inventaires", "comptage", "feuille_comptage", "ecarts"}),
    "outillage": ("Outillage", "outils", {"outils", "outil"}),
    "produits": ("Produits et machines", "produits", {
        "produits", "produit", "fiche", "machine", "nouveau_produit", "modifier_produit", "nouvelle_fiche",
        "modifier_fiche",
    }),
    "remontees": ("Remontées", "remontees", {"remontees", "montage_meule", "demontage_meule", "saisie_meule",
                                             "saisies_meules", "statistiques_meules", "controle_meules",
                                             "modifier_saisie_meule", "regles_meules"}),
    "droits": ("Droits", "droits", {"droits"}),
}

# Bureau (admin, méthode et management, intendant) : le stock et les commandes d'abord.
ORDRE_BUREAU = ["accueil", "stock", "a_commander", "commandes", "fournisseurs", "inventaires", "outillage", "produits",
                "remontees", "droits"]
# Atelier : les remontées et les fiches de production d'abord ; il suit les commandes (réceptions) mais ne les prépare pas.
ORDRE_ATELIER = ["accueil", "remontees", "produits", "outillage", "stock", "inventaires", "commandes", "droits"]


def entrees_menu(user, page_courante):
    """Liste de dicts (libelle, url, actif) dans l'ordre d'affichage pour ce profil, sans les pages qui lui sont fermées."""
    ordre = ORDRE_ATELIER if roles.profil(user) in (roles.REGLEUR, roles.OPERATEUR) else ORDRE_BUREAU
    entrees = []
    for nom in ordre:
        libelle, page_destination, pages_actives = ENTREES[nom]
        droit_necessaire = PAGES.get(page_destination)
        if droit_necessaire and not roles.a_le_droit(user, droit_necessaire):
            continue
        entrees.append({
            "libelle": libelle,
            "url": reverse(page_destination),
            "actif": page_courante in pages_actives,
        })
    return entrees
