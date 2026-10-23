from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from inventaire.models import Article, Mouvement


class DemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("charger_demo", stdout=open("/dev/null", "w"))

    def test_seuil_et_quantite_a_commander(self):
        art = Article.objects.get(reference="PAT-M")  # stock 6, mini 10, mini commande 20
        self.assertTrue(art.a_commander)
        self.assertEqual(art.quantite_a_commander, Decimal("24"))
        self.assertFalse(Article.objects.get(reference="PAT-P").a_commander)

    def test_mouvements_mettent_a_jour_le_stock(self):
        art = Article.objects.get(reference="PAT-P")
        Mouvement.enregistrer(art, Mouvement.SORTIE, Decimal("2"))
        art.refresh_from_db()
        self.assertEqual(art.stock, Decimal("12"))
        Mouvement.enregistrer(art, Mouvement.INVENTAIRE, Decimal("7"))
        art.refresh_from_db()
        self.assertEqual(art.stock, Decimal("7"))
        self.assertFalse(art.inventaire_du)

    def test_toutes_les_pages_repondent(self):
        self.client.login(username="operateur", password="demo")
        for url in ["/", "/articles/", "/articles/1/", "/a-commander/", "/inventaires/", "/inventaires/1/",
                    "/inventaires/1/feuille/", "/outils/", "/outils/1/", "/produits/", "/produits/1/",
                    "/produits/fiche/1/", "/produits/machines/", "/produits/machines/1/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_connexion_obligatoire(self):
        self.assertRedirects(self.client.get("/articles/"), "/connexion/?next=/articles/")

    def test_operateur_saisit_une_sortie_mais_ne_parametre_pas(self):
        self.client.login(username="operateur", password="demo")
        art = Article.objects.get(reference="PAT-P")
        self.client.post(f"/articles/{art.pk}/", {"type": "sortie", "quantite": "1"})
        art.refresh_from_db()
        self.assertEqual(art.stock, Decimal("13"))
        self.assertNotContains(self.client.get("/"), "Paramétrage")
        self.assertEqual(self.client.get("/admin/inventaire/article/").status_code, 302)

    def test_methode_parametre_via_l_admin(self):
        self.client.login(username="methode", password="demo")
        self.assertContains(self.client.get("/"), "Paramétrage")
        self.assertEqual(self.client.get("/admin/inventaire/article/add/").status_code, 200)

    def test_comptage_inventaire(self):
        self.client.login(username="intendante", password="demo")
        art = Article.objects.get(reference="PL-M")  # dernier inventaire il y a 200 j, fréquence 180 j
        self.assertTrue(art.inventaire_du)
        self.client.post(f"/inventaires/{art.type_inventaire_id}/", {f"compte_{art.pk}": "5"})
        art.refresh_from_db()
        self.assertEqual(art.stock, Decimal("5"))
        self.assertFalse(art.inventaire_du)

    def test_export_statique(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as dossier:
            call_command("exporter_statique", sortie=dossier, stdout=open("/dev/null", "w"))
            racine = Path(dossier)
            self.assertTrue((racine / "index.html").exists())
            accueil = (racine / "operateur" / "index.html").read_text()
            self.assertNotIn("Paramétrage", accueil)
            self.assertIn('href="../static/atelier.css"', accueil)
            self.assertIn("Paramétrage", (racine / "methode" / "index.html").read_text())
