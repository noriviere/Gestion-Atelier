"""Sommaire du mode d'emploi, et page d'aide de chaque écran de l'application."""
from collections import namedtuple

Sujet = namedtuple("Sujet", "code titre resume")

# Dans l'ordre du sommaire. Le texte de chaque sujet est dans frontend/templates/aide/<code>.html.
SUJETS = [
    Sujet("navigation", "Se repérer dans l'application",
          "Menu, recherche, petits « i », thème sombre, téléphone et impression."),
    Sujet("profils", "Profils et droits",
          "Les cinq profils, ce que chacun peut faire, et la page Droits qui les règle."),
    Sujet("stock", "Stock et articles",
          "Liste du stock, fiche article, sorties et entrées, création d'articles, import et export Excel."),
    Sujet("fournisseurs", "Fournisseurs",
          "Coordonnées, articles fournis, prix, délais et fournisseur préféré."),
    Sujet("commandes", "À commander et commandes",
          "Articles sous le mini, préparation, passage, réception et entrée en stock des commandes."),
    Sujet("inventaires", "Inventaires et écarts",
          "Inventaires tournants, feuille de comptage, saisie des quantités comptées et rapport des écarts."),
    Sujet("outillage", "Outillage",
          "Arborescence des outils, pièces d'usure montées, sortie d'une pièce remplacée."),
    Sujet("produits", "Produits et machines",
          "La matrice produits × machines, ses états, et les pages produit et machine."),
    Sujet("fiches", "Fiches de production",
          "Cadence, paramètres de réglage, outillages, consommables, notes, photos et documents."),
    Sujet("remontees", "Remontées terrain",
          "Écran des remontées, montage et démontage d'une meule, contrôles, avertissements et valeurs calculées."),
    Sujet("demo", "La démo en ligne",
          "Choisir un profil, ce qui est simulé, et comment remettre la démo à zéro."),
]

PAR_CODE = {sujet.code: sujet for sujet in SUJETS}

# Nom de chaque page de l'application -> sujet du mode d'emploi ouvert par le bouton « ? » de la barre du haut.
SUJET_DE_LA_PAGE = {
    "recherche": "navigation",
    "droits": "profils",
    "articles": "stock",
    "article": "stock",
    "article_nouveau": "stock",
    "article_modifier": "stock",
    "import_articles": "stock",
    "fournisseurs": "fournisseurs",
    "fournisseur": "fournisseurs",
    "fournisseur_nouveau": "fournisseurs",
    "fournisseur_modifier": "fournisseurs",
    "a_commander": "commandes",
    "commandes": "commandes",
    "commande": "commandes",
    "inventaires": "inventaires",
    "comptage": "inventaires",
    "feuille_comptage": "inventaires",
    "ecarts": "inventaires",
    "outils": "outillage",
    "outil": "outillage",
    "nouvel_outil": "outillage",
    "modifier_outil": "outillage",
    "produits": "produits",
    "produit": "produits",
    "machine": "produits",
    "nouveau_produit": "produits",
    "modifier_produit": "produits",
    "fiche": "fiches",
    "nouvelle_fiche": "fiches",
    "modifier_fiche": "fiches",
    "remontees": "remontees",
    "montage_meule": "remontees",
    "demontage_meule": "remontees",
    "saisie_meule": "remontees",
    "saisies_meules": "remontees",
    "statistiques_meules": "remontees",
    "controle_meules": "remontees",
    "modifier_saisie_meule": "remontees",
    "regles_meules": "remontees",
}


def voisins(code):
    """Sujets précédent et suivant dans le sommaire (None aux extrémités)."""
    position = [sujet.code for sujet in SUJETS].index(code)
    precedent = SUJETS[position - 1] if position > 0 else None
    suivant = SUJETS[position + 1] if position + 1 < len(SUJETS) else None
    return precedent, suivant
