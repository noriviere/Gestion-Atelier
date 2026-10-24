"""Pages de l'application : accès selon le profil, saisies, et export statique, sur les données de démo."""
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from comptes.management.commands.exporter_statique import chemin_statique
from commandes.models import Commande
from inventaire.models import Article, TypeInventaire

SORTIE_MUETTE = open("/dev/null", "w")


class PagesDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("charger_demo", stdout=SORTIE_MUETTE)

    def test_toutes_les_pages_repondent(self):
        self.client.login(username="operateur", password="demo")
        article = Article.objects.first()
        type_inventaire = TypeInventaire.objects.first()
        for adresse in ["/", "/articles/", f"/articles/{article.pk}/", "/a-commander/", "/inventaires/",
                        f"/inventaires/{type_inventaire.pk}/", f"/inventaires/{type_inventaire.pk}/?tous=1",
                        f"/inventaires/{type_inventaire.pk}/feuille/", "/outils/", "/produits/",
                        "/produits/machines/", "/commandes/", "/commandes/?etat=&retard=1",
                        *[f"/commandes/{commande.pk}/" for commande in Commande.objects.all()]]:
            self.assertEqual(self.client.get(adresse).status_code, 200, adresse)

    def test_connexion_obligatoire(self):
        self.assertRedirects(self.client.get("/articles/"), "/connexion/?next=/articles/")

    def test_filtre_des_articles_sous_le_mini(self):
        self.client.login(username="operateur", password="demo")
        reponse = self.client.get("/articles/", {"alerte": "1"})
        self.assertTrue(all(article.a_commander for article in reponse.context["articles"]))
        self.assertGreater(len(reponse.context["articles"]), 0)

    def test_operateur_saisit_une_sortie_mais_ne_parametre_pas(self):
        self.client.login(username="operateur", password="demo")
        patin = Article.objects.get(reference="PAT-P")
        self.client.post(f"/articles/{patin.pk}/", {"type": "sortie", "quantite": "1"})
        patin.refresh_from_db()
        self.assertEqual(patin.stock, Decimal("13"))
        self.assertNotContains(self.client.get("/"), "Paramétrage")
        self.assertEqual(self.client.get("/admin/inventaire/article/").status_code, 302)

    def test_quantite_negative_refusee(self):
        self.client.login(username="operateur", password="demo")
        patin = Article.objects.get(reference="PAT-P")
        self.client.post(f"/articles/{patin.pk}/", {"type": "sortie", "quantite": "-2"})
        patin.refresh_from_db()
        self.assertEqual(patin.stock, Decimal("14"))

    def test_methode_parametre_via_l_admin(self):
        self.client.login(username="methode", password="demo")
        self.assertContains(self.client.get("/"), "Paramétrage")
        self.assertEqual(self.client.get("/admin/inventaire/article/add/").status_code, 200)

    def test_comptage_inventaire_corrige_le_stock(self):
        self.client.login(username="intendante", password="demo")
        porte_lame = Article.objects.get(reference="PL-M")
        self.assertTrue(porte_lame.inventaire_du)
        self.client.post(f"/inventaires/{porte_lame.type_inventaire_id}/",
                         {f"compte_{porte_lame.pk}": "5", f"compte_{porte_lame.pk + 1}": "illisible"})
        porte_lame.refresh_from_db()
        self.assertEqual(porte_lame.stock, Decimal("5"))
        self.assertFalse(porte_lame.inventaire_du)

    def test_operateur_ne_saisit_pas_de_comptage(self):
        self.client.login(username="operateur", password="demo")
        porte_lame = Article.objects.get(reference="PL-M")
        page = self.client.get(f"/inventaires/{porte_lame.type_inventaire_id}/")
        self.assertNotContains(page, "Enregistrer les comptages")
        reponse = self.client.post(f"/inventaires/{porte_lame.type_inventaire_id}/", {f"compte_{porte_lame.pk}": "5"})
        self.assertEqual(reponse.status_code, 403)
        porte_lame.refresh_from_db()
        self.assertEqual(porte_lame.stock, Decimal("3"))

    def test_stock_bas_avec_commande_en_cours_est_signale(self):
        self.client.login(username="operateur", password="demo")
        porte_lame = Article.objects.get(reference="PL-M")
        reponse = self.client.get(f"/articles/{porte_lame.pk}/")
        self.assertContains(reponse, "couvert par les commandes en cours")
        self.assertContains(reponse, "en retard")

    def test_a_commander_propose_de_preparer_les_commandes_restantes(self):
        self.client.login(username="methode", password="demo")
        reponse = self.client.get("/a-commander/")
        self.assertContains(reponse, "Préparer la commande Usinage Martin")
        self.assertContains(reponse, "couvert")


class ExportStatiqueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("charger_demo", stdout=SORTIE_MUETTE)

    def test_chemin_statique_des_adresses(self):
        self.assertEqual(chemin_statique("/"), "index.html")
        self.assertEqual(chemin_statique("/articles/12/"), "articles/12/index.html")
        self.assertEqual(chemin_statique("/inventaires/3/?tous=1"), "inventaires/3/tous-1/index.html")

    def test_export_un_jeu_de_pages_par_profil(self):
        with tempfile.TemporaryDirectory() as dossier:
            call_command("exporter_statique", sortie=dossier, stdout=SORTIE_MUETTE)
            racine = Path(dossier)
            self.assertTrue((racine / "index.html").exists())
            self.assertTrue((racine / "static" / "js" / "demo.js").exists())
            accueil_operateur = (racine / "operateur" / "index.html").read_text()
            self.assertNotIn("Paramétrage", accueil_operateur)
            self.assertIn('href="../static/css/atelier.css"', accueil_operateur)
            self.assertNotIn('href="/', accueil_operateur)
            self.assertIn("Paramétrage", (racine / "methode" / "index.html").read_text())
