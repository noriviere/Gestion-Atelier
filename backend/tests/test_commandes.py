"""Suivi des commandes fournisseurs : états, retards, quantités en commande, réception en stock."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from commandes.models import Commande, LigneCommande, renseigner_commandes_en_cours
from commandes.views import filtrer_commandes, trier_pour_le_suivi
from comptes.roles import ATELIER, METHODE
from inventaire.models import ArticleFournisseur, Fournisseur, Mouvement

from .fabriques import creer_article, creer_utilisateur, lier_fournisseur

AUJOURDHUI = timezone.localdate()


def creer_commande(fournisseur_nom="Fournisseur A", etat=Commande.EN_ATTENTE, lignes=(), **champs):
    fournisseur = Fournisseur.objects.get_or_create(nom=fournisseur_nom)[0]
    commande = Commande.objects.create(fournisseur=fournisseur, etat=etat, **champs)
    for article, quantite in lignes:
        LigneCommande.objects.create(commande=commande, article=article, quantite=Decimal(quantite))
    return commande


class NumerotationTests(TestCase):
    def test_numero_automatique_par_annee(self):
        premiere = creer_commande()
        seconde = creer_commande()
        self.assertEqual(premiere.numero, f"CDE-{AUJOURDHUI.year}-0001")
        self.assertEqual(seconde.numero, f"CDE-{AUJOURDHUI.year}-0002")

    def test_numero_saisi_conserve(self):
        self.assertEqual(creer_commande(numero="ABAS-123").numero, "ABAS-123")


class RetardTests(TestCase):
    def test_commande_passee_en_retard_apres_la_date_prevue(self):
        commande = creer_commande(etat=Commande.PASSEE, date_prevue=AUJOURDHUI - timedelta(days=3))
        self.assertTrue(commande.en_retard)
        self.assertEqual(commande.jours_de_retard, 3)

    def test_pas_de_retard_le_jour_prevu(self):
        commande = creer_commande(etat=Commande.PASSEE, date_prevue=AUJOURDHUI)
        self.assertFalse(commande.en_retard)
        self.assertTrue(commande.livraison_proche)

    def test_commande_recue_n_est_plus_en_retard_mais_garde_son_retard_de_livraison(self):
        commande = creer_commande(etat=Commande.RECUE, date_prevue=AUJOURDHUI - timedelta(days=5),
                                  date_reception=AUJOURDHUI - timedelta(days=1))
        self.assertFalse(commande.en_retard)
        self.assertEqual(commande.retard_a_la_livraison, 4)

    def test_delai_entre_passage_et_livraison_prevue(self):
        commande = creer_commande(date_passage=AUJOURDHUI, date_prevue=AUJOURDHUI + timedelta(days=12))
        self.assertEqual(commande.delai_jours, 12)


class QuantiteEnCommandeTests(TestCase):
    def setUp(self):
        self.article = creer_article("PAT-M", stock=6, stock_mini=10, mini_commande=20)

    def test_article_sous_le_mini_couvert_par_une_commande_en_cours(self):
        creer_commande(etat=Commande.PASSEE, lignes=[(self.article, 20)])
        self.assertEqual(self.article.quantite_en_commande, Decimal("20"))
        self.assertTrue(self.article.couvert_par_commande)
        self.assertEqual(self.article.reste_a_commander, 0)

    def test_commande_insuffisante_laisse_un_reste_a_commander(self):
        creer_commande(etat=Commande.EN_ATTENTE, lignes=[(self.article, 2)])
        self.assertFalse(self.article.couvert_par_commande)
        # stock prévisionnel 8, mini 10 : 10 - 8 + 20
        self.assertEqual(self.article.reste_a_commander, Decimal("22"))

    def test_commandes_terminees_ne_comptent_pas(self):
        creer_commande(etat=Commande.RECEPTIONNEE, lignes=[(self.article, 20)])
        creer_commande(etat=Commande.ANNULEE, lignes=[(self.article, 20)])
        self.assertEqual(self.article.quantite_en_commande, 0)
        self.assertTrue(self.article.a_commander)

    def test_renseignement_groupe_des_commandes_en_cours(self):
        autre_article = creer_article("TIG-G")
        commande = creer_commande(etat=Commande.PASSEE, lignes=[(self.article, 5), (self.article, 3)])
        articles = renseigner_commandes_en_cours([self.article, autre_article])
        self.assertEqual(articles[0].quantite_en_commande, Decimal("8"))
        self.assertEqual([ligne.commande for ligne in articles[0].lignes_en_cours], [commande, commande])
        self.assertEqual(articles[1].quantite_en_commande, 0)


class ChangementEtatTests(TestCase):
    def setUp(self):
        self.article = creer_article("PAT-M", stock=6, stock_mini=10, mini_commande=20)
        lien = lier_fournisseur(self.article, "Fournisseur A", prefere=True, prix=Decimal("18"))
        ArticleFournisseur.objects.filter(pk=lien.pk).update(delai=10)
        self.commande = creer_commande(lignes=[(self.article, 20)])

    def test_prix_repris_du_fournisseur(self):
        ligne = self.commande.lignes.get()
        self.assertEqual(ligne.prix_unitaire, Decimal("18"))
        self.assertEqual(self.commande.montant_total, Decimal("360"))

    def test_passer_la_commande_calcule_la_livraison_avec_le_delai_fournisseur(self):
        self.commande.changer_etat(Commande.PASSEE)
        self.assertEqual(self.commande.date_passage, AUJOURDHUI)
        self.assertEqual(self.commande.date_prevue, AUJOURDHUI + timedelta(days=10))

    def test_date_prevue_saisie_conservee(self):
        self.commande.date_prevue = AUJOURDHUI + timedelta(days=3)
        self.commande.changer_etat(Commande.PASSEE)
        self.assertEqual(self.commande.date_prevue, AUJOURDHUI + timedelta(days=3))

    def test_etat_impossible_refuse(self):
        with self.assertRaises(ValueError):
            self.commande.changer_etat(Commande.RECEPTIONNEE)

    def test_reception_entre_les_quantites_en_stock(self):
        self.commande.changer_etat(Commande.PASSEE)
        self.commande.changer_etat(Commande.RECUE)
        self.commande.receptionner({})
        self.article.refresh_from_db()
        self.assertEqual(self.article.stock, Decimal("26"))
        self.assertEqual(self.commande.etat, Commande.RECEPTIONNEE)
        self.assertEqual(self.commande.date_entree_stock, AUJOURDHUI)
        mouvement = Mouvement.objects.get(article=self.article)
        self.assertEqual(mouvement.type, Mouvement.ENTREE)
        self.assertIn(self.commande.numero, mouvement.commentaire)

    def test_reception_partielle(self):
        self.commande.changer_etat(Commande.PASSEE)
        ligne = self.commande.lignes.get()
        self.commande.receptionner({ligne: Decimal("15")})
        self.article.refresh_from_db()
        ligne.refresh_from_db()
        self.assertEqual(self.article.stock, Decimal("21"))
        self.assertEqual(ligne.manquant, Decimal("5"))
        self.assertTrue(self.commande.livraison_incomplete)

    def test_creation_depuis_les_besoins(self):
        commande = Commande.creer_pour_les_besoins(self.commande.fournisseur, [creer_article("TIG-G", stock=1, stock_mini=4, mini_commande=4)])
        ligne = commande.lignes.get()
        self.assertEqual(commande.etat, Commande.EN_ATTENTE)
        self.assertEqual(ligne.quantite, Decimal("7"))


class SuiviTests(TestCase):
    def test_en_cours_triees_par_urgence_puis_terminees(self):
        tardive = creer_commande(etat=Commande.PASSEE, date_prevue=AUJOURDHUI + timedelta(days=9))
        urgente = creer_commande(etat=Commande.PASSEE, date_prevue=AUJOURDHUI - timedelta(days=2))
        sans_date = creer_commande(etat=Commande.EN_ATTENTE)
        terminee = creer_commande(etat=Commande.RECEPTIONNEE)
        self.assertEqual(trier_pour_le_suivi(Commande.objects.all()), [urgente, tardive, sans_date, terminee])

    def test_filtres(self):
        en_retard = creer_commande(etat=Commande.PASSEE, date_prevue=AUJOURDHUI - timedelta(days=2))
        a_l_heure = creer_commande("Fournisseur B", etat=Commande.PASSEE, date_prevue=AUJOURDHUI + timedelta(days=2))
        terminee = creer_commande(etat=Commande.RECEPTIONNEE)
        toutes = list(Commande.objects.all())
        self.assertCountEqual(filtrer_commandes(toutes, "en_cours"), [en_retard, a_l_heure])
        self.assertEqual(filtrer_commandes(toutes, Commande.RECEPTIONNEE), [terminee])
        self.assertEqual(filtrer_commandes(toutes, seulement_en_retard=True), [en_retard])
        self.assertEqual(filtrer_commandes(toutes, fournisseur_id=str(a_l_heure.fournisseur_id)), [a_l_heure])
        self.assertEqual(filtrer_commandes(toutes, recherche=a_l_heure.numero.lower()), [a_l_heure])


class DroitsTests(TestCase):
    def setUp(self):
        self.article = creer_article("PAT-M", stock=6, stock_mini=10, mini_commande=20)
        lier_fournisseur(self.article, "Fournisseur A", prefere=True)
        self.commande = creer_commande(lignes=[(self.article, 20)])

    def test_operateur_ne_passe_pas_de_commande(self):
        self.client.force_login(creer_utilisateur("operateur", ATELIER))
        reponse = self.client.post(f"/commandes/{self.commande.pk}/", {"action": Commande.PASSEE})
        self.assertEqual(reponse.status_code, 403)
        reponse = self.client.post(f"/commandes/creer/{self.commande.fournisseur_id}/")
        self.assertEqual(reponse.status_code, 403)

    def test_operateur_receptionne_avec_quantite_livree(self):
        self.commande.changer_etat(Commande.PASSEE)
        ligne = self.commande.lignes.get()
        self.client.force_login(creer_utilisateur("operateur", ATELIER))
        self.client.post(f"/commandes/{self.commande.pk}/", {"action": Commande.RECEPTIONNEE, f"recu_{ligne.pk}": "12,5"})
        self.article.refresh_from_db()
        self.assertEqual(self.article.stock, Decimal("18.5"))

    def test_saisie_illisible_ne_receptionne_rien(self):
        self.commande.changer_etat(Commande.PASSEE)
        ligne = self.commande.lignes.get()
        self.client.force_login(creer_utilisateur("operateur", ATELIER))
        self.client.post(f"/commandes/{self.commande.pk}/", {"action": Commande.RECEPTIONNEE, f"recu_{ligne.pk}": "douze"})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.etat, Commande.PASSEE)

    def test_methode_prepare_la_commande_des_besoins_non_couverts(self):
        self.client.force_login(creer_utilisateur("methode", METHODE))
        self.commande.changer_etat(Commande.ANNULEE)
        reponse = self.client.post(f"/commandes/creer/{self.commande.fournisseur_id}/")
        nouvelle = Commande.objects.exclude(pk=self.commande.pk).get()
        self.assertRedirects(reponse, nouvelle.get_absolute_url())
        self.assertEqual(nouvelle.lignes.get().quantite, Decimal("24"))

    def test_rien_a_preparer_quand_tout_est_couvert(self):
        self.client.force_login(creer_utilisateur("methode", METHODE))
        self.client.post(f"/commandes/creer/{self.commande.fournisseur_id}/")
        self.assertEqual(Commande.objects.count(), 1)
