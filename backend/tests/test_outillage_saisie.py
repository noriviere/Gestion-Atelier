"""Saisie des outils et de leurs pièces par le profil méthode, sorties de pièces depuis la fiche outil."""
from decimal import Decimal

from django.test import TestCase

from comptes import roles
from inventaire.models import Mouvement
from outillage.models import Outil, PieceOutil

from .fabriques import creer_article, creer_utilisateur


def donnees_formulaire(code, nom, parent="", pieces=(), pieces_existantes=()):
    """Données POST du formulaire outil : pieces = [(article, quantité)], pieces_existantes = [(lien, quantité, retirer)]."""
    lignes = [(lien.pk, lien.article.pk, quantite, retirer) for lien, quantite, retirer in pieces_existantes]
    lignes += [("", article.pk, quantite, False) for article, quantite in pieces]
    donnees = {
        "code": code, "nom": nom, "parent": parent.pk if parent else "", "description": "",
        "liens_pieces-TOTAL_FORMS": str(len(lignes)),
        "liens_pieces-INITIAL_FORMS": str(len(pieces_existantes)),
        "liens_pieces-MIN_NUM_FORMS": "0",
        "liens_pieces-MAX_NUM_FORMS": "1000",
    }
    for position, (lien_pk, article_pk, quantite, retirer) in enumerate(lignes):
        donnees[f"liens_pieces-{position}-id"] = lien_pk
        donnees[f"liens_pieces-{position}-article"] = article_pk
        donnees[f"liens_pieces-{position}-quantite"] = quantite
        if retirer:
            donnees[f"liens_pieces-{position}-DELETE"] = "on"
    return donnees


class SaisieOutilTests(TestCase):
    def setUp(self):
        self.methodiste = creer_utilisateur("methode", roles.METHODE)
        self.operateur = creer_utilisateur("operateur", roles.ATELIER)
        self.patin = creer_article("PAT-M", stock=10)
        self.tige = creer_article("TIG-M", stock=4)
        self.jeu = Outil.objects.create(code="OUT-N7", nom="Jeu d'outils N7")
        self.chargeur = Outil.objects.create(code="OUT-N7-1", nom="Chargeur N7", parent=self.jeu)
        self.lien_patin = PieceOutil.objects.create(outil=self.chargeur, article=self.patin, quantite=2)

    def test_descendants_a_tous_les_niveaux(self):
        porte_patin = Outil.objects.create(code="OUT-N7-1-A", nom="Porte-patin", parent=self.chargeur)
        self.assertEqual(self.jeu.descendants(), [self.chargeur, porte_patin])

    def test_le_formulaire_reprend_l_outil_parent(self):
        self.client.force_login(self.methodiste)
        modification = self.client.get(f"/outils/{self.chargeur.pk}/modifier/")
        self.assertEqual(modification.context["form"]["parent"].value(), self.jeu.pk)
        creation = self.client.get("/outils/nouveau/", {"parent": self.jeu.pk})
        self.assertEqual(str(creation.context["form"]["parent"].value()), str(self.jeu.pk))

    def test_methode_cree_un_sous_ensemble_avec_ses_pieces(self):
        self.client.force_login(self.methodiste)
        reponse = self.client.post(
            "/outils/nouveau/", donnees_formulaire("OUT-N7-2", "Pince N7", self.jeu, [(self.patin, 1), (self.tige, 3)])
        )
        pince = Outil.objects.get(code="OUT-N7-2")
        self.assertRedirects(reponse, pince.get_absolute_url())
        self.assertEqual(pince.parent, self.jeu)
        self.assertEqual({lien.article.reference: lien.quantite for lien in pince.liens_pieces.all()},
                         {"PAT-M": 1, "TIG-M": 3})

    def test_methode_modifie_retire_et_ajoute_des_pieces(self):
        self.client.force_login(self.methodiste)
        self.client.post(
            f"/outils/{self.chargeur.pk}/modifier/",
            donnees_formulaire("OUT-N7-1", "Chargeur N7 révisé", self.jeu, [(self.tige, 2)],
                               pieces_existantes=[(self.lien_patin, 2, True)]),
        )
        self.chargeur.refresh_from_db()
        self.assertEqual(self.chargeur.nom, "Chargeur N7 révisé")
        self.assertEqual([lien.article for lien in self.chargeur.liens_pieces.all()], [self.tige])
        self.assertEqual(self.patin.liens_outils.count(), 0)

    def test_la_meme_piece_deux_fois_est_refusee(self):
        self.client.force_login(self.methodiste)
        reponse = self.client.post(
            "/outils/nouveau/", donnees_formulaire("OUT-X", "Outil X", pieces=[(self.patin, 1), (self.patin, 2)])
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Outil.objects.filter(code="OUT-X").exists())

    def test_un_outil_ne_peut_pas_etre_range_sous_son_sous_ensemble(self):
        self.client.force_login(self.methodiste)
        reponse = self.client.post(
            f"/outils/{self.jeu.pk}/modifier/", donnees_formulaire("OUT-N7", "Jeu d'outils N7", self.chargeur)
        )
        self.assertEqual(reponse.status_code, 200)
        self.jeu.refresh_from_db()
        self.assertIsNone(self.jeu.parent)
        self.assertNotIn(self.chargeur, reponse.context["form"].fields["parent"].queryset)

    def test_suppression_garde_les_articles_du_stock(self):
        self.client.force_login(self.methodiste)
        reponse = self.client.post(f"/outils/{self.jeu.pk}/supprimer/")
        self.assertRedirects(reponse, "/outils/")
        self.assertFalse(Outil.objects.filter(code__startswith="OUT-N7").exists())
        self.patin.refresh_from_db()
        self.assertEqual(self.patin.stock, Decimal("10"))

    def test_operateur_ne_modifie_pas_les_outils(self):
        self.client.force_login(self.operateur)
        self.assertEqual(self.client.get("/outils/nouveau/").status_code, 403)
        self.assertEqual(self.client.get(f"/outils/{self.jeu.pk}/modifier/").status_code, 403)
        self.assertEqual(self.client.post(f"/outils/{self.jeu.pk}/supprimer/").status_code, 403)
        self.assertNotContains(self.client.get(self.jeu.get_absolute_url()), "Modifier l'outil")


