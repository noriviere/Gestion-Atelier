import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from commandes.models import Commande, LigneCommande
from comptes.roles import ADMIN, configurer_permissions
from demo import donnees, fichiers
from inventaire.models import Article, ArticleFournisseur, Fournisseur, Mouvement, TypeInventaire
from outillage.models import Outil, PieceOutil
from produits.models import Consommation, Document, Machine, Parametre, Produit, ProduitMachine
from remontees import regles
from remontees.models import FormatMatiere, HistoriqueRegle, Matricule, RegleMeule, SaisieMeule, ThemeProbleme

MOT_DE_PASSE_DEMO = "demo"


class Command(BaseCommand):
    help = ("Efface les données métier et charge les données fictives de demo/donnees.py. "
            "Les comptes de démo (admin compris) reprennent le mot de passe « demo ».")

    def add_arguments(self, parser):
        parser.add_argument("--effacer-tout", action="store_true",
                            help="Obligatoire hors mode DEBUG : confirme l'effacement des données réelles.")

    @transaction.atomic
    def handle(self, *args, **options):
        # Sur une installation réelle (DEBUG coupé), la commande effacerait le stock et les commandes.
        if not settings.DEBUG and not options["effacer_tout"]:
            raise CommandError("Cette commande efface toutes les données et remet le mot de passe « demo » aux comptes "
                               "de démo. Hors démo, relancez-la avec --effacer-tout si c'est bien voulu.")
        self.effacer_donnees_metier()
        configurer_permissions(reinitialiser=True)
        comptes = self.creer_comptes()
        articles = self.creer_stock()
        outils = self.creer_outillage(articles)
        produits, machines = self.creer_produits(articles, outils)
        self.creer_mouvements(articles, comptes)
        self.creer_comptages(articles, comptes)
        commandes = self.creer_commandes(articles, comptes)
        saisies_meules = self.creer_remontees(articles, produits, machines, comptes)
        self.stdout.write(self.style.SUCCESS(
            f"Démo chargée : {len(articles)} articles, {len(outils)} outils, {len(produits)} produits, "
            f"{len(machines)} machines, {len(commandes)} commandes, {len(saisies_meules)} saisies meules, "
            f"{len(comptes)} comptes (mot de passe : {MOT_DE_PASSE_DEMO})."
        ))

    @staticmethod
    def effacer_donnees_metier():
        for document in Document.objects.all():
            document.fichier.delete(save=False)
        for modele in (SaisieMeule, FormatMatiere, Matricule, RegleMeule, HistoriqueRegle, ThemeProbleme,
                       LigneCommande, Commande, Mouvement, Document, Parametre, Consommation, ProduitMachine, Produit, Machine, PieceOutil, Outil,
                       ArticleFournisseur, Article, TypeInventaire, Fournisseur):
            modele.objects.all().delete()

    @staticmethod
    def creer_comptes():
        comptes = {}
        for identifiant, prenom, nom, profil in donnees.COMPTES:
            utilisateur, _ = User.objects.get_or_create(username=identifiant)
            utilisateur.first_name, utilisateur.last_name = prenom, nom
            utilisateur.is_superuser = profil == ADMIN
            # L'administration s'ouvre selon les droits du profil (page « Droits »), voir config/urls.py.
            utilisateur.is_staff = profil == ADMIN
            utilisateur.set_password(MOT_DE_PASSE_DEMO)
            utilisateur.save()
            utilisateur.groups.set([Group.objects.get(name=profil)])
            comptes[identifiant] = utilisateur
        return comptes

    @staticmethod
    def creer_stock():
        fournisseurs = {
            nom: Fournisseur.objects.create(nom=nom, contact=contact, telephone=telephone)
            for nom, contact, telephone in donnees.FOURNISSEURS
        }
        types_inventaire = {
            nom: TypeInventaire.objects.create(nom=nom, description=description)
            for nom, description in donnees.TYPES_INVENTAIRE
        }
        aujourdhui = timezone.localdate()
        articles = {}
        for (reference, designation, categorie, type_inventaire, emplacement, unite, stock, stock_mini,
             mini_commande, frequence_jours, inventorie_il_y_a_jours) in donnees.ARTICLES:
            articles[reference] = Article.objects.create(
                reference=reference, designation=designation, categorie=categorie,
                type_inventaire=types_inventaire[type_inventaire], emplacement=emplacement, unite=unite,
                origine=Article.DESIGN_INTERNE if reference in donnees.PLANS else Article.ACHAT,
                numero_plan=donnees.PLANS.get(reference, ""),
                stock=stock, stock_mini=stock_mini, mini_commande=mini_commande,
                frequence_inventaire=frequence_jours,
                dernier_inventaire=aujourdhui - timedelta(days=inventorie_il_y_a_jours),
            )
        for reference, fournisseur, reference_fournisseur, prix, delai_jours, prefere in donnees.PRIX:
            ArticleFournisseur.objects.create(
                article=articles[reference], fournisseur=fournisseurs[fournisseur],
                reference_fournisseur=reference_fournisseur, prix=Decimal(str(prix)), delai=delai_jours,
                prefere=prefere,
            )
        return articles

    @staticmethod
    def creer_outillage(articles):
        outils = {}
        for code, nom, code_parent, description in donnees.OUTILS:
            outils[code] = Outil.objects.create(
                code=code, nom=nom, parent=outils.get(code_parent), description=description
            )
        for code_outil, reference, quantite in donnees.PIECES_OUTILS:
            PieceOutil.objects.create(outil=outils[code_outil], article=articles[reference], quantite=quantite)
        return outils

    @staticmethod
    def creer_produits(articles, outils):
        machines = {
            code: Machine.objects.create(code=code, nom=nom, description=description)
            for code, nom, description in donnees.MACHINES
        }
        produits = {
            reference: Produit.objects.create(reference=reference, designation=designation, client=client, notes=notes)
            for reference, designation, client, notes in donnees.PRODUITS
        }
        fabrications = {}
        for reference, code_machine, cadence, codes_outils, notes in donnees.FABRICATIONS:
            fabrication = ProduitMachine.objects.create(
                produit=produits[reference], machine=machines[code_machine], cadence=cadence, notes=notes
            )
            fabrication.outils.set([outils[code] for code in codes_outils])
            fabrications[(reference, code_machine)] = fabrication
        for reference, code_machine, reference_article, quantite in donnees.CONSOMMATIONS:
            Consommation.objects.create(
                fabrication=fabrications[(reference, code_machine)], article=articles[reference_article],
                quantite=quantite,
            )
        for ordre, (reference, code_machine, libelle, valeur, unite) in enumerate(donnees.PARAMETRES):
            Parametre.objects.create(fabrication=fabrications[(reference, code_machine)], libelle=libelle,
                                     valeur=valeur, unite=unite, ordre=ordre)
        for reference, code_machine, etat in donnees.ETATS_MATRICE:
            ProduitMachine.objects.create(produit=produits[reference], machine=machines[code_machine], etat=etat)
        tailles = dict(donnees.TAILLES)
        for reference, code_machine, titre, nom_fichier, nature in donnees.DOCUMENTS:
            produit = produits[reference]
            if nature == "plan":
                contenu = fichiers.plan_pdf(reference, produit.designation, tailles.get(reference, "M"))
            else:
                contenu = fichiers.photo_reglage_svg(reference, code_machine, a_bandes=code_machine.startswith("MAD"))
            document = Document(produit=produit, fabrication=fabrications.get((reference, code_machine)), titre=titre)
            document.fichier.save(nom_fichier, ContentFile(contenu), save=True)
        return produits, machines

    @staticmethod
    def creer_mouvements(articles, comptes):
        # Les stocks de demo/donnees.py sont les stocks finaux : on rejoue les mouvements
        # pour avoir un historique, puis on remet le stock prévu.
        for reference, type_mouvement, quantite, identifiant, commentaire in donnees.MOUVEMENTS:
            article = articles[reference]
            stock_final = article.stock
            mouvement = Mouvement.enregistrer(
                article, type_mouvement, Decimal(quantite), utilisateur=comptes.get(identifiant), commentaire=commentaire
            )
            Article.objects.filter(pk=article.pk).update(stock=stock_final)
            Mouvement.objects.filter(pk=mouvement.pk).update(stock_apres=stock_final)

    @staticmethod
    def creer_comptages(articles, comptes):
        # Comptages passés, pour le rapport des écarts : ils ne touchent pas aux stocks de la démo.
        maintenant = timezone.now()
        for reference, stock_theorique, quantite_comptee, compte_il_y_a_jours in donnees.COMPTAGES:
            Mouvement.objects.create(
                article=articles[reference], type=Mouvement.INVENTAIRE, quantite=quantite_comptee,
                stock_apres=quantite_comptee, ecart=quantite_comptee - stock_theorique,
                date=maintenant - timedelta(days=compte_il_y_a_jours), utilisateur=comptes["intendante"],
            )

    @staticmethod
    def creer_commandes(articles, comptes):
        # Les états et dates sont posés directement : les réceptions passées sont déjà dans les stocks de la démo.
        aujourdhui = timezone.localdate()

        def il_y_a(jours):
            return None if jours is None else aujourdhui - timedelta(days=jours)

        commandes = []
        for (nom_fournisseur, etat, creee_il_y_a, passee_il_y_a, prevue_dans, recue_il_y_a, numero_fournisseur,
             lignes, notes) in donnees.COMMANDES:
            commande = Commande.objects.create(
                fournisseur=Fournisseur.objects.get(nom=nom_fournisseur), etat=etat, numero_fournisseur=numero_fournisseur,
                date_creation=il_y_a(creee_il_y_a), date_passage=il_y_a(passee_il_y_a),
                date_prevue=None if prevue_dans is None else aujourdhui + timedelta(days=prevue_dans),
                date_reception=il_y_a(recue_il_y_a),
                date_entree_stock=il_y_a(recue_il_y_a) if etat == Commande.RECEPTIONNEE else None,
                notes=notes, cree_par=comptes["methode"],
            )
            for reference, quantite, quantite_recue in lignes:
                LigneCommande.objects.create(
                    commande=commande, article=articles[reference], quantite=Decimal(quantite),
                    quantite_recue=None if quantite_recue is None else Decimal(quantite_recue),
                )
            commandes.append(commande)
        return commandes

    @staticmethod
    def creer_remontees(articles, produits, machines, comptes):
        # Les saisies passées ne font pas de sortie de stock : les stocks de la démo restent ceux de donnees.py.
        # Règles à leurs valeurs d'origine (RegleMeule vide) et thèmes d'origine.
        ThemeProbleme.objects.bulk_create([ThemeProbleme(libelle=libelle, ordre=ordre)
                                           for ordre, libelle in enumerate(regles.THEMES_D_ORIGINE)])
        matricules = [Matricule.objects.create(numero=numero, nom=nom) for numero, nom in donnees.MATRICULES]
        formats = {}
        for reference, matiere, code_lame, ma5, meules, codes_machines in donnees.FORMATS_MEULE:
            ligne = FormatMatiere.objects.create(produit=produits[reference], matiere=matiere, code_lame=code_lame, ma5=ma5)
            ligne.meules.set([articles[meule] for meule in meules])
            ligne.machines.set([machines[code] for code in codes_machines])
            formats[(reference, matiere)] = ligne
        alea = random.Random(2026)
        aujourdhui = timezone.localdate()

        def a_heure(jour, heure):
            return timezone.make_aware(datetime.combine(jour, time(heure)))

        saisies = []
        for valeurs in donnees.saisies_meules_historique(alea):
            date_montage = aujourdhui - timedelta(days=valeurs["monte_il_y_a"])
            hauteur_finale = Decimal(str(valeurs["hauteur_finale"]))
            saisies.append(SaisieMeule(
                machine=machines[valeurs["machine"]], format_matiere=formats[(valeurs["produit"], valeurs["matiere"])],
                face=valeurs["face"], meule=articles[valeurs["meule"]], lot_fournisseur=f"FA{alea.randint(100000, 999999)}",
                date_montage=date_montage, ma5=formats[(valeurs["produit"], valeurs["matiere"])].ma5 == FormatMatiere.MA5_OUI,
                pression_arrosage=valeurs["pression"], vitesse_rotation=valeurs["vitesse_rotation"],
                vitesse_avance=valeurs["vitesse_avance"], hauteur_initiale=Decimal(str(valeurs["hauteur_initiale"])),
                compteur_debut=0, matricule_monteur=alea.choice(matricules), monte_par=comptes["regleur"],
                monte_le=a_heure(date_montage, 6), matricule_demonteur=alea.choice(matricules),
                compteur_fin=valeurs["compteur_fin"], hauteur_finale=hauteur_finale, probleme=valeurs["probleme"],
                themes=valeurs["themes"], commentaire=valeurs["commentaire"], demonte_par=comptes["operateur"],
                demonte_le=a_heure(date_montage + timedelta(days=valeurs["duree_jours"]), 14),
                non_finie=regles.demontee_avant_usure(hauteur_finale),
                defaut=regles.est_un_defaut(valeurs["probleme"], valeurs["themes"], hauteur_finale),
            ))
        for code_machine, reference, matiere, face, il_y_a in donnees.MEULES_MONTEES:
            format_matiere = formats[(reference, matiere)]
            date_montage = aujourdhui - timedelta(days=il_y_a)
            vitesse_meule, avance = (int(valeur) for valeur in donnees._PARAMETRES_PAR_TAILLE[donnees.TAILLES[reference]][:2])
            saisies.append(SaisieMeule(
                machine=machines[code_machine], format_matiere=format_matiere, face=face,
                meule=format_matiere.meules.first(), lot_fournisseur=f"FA{alea.randint(100000, 999999)}",
                date_montage=date_montage, ma5=format_matiere.ma5 == FormatMatiere.MA5_OUI, pression_arrosage=6,
                vitesse_rotation=vitesse_meule, vitesse_avance=avance, hauteur_initiale=Decimal("104"), compteur_debut=0,
                matricule_monteur=alea.choice(matricules), monte_par=comptes["regleur"], monte_le=a_heure(date_montage, 6),
            ))
        return SaisieMeule.objects.bulk_create(saisies)
