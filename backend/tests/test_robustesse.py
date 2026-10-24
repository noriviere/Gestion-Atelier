"""Points relevés par la revue de code : sécurité, saisies inattendues et garde-fous sur le stock."""
from decimal import Decimal

from unittest import mock

from django.contrib.admin.sites import site as administration
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase
from django.urls import URLResolver, get_resolver

from commandes.models import Commande, LigneCommande
from comptes import roles
from comptes.droits import PAGES, PAGES_SANS_DROIT_UNIQUE
from inventaire import excel
from inventaire.models import Article, Fournisseur, Mouvement
from inventaire.recherche import rechercher
from inventaire.views import lire_quantite
from produits.models import Document, Machine, Produit

from .fabriques import creer_article, creer_utilisateur
from .test_excel import classeur, ligne_patin


def noms_des_pages(motifs):
    for motif in motifs:
        if isinstance(motif, URLResolver):
            if motif.namespace != "admin":
                yield from noms_des_pages(motif.url_patterns)
        elif motif.name:
            yield motif.name


class ControleDesPagesTests(TestCase):
    def test_chaque_page_a_son_droit_ou_est_declaree_sans_droit_unique(self):
        oubliees = set(noms_des_pages(get_resolver().url_patterns)) - set(PAGES) - PAGES_SANS_DROIT_UNIQUE
        self.assertEqual(oubliees, set(), "Ajouter ces pages à droits.PAGES (ou à PAGES_SANS_DROIT_UNIQUE).")

    def test_la_recherche_ne_montre_que_ce_que_le_profil_peut_ouvrir(self):
        creer_article("PL-9")
        Machine.objects.create(code="S1", nom="Meule S1")
        roles.enregistrer_droits({Group.objects.get(name=roles.OPERATEUR): {"produits_consulter"}})
        operateur = creer_utilisateur("operateur", roles.OPERATEUR)
        self.assertEqual([nom for nom, _ in rechercher("", roles.droits(operateur))], ["Machines"])
        self.client.force_login(operateur)
        self.assertNotContains(self.client.get("/recherche/", {"q": "PL-9"}), "PL-9</")

    def test_retour_a_la_connexion_garde_l_adresse_complete(self):
        reponse = self.client.get("/articles/", {"categorie": "usure", "q": "a&b"})
        self.assertEqual(reponse.url, "/connexion/?next=/articles/%3Fcategorie%3Dusure%26q%3Da%2526b")


class DocumentsTests(TestCase):
    def setUp(self):
        self.produit = Produit.objects.create(reference="N2", designation="Produit N2")
        self.client.force_login(creer_utilisateur("regleur", roles.REGLEUR))

    def test_un_svg_ouvert_seul_ne_peut_pas_executer_de_script(self):
        photo = Document.objects.create(produit=self.produit, titre="Réglage",
                                        fichier=ContentFile(b"<svg><script>alert(1)</script></svg>", name="r.svg"))
        reponse = self.client.get(photo.get_absolute_url())
        self.assertIn("sandbox", reponse["Content-Security-Policy"])

    def test_retour_apres_suppression_reste_sur_le_site(self):
        plan = Document.objects.create(produit=self.produit, titre="Plan", fichier=ContentFile(b"%PDF", name="p.pdf"))
        reponse = self.client.post(f"/produits/documents/{plan.pk}/supprimer/", {"retour": "//autre-site.example/"})
        self.assertRedirects(reponse, "/produits/", fetch_redirect_response=False)


