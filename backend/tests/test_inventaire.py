"""Règles de gestion du stock : seuils, quantités à commander, inventaires tournants, mouvements."""
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from inventaire.models import Mouvement
from inventaire.views import articles_a_compter, lire_quantite, regrouper_par_fournisseur_prefere

from .fabriques import creer_article, creer_type_inventaire, creer_utilisateur, lier_fournisseur


class SeuilDeCommandeTests(TestCase):
    def test_article_au_dessus_du_mini_n_est_pas_a_commander(self):
        article = creer_article(stock=6, stock_mini=5)
        self.assertFalse(article.a_commander)
        self.assertEqual(article.quantite_a_commander, 0)

    def test_article_exactement_au_mini_est_a_commander(self):
        article = creer_article(stock=5, stock_mini=5, mini_commande=10)
        self.assertTrue(article.a_commander)

    def test_quantite_suggeree_remonte_le_stock_au_mini_plus_le_mini_de_commande(self):
        article = creer_article(stock=2, stock_mini=10, mini_commande=20)
        self.assertEqual(article.quantite_a_commander, Decimal("28"))

    def test_quantite_suggeree_jamais_sous_le_mini_de_commande(self):
        article = creer_article(stock=5, stock_mini=5, mini_commande=12)
        self.assertEqual(article.quantite_a_commander, Decimal("12"))

    def test_stock_negatif_est_compense(self):
        article = creer_article(stock=-3, stock_mini=4, mini_commande=4)
        self.assertEqual(article.quantite_a_commander, Decimal("11"))


class InventaireTournantTests(TestCase):
    def test_article_jamais_compte_est_a_compter(self):
        article = creer_article(inventorie_il_y_a_jours=None)
        self.assertIsNone(article.prochain_inventaire)
        self.assertTrue(article.inventaire_du)

    def test_prochain_inventaire_ajoute_la_frequence_au_dernier_comptage(self):
        article = creer_article(frequence_inventaire=30, inventorie_il_y_a_jours=10)
        self.assertEqual(article.prochain_inventaire, timezone.localdate() + timedelta(days=20))
        self.assertFalse(article.inventaire_du)

    def test_inventaire_du_le_jour_de_l_echeance(self):
        article = creer_article(frequence_inventaire=30, inventorie_il_y_a_jours=30)
        self.assertTrue(article.inventaire_du)

    def test_liste_de_comptage_par_defaut_ne_garde_que_les_articles_dus(self):
        magasin = creer_type_inventaire("Magasin")
        creer_article("DU", type_inventaire=magasin, frequence_inventaire=30, inventorie_il_y_a_jours=40)
        creer_article("A-JOUR", type_inventaire=magasin, frequence_inventaire=30, inventorie_il_y_a_jours=5)
        creer_article("AUTRE-TYPE", type_inventaire=creer_type_inventaire("Huiles"), inventorie_il_y_a_jours=None)
        self.assertEqual([a.reference for a in articles_a_compter(magasin)], ["DU"])
        self.assertEqual([a.reference for a in articles_a_compter(magasin, tous_les_articles=True)], ["A-JOUR", "DU"])

    def test_liste_de_comptage_rangee_par_emplacement(self):
        magasin = creer_type_inventaire()
        creer_article("Z", type_inventaire=magasin, emplacement="A1", inventorie_il_y_a_jours=None)
        creer_article("A", type_inventaire=magasin, emplacement="B2", inventorie_il_y_a_jours=None)
        self.assertEqual([a.reference for a in articles_a_compter(magasin)], ["Z", "A"])


