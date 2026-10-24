"""Mode d'emploi : pages d'aide, bouton « ? », petits « i » et export statique."""
import re
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import get_resolver

from aide.sujets import SUJET_DE_LA_PAGE, SUJETS

SORTIE_MUETTE = open("/dev/null", "w")
# {% info "stock" "stock-mini" "…" %} et {% include "_champ.html" … aide_sujet="stock" aide_ancre="stock-mini" %}
PETIT_I = re.compile(r'{% info "([\w-]+)" "([\w-]+)"')
PETIT_I_DE_CHAMP = re.compile(r'aide_sujet="([\w-]+)" aide_ancre="([\w-]+)"')


def petits_i_des_gabarits():
    """Ensemble de (fichier, sujet, ancre) pour chaque petit « i » écrit dans les gabarits."""
    trouves = set()
    for gabarit in Path(settings.FRONTEND_DIR, "templates").rglob("*.html"):
        texte = gabarit.read_text(encoding="utf-8")
        for sujet, ancre in PETIT_I.findall(texte) + PETIT_I_DE_CHAMP.findall(texte):
            trouves.add((gabarit.name, sujet, ancre))
    return trouves


class ModeEmploiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("charger_demo", stdout=SORTIE_MUETTE)

    def setUp(self):
        self.client.login(username="methode", password="demo")

    def test_sommaire_et_toutes_les_pages_d_aide_repondent(self):
        reponse = self.client.get("/aide/")
        for sujet in SUJETS:
            self.assertContains(reponse, f'href="/aide/{sujet.code}/"')
            self.assertEqual(self.client.get(f"/aide/{sujet.code}/").status_code, 200, sujet.code)
        self.assertEqual(self.client.get("/aide/inconnu/").status_code, 404)

    def test_chaque_petit_i_mene_a_une_explication_existante(self):
        petits_i = petits_i_des_gabarits()
        self.assertGreater(len(petits_i), 40)
        pages = {sujet.code: self.client.get(f"/aide/{sujet.code}/").content.decode() for sujet in SUJETS}
        for fichier, sujet, ancre in petits_i:
            self.assertIn(sujet, pages, f"{fichier} : sujet {sujet} inconnu")
            self.assertIn(f'id="{ancre}"', pages[sujet], f"{fichier} : ancre {ancre} absente de l'aide « {sujet} »")

    def test_les_pages_associees_a_un_sujet_existent(self):
        noms_des_pages = {nom for nom in get_resolver().reverse_dict if isinstance(nom, str)}
        self.assertFalse(set(SUJET_DE_LA_PAGE) - noms_des_pages)

    def test_bouton_aide_ouvre_le_sujet_de_la_page(self):
        self.assertContains(self.client.get("/articles/"), 'class="bouton-aide" href="/aide/stock/"')
        self.assertContains(self.client.get("/"), 'class="bouton-aide" href="/aide/"')

    def test_petit_i_dans_une_page(self):
        reponse = self.client.get("/articles/")
        self.assertContains(reponse, 'href="/aide/stock/#colonnes"')
        self.assertContains(reponse, "data-info")

    def test_droit_requis_selon_le_profil_du_lecteur(self):
        self.client.login(username="intendante", password="demo")
        self.assertContains(self.client.get("/aide/inventaires/"), "votre profil l'a")
        self.client.login(username="operateur", password="demo")
        reponse = self.client.get("/aide/inventaires/")
        self.assertContains(reponse, "Saisir les comptages d&#x27;inventaire")
        self.assertContains(reponse, "pas avec votre profil")

    def test_export_statique_garde_les_ancres(self):
        with tempfile.TemporaryDirectory() as dossier:
            call_command("exporter_statique", sortie=dossier, stdout=SORTIE_MUETTE)
            racine = Path(dossier)
            self.assertTrue((racine / "operateur" / "aide" / "stock" / "index.html").exists())
            liste_du_stock = (racine / "operateur" / "articles" / "index.html").read_text()
            self.assertIn('href="../aide/stock/index.html#colonnes"', liste_du_stock)
            self.assertIn('href="admin/aide/index.html"', (racine / "index.html").read_text())
