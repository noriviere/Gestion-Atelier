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


def tous_les_resultats():
    """Liste de (nom du groupe, [résultat, ...]) couvrant toutes les données consultables."""
    return [
        ("Articles", [
            resultat(article.reference, article.designation, article,
                     article.reference, article.designation, article.emplacement)
            for article in Article.objects.all()
        ]),
        ("Outils", [
            resultat(outil.code, outil.nom, outil, outil.code, outil.nom)
            for outil in Outil.objects.all()
        ]),
        ("Produits", [
            resultat(produit.reference, produit.designation, produit,
                     produit.reference, produit.designation, produit.client)
            for produit in Produit.objects.all()
        ]),
        ("Machines", [
            resultat(machine.code, machine.nom, machine, machine.code, machine.nom)
            for machine in Machine.objects.all()
        ]),
    ]


def rechercher(texte):
    """Groupes non vides dont chaque résultat contient tous les mots saisis, dans n'importe quel ordre."""
    mots = normaliser(texte).split()
    groupes = []
    for nom_groupe, resultats in tous_les_resultats():
        retenus = [res for res in resultats if all(mot in res["texte_cherche"] for mot in mots)]
        if retenus:
            groupes.append((nom_groupe, retenus))
    return groupes