class MouvementTests(TestCase):
    def setUp(self):
        self.regleur = creer_utilisateur("regleur")
        self.article = creer_article(stock=10, frequence_inventaire=30, inventorie_il_y_a_jours=60)

    def test_sortie_diminue_le_stock_et_garde_la_trace(self):
        mouvement = Mouvement.enregistrer(self.article, Mouvement.SORTIE, Decimal("3"), utilisateur=self.regleur,
                                          commentaire="Changement d'outil")
        self.article.refresh_from_db()
        self.assertEqual(self.article.stock, Decimal("7"))
        self.assertEqual(mouvement.stock_apres, Decimal("7"))
        self.assertEqual(mouvement.utilisateur, self.regleur)
        self.assertEqual(mouvement.commentaire, "Changement d'outil")

    def test_entree_augmente_le_stock(self):
        Mouvement.enregistrer(self.article, Mouvement.ENTREE, Decimal("5"))
        self.article.refresh_from_db()
        self.assertEqual(self.article.stock, Decimal("15"))

    def test_comptage_remplace_le_stock_et_date_l_inventaire(self):
        Mouvement.enregistrer(self.article, Mouvement.INVENTAIRE, Decimal("8"))
        self.article.refresh_from_db()
        self.assertEqual(self.article.stock, Decimal("8"))
        self.assertEqual(self.article.dernier_inventaire, timezone.localdate())
        self.assertFalse(self.article.inventaire_du)

    def test_sortie_ne_change_pas_la_date_d_inventaire(self):
        date_avant = self.article.dernier_inventaire
        Mouvement.enregistrer(self.article, Mouvement.SORTIE, Decimal("1"))
        self.article.refresh_from_db()
        self.assertEqual(self.article.dernier_inventaire, date_avant)

    def test_historique_du_plus_recent_au_plus_ancien(self):
        premier = Mouvement.enregistrer(self.article, Mouvement.SORTIE, Decimal("1"))
        second = Mouvement.enregistrer(self.article, Mouvement.SORTIE, Decimal("1"))
        second.date = premier.date + timedelta(minutes=1)
        second.save()
        self.assertEqual(list(self.article.mouvements.all()), [second, premier])


class FournisseurTests(TestCase):
    def test_fournisseur_prefere(self):
        article = creer_article()
        lier_fournisseur(article, "Usinage Martin")
        lier_fournisseur(article, "Mécanique Sud", prefere=True)
        self.assertEqual(article.fournisseur_prefere.nom, "Mécanique Sud")

    def test_sans_fournisseur_prefere(self):
        article = creer_article()
        lier_fournisseur(article, "Usinage Martin")
        self.assertIsNone(article.fournisseur_prefere)

    def test_un_seul_fournisseur_prefere_par_article(self):
        article = creer_article()
        lier_fournisseur(article, "Usinage Martin", prefere=True)
        with self.assertRaises(IntegrityError):
            lier_fournisseur(article, "Mécanique Sud", prefere=True)

    def test_regroupement_des_commandes_par_fournisseur_prefere(self):
        patin = creer_article("PATIN")
        tige = creer_article("TIGE")
        huile = creer_article("HUILE")
        lien_patin = lier_fournisseur(patin, "Usinage Martin", prefere=True)
        lier_fournisseur(tige, "Abrasifs", prefere=True)
        lier_fournisseur(tige, "Usinage Martin")
        commandes = regrouper_par_fournisseur_prefere([patin, tige, huile])
        self.assertEqual([fournisseur.nom if fournisseur else None for fournisseur, _ in commandes],
                         ["Abrasifs", "Usinage Martin", None])
        self.assertEqual(commandes[1][1], [(patin, lien_patin)])
        self.assertEqual(commandes[2][1], [(huile, None)])


class LectureQuantiteTests(TestCase):
    def test_virgule_et_point_acceptes(self):
        self.assertEqual(lire_quantite("3,5"), Decimal("3.5"))
        self.assertEqual(lire_quantite(" 12 "), Decimal("12"))

    def test_saisie_vide(self):
        self.assertIsNone(lire_quantite("  "))

    def test_saisie_illisible(self):
        with self.assertRaises(ValueError):
            lire_quantite("douze")
