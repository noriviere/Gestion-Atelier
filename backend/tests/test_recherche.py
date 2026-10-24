"""Recherche globale de la barre du haut."""
from django.core.management import call_command
from django.test import TestCase

from inventaire.recherche import normaliser, rechercher

SORTIE_MUETTE = open("/dev/null", "w")


def noms_des_groupes(groupes):
    return [nom_groupe for nom_groupe, _ in groupes]


def titres(groupes, nom_groupe):
    return [resultat["titre"] for nom, resultats in groupes if nom == nom_groupe for resultat in resultats]


class RechercheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("charger_demo", stdout=SORTIE_MUETTE)

    def test_normaliser_ignore_accents_et_majuscules(self):
        self.assertEqual(normaliser("Pièce d'USURE"), "piece d'usure")

    def test_recherche_vide_renvoie_tout(self):
        self.assertEqual(noms_des_groupes(rechercher("")), ["Articles", "Outils", "Produits", "Machines"])

    def test_recherche_sans_accent_trouve_un_article_accentue(self):
        self.assertIn("PL-M", titres(rechercher("porte-lame"), "Articles"))

    def test_tous_les_mots_doivent_apparaitre(self):
        self.assertEqual(titres(rechercher("s1"), "Machines"), ["S1"])
        self.assertEqual(rechercher("s1 introuvable"), [])

    def test_groupes_vides_retires(self):
        self.assertEqual(noms_des_groupes(rechercher("MAD1")), ["Machines"])

    def test_page_de_recherche(self):
        self.client.login(username="operateur", password="demo")
        reponse = self.client.get("/recherche/", {"q": "zzz"})
        self.assertContains(reponse, "Aucun résultat pour « zzz »")
        self.assertContains(self.client.get("/"), 'action="/recherche/"')
