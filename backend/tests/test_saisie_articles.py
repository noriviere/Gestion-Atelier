"""Création et modification des articles et des fournisseurs depuis l'application."""
from decimal import Decimal

from django.test import TestCase

from comptes import roles
from inventaire.models import Article, Fournisseur

from .fabriques import creer_article, creer_type_inventaire, creer_utilisateur, lier_fournisseur


def donnees_article(type_inventaire, **champs):
    donnees = {
        "reference": "PL-9", "designation": "Porte-lame N9", "categorie": "usure", "origine": "achat", "numero_plan": "",
        "type_inventaire": type_inventaire.pk, "emplacement": "A2-09", "unite": "pièce", "stock_mini": "2",
        "mini_commande": "4", "frequence_inventaire": "90", "stock_initial": "",
        "liens_fournisseurs-TOTAL_FORMS": "0", "liens_fournisseurs-INITIAL_FORMS": "0",
    }
    donnees.update(champs)
    return donnees


def lignes_fournisseurs(*lignes, deja_enregistrees=0):
    """Données du tableau des fournisseurs : une ligne par dictionnaire."""
    donnees = {"liens_fournisseurs-TOTAL_FORMS": str(len(lignes)),
               "liens_fournisseurs-INITIAL_FORMS": str(deja_enregistrees)}
    for position, ligne in enumerate(lignes):
        for champ, valeur in ligne.items():
            donnees[f"liens_fournisseurs-{position}-{champ}"] = valeur
    return donnees


class SaisieArticleTests(TestCase):
    def setUp(self):
        self.type_inventaire = creer_type_inventaire()
        self.client.force_login(creer_utilisateur("methode", roles.METHODE))

    def test_creation_avec_stock_initial_et_fournisseur(self):
        usinage = Fournisseur.objects.create(nom="Usinage Martin")
        reponse = self.client.post("/articles/nouveau/", donnees_article(
            self.type_inventaire, stock_initial="6",
            **lignes_fournisseurs({"fournisseur": usinage.pk, "prix": "145", "delai": "15", "prefere": "on"}),
        ))
        article = Article.objects.get(reference="PL-9")
        self.assertRedirects(reponse, f"/articles/{article.pk}/")
        self.assertEqual(article.stock, Decimal("6"))
        self.assertEqual(article.mouvements.get().commentaire, "Stock initial")
        self.assertEqual(article.fournisseur_prefere, usinage)

    def test_design_interne_demande_le_numero_de_plan(self):
        reponse = self.client.post("/articles/nouveau/", donnees_article(self.type_inventaire, origine="interne"))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn("numero_plan", reponse.context["form"].errors)
        self.assertFalse(Article.objects.exists())

    def test_design_interne_avec_son_plan(self):
        self.client.post("/articles/nouveau/", donnees_article(self.type_inventaire, origine="interne",
                                                               numero_plan="PL-1109 ind. A"))
        self.assertTrue(Article.objects.get(reference="PL-9").est_design_interne)

    def test_deux_fournisseurs_preferes_refuses(self):
        premier = Fournisseur.objects.create(nom="Usinage Martin")
        second = Fournisseur.objects.create(nom="Mécanique Sud")
        reponse = self.client.post("/articles/nouveau/", donnees_article(self.type_inventaire, **lignes_fournisseurs(
            {"fournisseur": premier.pk, "prefere": "on"}, {"fournisseur": second.pk, "prefere": "on"},
        )))
        self.assertContains(reponse, "Un seul fournisseur peut être le fournisseur préféré.")
        self.assertFalse(Article.objects.exists())

    def test_changer_de_fournisseur_prefere(self):
        article = creer_article("PL-9", type_inventaire=self.type_inventaire)
        ancien = lier_fournisseur(article, "Usinage Martin", prefere=True)
        nouveau = lier_fournisseur(article, "Mécanique Sud")
        reponse = self.client.post(f"/articles/{article.pk}/modifier/", donnees_article(
            self.type_inventaire, **lignes_fournisseurs(
                {"id": ancien.pk, "fournisseur": ancien.fournisseur_id},
                {"id": nouveau.pk, "fournisseur": nouveau.fournisseur_id, "prefere": "on"},
                deja_enregistrees=2,
            ),
        ))
        self.assertRedirects(reponse, f"/articles/{article.pk}/")
        self.assertEqual(article.fournisseur_prefere.nom, "Mécanique Sud")

    def test_modification_ne_touche_pas_au_stock(self):
        article = creer_article("PL-9", stock=7, type_inventaire=self.type_inventaire)
        self.assertNotIn("stock_initial", self.client.get(f"/articles/{article.pk}/modifier/").context["form"].fields)
        self.client.post(f"/articles/{article.pk}/modifier/", donnees_article(self.type_inventaire, designation="Renommé",
                                                                              stock_initial="50"))
        article.refresh_from_db()
        self.assertEqual(article.designation, "Renommé")
        self.assertEqual(article.stock, Decimal("7"))

    def test_retirer_un_fournisseur(self):
        article = creer_article("PL-9", type_inventaire=self.type_inventaire)
        lien = lier_fournisseur(article, "Usinage Martin")
        self.client.post(f"/articles/{article.pk}/modifier/", donnees_article(self.type_inventaire, **lignes_fournisseurs(
            {"id": lien.pk, "fournisseur": lien.fournisseur_id, "DELETE": "on"}, deja_enregistrees=1,
        )))
        self.assertFalse(article.liens_fournisseurs.exists())


class DroitsDeSaisieTests(TestCase):
    def test_atelier_et_intendant_ne_modifient_pas_les_articles(self):
        article = creer_article()
        for identifiant, profil in (("operateur", roles.ATELIER), ("intendante", roles.INTENDANT)):
            self.client.force_login(creer_utilisateur(identifiant, profil))
            self.assertEqual(self.client.get("/articles/nouveau/").status_code, 403)
            self.assertEqual(self.client.get(f"/articles/{article.pk}/modifier/").status_code, 403)
            self.assertEqual(self.client.get("/fournisseurs/nouveau/").status_code, 403)
            self.assertEqual(self.client.get("/fournisseurs/").status_code, 200)


class SaisieFournisseurTests(TestCase):
    def setUp(self):
        self.client.force_login(creer_utilisateur("methode", roles.METHODE))

    def test_creation_puis_modification(self):
        self.client.post("/fournisseurs/nouveau/", {"nom": "Rectif Est", "contact": "M. Durand", "telephone": "",
                                                    "email": "contact@rectif-est.fr"})
        fournisseur = Fournisseur.objects.get(nom="Rectif Est")
        self.client.post(f"/fournisseurs/{fournisseur.pk}/modifier/", {"nom": "Rectif Est", "contact": "Mme Roux",
                                                                       "telephone": "04 00 00 00 09", "email": ""})
        fournisseur.refresh_from_db()
        self.assertEqual(fournisseur.contact, "Mme Roux")

    def test_nom_en_double_refuse(self):
        Fournisseur.objects.create(nom="Rectif Est")
        reponse = self.client.post("/fournisseurs/nouveau/", {"nom": "Rectif Est"})
        self.assertIn("nom", reponse.context["form"].errors)

    def test_fiche_fournisseur_liste_ses_articles(self):
        article = creer_article("PAT-P")
        lien = lier_fournisseur(article, "Usinage Martin", prefere=True)
        reponse = self.client.get(f"/fournisseurs/{lien.fournisseur_id}/")
        self.assertContains(reponse, "PAT-P")
        self.assertContains(reponse, "préféré")
