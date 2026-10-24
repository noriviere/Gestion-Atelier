"""Recherche globale : articles, outils, produits et machines, depuis la barre du haut."""
import unicodedata

from outillage.models import Outil
from produits.models import Machine, Produit

from .models import Article


def normaliser(texte):
    """Minuscules, sans accents : « Pièce » et « piece » se retrouvent."""
    decompose = unicodedata.normalize("NFD", texte.lower())
    return "".join(caractere for caractere in decompose if not unicodedata.combining(caractere))


def resultat(titre, detail, objet, *champs_cherches):
    return {
        "titre": titre,
        "detail": detail,
        "url": objet.get_absolute_url(),
        "texte_cherche": normaliser(" ".join(champ for champ in champs_cherches if champ)),
    }


# Droit de consultation nécessaire pour voir chaque groupe de résultats (le même que pour ouvrir les fiches).
GROUPES = [
    ("Articles", "stock_consulter", lambda: [
        resultat(article.reference, article.designation, article, article.reference, article.designation, article.emplacement)
        for article in Article.objects.all()
    ]),
    ("Outils", "outillage_consulter", lambda: [
        resultat(outil.code, outil.nom, outil, outil.code, outil.nom) for outil in Outil.objects.all()
    ]),
    ("Produits", "produits_consulter", lambda: [
        resultat(produit.reference, produit.designation, produit, produit.reference, produit.designation, produit.client)
        for produit in Produit.objects.all()
    ]),
    ("Machines", "produits_consulter", lambda: [
        resultat(machine.code, machine.nom, machine, machine.code, machine.nom) for machine in Machine.objects.all()
    ]),
]


def tous_les_resultats(droits=None):
    """Liste de (nom du groupe, [résultat, ...]) des données consultables avec ces droits (toutes si None)."""
    return [(nom, lister()) for nom, droit, lister in GROUPES if droits is None or droit in droits]


def rechercher(texte, droits=None):
    """Groupes non vides dont chaque résultat contient tous les mots saisis, dans n'importe quel ordre."""
    mots = normaliser(texte).split()
    groupes = []
    for nom_groupe, resultats in tous_les_resultats(droits):
        retenus = [res for res in resultats if all(mot in res["texte_cherche"] for mot in mots)]
        if retenus:
            groupes.append((nom_groupe, retenus))
    return groupes
