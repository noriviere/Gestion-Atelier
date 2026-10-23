from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from comptes.roles import ADMIN, configurer_permissions
from demo import donnees as d
from inventaire.models import Article, ArticleFournisseur, Fournisseur, Mouvement, TypeInventaire
from outillage.models import Outil, PieceOutil
from produits.models import Consommation, Machine, Produit, ProduitMachine


class Command(BaseCommand):
    help = "Efface les données métier et charge les données fictives de demo/donnees.py."

    @transaction.atomic
    def handle(self, *args, **options):
        for modele in (Mouvement, Consommation, ProduitMachine, Produit, Machine, PieceOutil, Outil,
                       ArticleFournisseur, Article, TypeInventaire, Fournisseur):
            modele.objects.all().delete()
        configurer_permissions()

        comptes = {}
        for identifiant, prenom, nom, profil in d.COMPTES:
            user, _ = User.objects.get_or_create(username=identifiant)
            user.first_name, user.last_name = prenom, nom
            user.is_superuser = profil == ADMIN
            user.is_staff = profil != "Régleur et opérateur"
            user.set_password("demo")
            user.save()
            user.groups.set([Group.objects.get(name=profil)])
            comptes[identifiant] = user

        fournisseurs = {
            nom: Fournisseur.objects.create(nom=nom, contact=contact, telephone=tel)
            for nom, contact, tel in d.FOURNISSEURS
        }
        types = {nom: TypeInventaire.objects.create(nom=nom, description=desc) for nom, desc in d.TYPES_INVENTAIRE}
        aujourdhui = timezone.localdate()
        articles = {}
        for ref, des, cat, type_inv, empl, unite, stock, mini, mini_cde, freq, il_y_a in d.ARTICLES:
            articles[ref] = Article.objects.create(
                reference=ref, designation=des, categorie=cat, type_inventaire=types[type_inv],
                emplacement=empl, unite=unite, stock=stock, stock_mini=mini, mini_commande=mini_cde,
                frequence_inventaire=freq, dernier_inventaire=aujourdhui - timedelta(days=il_y_a),
            )
        for ref, fournisseur, ref_f, prix, delai, prefere in d.PRIX:
            ArticleFournisseur.objects.create(
                article=articles[ref], fournisseur=fournisseurs[fournisseur], reference_fournisseur=ref_f,
                prix=Decimal(str(prix)), delai=delai, prefere=prefere,
            )

        outils = {}
        for code, nom, parent, desc in d.OUTILS:
            outils[code] = Outil.objects.create(code=code, nom=nom, parent=outils.get(parent), description=desc)
        for code, ref, qte in d.PIECES_OUTILS:
            PieceOutil.objects.create(outil=outils[code], article=articles[ref], quantite=qte)

        machines = {code: Machine.objects.create(code=code, nom=nom, description=desc) for code, nom, desc in d.MACHINES}
        produits = {
            ref: Produit.objects.create(reference=ref, designation=des, client=client, notes=notes)
            for ref, des, client, notes in d.PRODUITS
        }
        fabrications = {}
        for ref, machine, cadence, codes_outils, notes in d.FABRICATIONS:
            fab = ProduitMachine.objects.create(produit=produits[ref], machine=machines[machine], cadence=cadence, notes=notes)
            fab.outils.set([outils[c] for c in codes_outils])
            fabrications[(ref, machine)] = fab
        for ref, machine, article, qte in d.CONSOMMATIONS:
            Consommation.objects.create(fabrication=fabrications[(ref, machine)], article=articles[article], quantite=qte)

        # Les stocks de demo/donnees.py sont les stocks finaux : on rejoue les mouvements
        # pour l'historique puis on remet le stock prévu.
        for ref, type_mvt, qte, identifiant, commentaire in d.MOUVEMENTS:
            art = articles[ref]
            stock_final = art.stock
            mvt = Mouvement.enregistrer(art, type_mvt, Decimal(qte), utilisateur=comptes.get(identifiant), commentaire=commentaire)
            Article.objects.filter(pk=art.pk).update(stock=stock_final)
            Mouvement.objects.filter(pk=mvt.pk).update(stock_apres=stock_final)

        self.stdout.write(self.style.SUCCESS(
            f"Démo chargée : {len(articles)} articles, {len(outils)} outils, {len(produits)} produits, "
            f"{len(machines)} machines, {len(comptes)} comptes (mot de passe : demo)."
        ))