class SortiePieceTests(TestCase):
    def setUp(self):
        self.operateur = creer_utilisateur("operateur", roles.ATELIER)
        self.patin = creer_article("PAT-M", stock=10, stock_mini=5)
        self.jeu = Outil.objects.create(code="OUT-N7", nom="Jeu d'outils N7")
        self.chargeur = Outil.objects.create(code="OUT-N7-1", nom="Chargeur N7", parent=self.jeu)
        self.lien_patin = PieceOutil.objects.create(outil=self.chargeur, article=self.patin, quantite=2)
        self.client.force_login(self.operateur)

    def test_la_fiche_outil_propose_la_sortie_des_pieces(self):
        self.assertContains(self.client.get(self.jeu.get_absolute_url()), 'data-demo="sortie-piece"')

    def test_sortie_d_une_piece_d_un_sous_ensemble_depuis_la_fiche_de_l_outil(self):
        reponse = self.client.post(f"/outils/{self.jeu.pk}/sortie/", {"piece": self.lien_patin.pk, "quantite": "2"})
        self.assertRedirects(reponse, self.jeu.get_absolute_url())
        self.patin.refresh_from_db()
        self.assertEqual(self.patin.stock, Decimal("8"))
        mouvement = Mouvement.objects.get(article=self.patin)
        self.assertEqual((mouvement.type, mouvement.utilisateur), (Mouvement.SORTIE, self.operateur))
        self.assertEqual(mouvement.commentaire, "Remplacement sur OUT-N7-1")

    def test_quantite_nulle_refusee(self):
        self.client.post(f"/outils/{self.jeu.pk}/sortie/", {"piece": self.lien_patin.pk, "quantite": "0"})
        self.patin.refresh_from_db()
        self.assertEqual(self.patin.stock, Decimal("10"))

    def test_piece_d_un_autre_outil_refusee(self):
        autre_jeu = Outil.objects.create(code="OUT-N8", nom="Jeu d'outils N8")
        reponse = self.client.post(f"/outils/{autre_jeu.pk}/sortie/", {"piece": self.lien_patin.pk, "quantite": "1"})
        self.assertEqual(reponse.status_code, 404)
        self.assertFalse(Mouvement.objects.exists())

    def test_sortie_uniquement_en_post(self):
        self.assertEqual(self.client.get(f"/outils/{self.jeu.pk}/sortie/").status_code, 405)
