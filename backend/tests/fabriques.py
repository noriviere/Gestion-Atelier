"""Petites fonctions pour créer des données de test lisibles."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.utils import timezone

from inventaire.models import Article, ArticleFournisseur, Fournisseur, TypeInventaire


def creer_type_inventaire(nom="Magasin"):
    return TypeInventaire.objects.get_or_create(nom=nom)[0]


def creer_article(reference="ART-1", stock=10, stock_mini=5, mini_commande=10, frequence_inventaire=90,
                  inventorie_il_y_a_jours=0, type_inventaire=None, **autres_champs):
    dernier_inventaire = None
    if inventorie_il_y_a_jours is not None:
        dernier_inventaire = timezone.localdate() - timedelta(days=inventorie_il_y_a_jours)
    return Article.objects.create(
        reference=reference,
        designation=autres_champs.pop("designation", f"Article {reference}"),
        type_inventaire=type_inventaire or creer_type_inventaire(),
        stock=Decimal(stock),
        stock_mini=Decimal(stock_mini),
        mini_commande=Decimal(mini_commande),
        frequence_inventaire=frequence_inventaire,
        dernier_inventaire=dernier_inventaire,
        **autres_champs,
    )


def lier_fournisseur(article, nom_fournisseur, prefere=False, prix=None):
    fournisseur = Fournisseur.objects.get_or_create(nom=nom_fournisseur)[0]
    return ArticleFournisseur.objects.create(article=article, fournisseur=fournisseur, prefere=prefere, prix=prix)


def creer_utilisateur(identifiant, profil=None, superutilisateur=False):
    utilisateur = User.objects.create_user(identifiant, password="test", is_superuser=superutilisateur,
                                           is_staff=superutilisateur)
    if profil:
        utilisateur.groups.add(Group.objects.get(name=profil))
    return utilisateur
