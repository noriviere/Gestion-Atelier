"""Catalogue des droits : de grands blocs, chacun découpé en sous-fonctions.

Chaque profil reçoit une liste de sous-fonctions, modifiable sur la page « Droits ».
Une sous-fonction peut donner des permissions de l'administration Django
(« app.codename »), ce qui ouvre les écrans de paramétrage correspondants.
"""
from collections import namedtuple

Fonction = namedtuple("Fonction", "code libelle permissions_django")
Bloc = namedtuple("Bloc", "code libelle fonctions")


def _vues(*modeles):
    return [f"{app}.view_{modele}" for app, modele in (m.split(".") for m in modeles)]


def _edition(*modeles):
    return [
        f"{app}.{action}_{modele}"
        for app, modele in (m.split(".") for m in modeles)
        for action in ("add", "change", "delete")
    ]


BLOCS = [
    Bloc("stock", "Stock et inventaires", [
        Fonction("stock_consulter", "Consulter le stock, les articles et les inventaires",
                 _vues("inventaire.article", "inventaire.articlefournisseur", "inventaire.fournisseur",
                       "inventaire.typeinventaire", "inventaire.mouvement")),
        Fonction("stock_mouvements", "Saisir des sorties et des entrées de stock", ["inventaire.add_mouvement"]),
        Fonction("stock_comptages", "Saisir les comptages d'inventaire (corrige le stock)", []),
        Fonction("stock_articles", "Créer et modifier les articles, seuils et types d'inventaire",
                 _edition("inventaire.article", "inventaire.articlefournisseur", "inventaire.typeinventaire")),
        Fonction("stock_fournisseurs", "Créer et modifier les fournisseurs", _edition("inventaire.fournisseur")),
    ]),
    Bloc("commandes", "Commandes fournisseurs", [
        Fonction("commandes_consulter", "Consulter les commandes et la liste « À commander »",
                 _vues("commandes.commande", "commandes.lignecommande")),
        Fonction("commandes_preparer", "Préparer, modifier, passer et annuler les commandes",
                 _edition("commandes.commande", "commandes.lignecommande")),
        Fonction("commandes_receptionner", "Marquer reçue et réceptionner une commande", []),
    ]),
    Bloc("outillage", "Outillage", [
        Fonction("outillage_consulter", "Consulter les outils et leurs pièces d'usure",
                 _vues("outillage.outil", "outillage.pieceoutil")),
        Fonction("outillage_modifier", "Créer et modifier les outils", _edition("outillage.outil", "outillage.pieceoutil")),
    ]),
    Bloc("produits", "Produits, machines et fiches", [
        Fonction("produits_consulter", "Consulter la matrice, les produits, les machines et les fiches",
                 _vues("produits.produit", "produits.machine", "produits.produitmachine", "produits.consommation",
                       "produits.parametre")),
        Fonction("produits_documents_voir", "Voir les photos et les documents des fiches", _vues("produits.document")),
        Fonction("produits_documents_gerer", "Ajouter et retirer des photos et des documents", []),
        Fonction("produits_reglages", "Modifier les paramètres et notes de réglage d'une fiche", []),
        Fonction("produits_modifier", "Créer, modifier et dupliquer produits et fiches, changer la matrice",
                 _edition("produits.produit", "produits.machine", "produits.produitmachine", "produits.consommation",
                          "produits.parametre", "produits.document")),
    ]),
    Bloc("administration", "Administration", [
        Fonction("admin_droits", "Gérer les droits des profils et le profil des comptes", []),
    ]),
]

FONCTIONS = {fonction.code: fonction for bloc in BLOCS for fonction in bloc.fonctions}
TOUS_LES_CODES = list(FONCTIONS)

# Nom de chaque page -> sous-fonction nécessaire pour l'ouvrir (contrôlé par DroitsDeConsultationMiddleware).
# Les pages absentes sont ouvertes à tout compte connecté, ou contrôlées dans leur vue :
# modifier_fiche (produits_modifier, ou produits_reglages pour une fiche existante), et les actions
# des pages article, comptage et commande, qui dépendent de ce qui est envoyé.
PAGES = {
    "articles": "stock_consulter",
    "article": "stock_consulter",
    "export_articles": "stock_consulter",
    "article_nouveau": "stock_articles",
    "article_modifier": "stock_articles",
    "import_articles": "stock_articles",
    "modele_import": "stock_articles",
    "inventaires": "stock_consulter",
    "ecarts": "stock_consulter",
    "comptage": "stock_consulter",
    "feuille_comptage": "stock_consulter",
    "fournisseurs": "stock_consulter",
    "fournisseur": "stock_consulter",
    "fournisseur_nouveau": "stock_fournisseurs",
    "fournisseur_modifier": "stock_fournisseurs",
    "a_commander": "commandes_consulter",
    "commandes": "commandes_consulter",
    "commande": "commandes_consulter",
    "creer_commande": "commandes_preparer",
    "outils": "outillage_consulter",
    "outil": "outillage_consulter",
    "nouvel_outil": "outillage_modifier",
    "modifier_outil": "outillage_modifier",
    "supprimer_outil": "outillage_modifier",
    "sortie_piece": "stock_mouvements",
    "produits": "produits_consulter",
    "produit": "produits_consulter",
    "fiche": "produits_consulter",
    "machine": "produits_consulter",
    "changer_etat": "produits_modifier",
    "nouveau_produit": "produits_modifier",
    "modifier_produit": "produits_modifier",
    "dupliquer_produit": "produits_modifier",
    "nouvelle_fiche": "produits_modifier",
    "dupliquer_fiche": "produits_modifier",
    "document": "produits_documents_voir",
    "ajouter_document": "produits_documents_gerer",
    "supprimer_document": "produits_documents_gerer",
    "droits": "admin_droits",
}

# Pages hors de PAGES : ouvertes à tout compte connecté (leur contenu suit les droits), ou dont la vue
# vérifie elle-même les droits. Un test oblige chaque nouvelle page à figurer dans l'une des deux listes.
PAGES_SANS_DROIT_UNIQUE = {"connexion", "deconnexion", "accueil", "recherche", "aide", "aide_sujet", "modifier_fiche"}

_ATELIER = ["stock_consulter", "stock_mouvements", "commandes_consulter", "commandes_receptionner",
            "outillage_consulter", "produits_consulter"]

# Droits de départ de chaque profil, avant toute modification sur la page « Droits ».
# Le profil Admin a toujours tout et n'apparaît pas ici.
DEFAUTS = {
    "Méthode et management": [code for code in TOUS_LES_CODES if code != "admin_droits"],
    "Intendant": ["stock_consulter", "stock_mouvements", "stock_comptages", "stock_articles", "stock_fournisseurs",
                  "commandes_consulter", "commandes_preparer", "commandes_receptionner",
                  "outillage_consulter", "produits_consulter"],
    "Régleur": _ATELIER + ["produits_documents_voir", "produits_documents_gerer", "produits_reglages"],
    "Opérateur": _ATELIER,
}