class SaisiesInattenduesTests(TestCase):
    def test_quantites_refusees(self):
        for saisie in ("NaN", "Infinity", "-3", "1e30", "123456789"):
            with self.subTest(saisie=saisie), self.assertRaises(ValueError):
                lire_quantite(saisie)

    def test_comptage_negatif_ne_change_pas_le_stock(self):
        article = creer_article("PL-9", stock=7)
        self.client.force_login(creer_utilisateur("intendante", roles.INTENDANT))
        self.client.post(f"/inventaires/{article.type_inventaire_id}/", {f"compte_{article.pk}": "NaN"})
        article.refresh_from_db()
        self.assertEqual(article.stock, Decimal("7"))

    def test_reception_avec_nan_refusee_sans_erreur_serveur(self):
        article = creer_article("PL-9")
        commande = Commande.objects.create(fournisseur=Fournisseur.objects.create(nom="A"), etat=Commande.PASSEE)
        ligne = LigneCommande.objects.create(commande=commande, article=article, quantite=4)
        self.client.force_login(creer_utilisateur("intendante", roles.INTENDANT))
        reponse = self.client.post(commande.get_absolute_url(), {"action": Commande.RECEPTIONNEE, f"recu_{ligne.pk}": "NaN"})
        self.assertEqual(reponse.status_code, 302)
        commande.refresh_from_db()
        self.assertEqual(commande.etat, Commande.PASSEE)

    def test_identifiants_illisibles_dans_l_adresse(self):
        self.client.force_login(creer_utilisateur("methode", roles.METHODE))
        produit = Produit.objects.create(reference="N2", designation="Produit N2")
        self.assertEqual(self.client.get("/articles/", {"type": "abc"}).status_code, 200)
        self.assertEqual(self.client.get("/outils/nouveau/", {"parent": "abc"}).status_code, 200)
        self.assertEqual(self.client.get(f"/produits/{produit.pk}/fiche/nouvelle/", {"machine": "999"}).status_code, 404)
        self.assertEqual(self.client.post("/produits/etat/", {"produit": "abc", "machine": "1", "etat": ""}).status_code, 404)

    def test_import_texte_trop_long_signale_avant_enregistrement(self):
        ligne, = excel.analyser_import(excel.lire_classeur(classeur(ligne_patin(**{"Référence": "R" * 41}))))
        self.assertEqual(ligne.action, "erreur")
        self.assertIn("Référence trop long : 41 caractères pour 40 au plus.", ligne.erreurs)


class StockProtegeTests(TestCase):
    def test_reception_rejouee_n_entre_qu_une_fois_en_stock(self):
        article = creer_article("PL-9", stock=2)
        commande = Commande.objects.create(fournisseur=Fournisseur.objects.create(nom="A"), etat=Commande.PASSEE)
        LigneCommande.objects.create(commande=commande, article=article, quantite=4)
        # Deux requêtes chargent la commande avant que l'une d'elles ne la réceptionne.
        premiere, seconde = Commande.objects.get(pk=commande.pk), Commande.objects.get(pk=commande.pk)
        premiere.receptionner({})
        with self.assertRaises(ValueError):
            seconde.receptionner({})
        article.refresh_from_db()
        self.assertEqual(article.stock, Decimal("6"))

    def test_modifier_un_article_ne_reecrit_pas_le_stock(self):
        article = creer_article("PL-9", stock=7)
        self.client.force_login(creer_utilisateur("methode", roles.METHODE))
        donnees = {"reference": "PL-9", "designation": "Renommé", "categorie": "usure", "origine": "achat",
                   "numero_plan": "", "type_inventaire": article.type_inventaire_id, "emplacement": "", "unite": "pièce",
                   "stock_mini": "2", "mini_commande": "4", "frequence_inventaire": "90",
                   "liens_fournisseurs-TOTAL_FORMS": "0", "liens_fournisseurs-INITIAL_FORMS": "0"}
        with mock.patch.object(Article, "save", autospec=True, side_effect=Article.save) as enregistrement:
            self.client.post(f"/articles/{article.pk}/modifier/", donnees)
        champs_ecrits = enregistrement.call_args.kwargs["update_fields"]
        self.assertIn("designation", champs_ecrits)
        self.assertNotIn("stock", champs_ecrits)

    def test_l_administration_ne_modifie_ni_le_stock_ni_les_mouvements(self):
        requete = RequestFactory().get("/admin/")
        requete.user = creer_utilisateur("admin", superutilisateur=True)
        self.assertIn("stock", administration._registry[Article].get_readonly_fields(requete))
        administration_mouvements = administration._registry[Mouvement]
        self.assertFalse(administration_mouvements.has_add_permission(requete))
        self.assertFalse(administration_mouvements.has_change_permission(requete))

    def test_commande_passee_figee_dans_l_administration(self):
        requete = RequestFactory().get("/admin/")
        requete.user = creer_utilisateur("admin", superutilisateur=True)
        commande = Commande.objects.create(fournisseur=Fournisseur.objects.create(nom="A"), etat=Commande.PASSEE)
        administration_commandes = administration._registry[Commande]
        self.assertIn("etat", administration_commandes.get_readonly_fields(requete, commande))
        lignes = administration_commandes.inlines[0](Commande, administration)
        self.assertFalse(lignes.has_change_permission(requete, commande))
        self.assertFalse(lignes.has_delete_permission(requete, commande))

    def test_charger_demo_refuse_d_effacer_sans_confirmation_hors_debug(self):
        with self.assertRaises(CommandError):
            call_command("charger_demo")
        self.assertFalse(Machine.objects.exists())
