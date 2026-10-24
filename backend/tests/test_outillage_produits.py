"""Arborescence des outils et liens produit / machine / outils / consommables."""
from django.db import IntegrityError
from django.test import TestCase

from outillage.models import Outil, PieceOutil
from outillage.views import construire_arbre
from produits.models import Consommation, Machine, Produit, ProduitMachine

from .fabriques import creer_article


class ArborescenceOutilTests(TestCase):
    def setUp(self):
        self.jeu = Outil.objects.create(code="OUT-N7", nom="Jeu d'outils N7")
        self.chargeur = Outil.objects.create(code="OUT-N7-1", nom="Chargeur N7", parent=self.jeu)
        self.porte_patin = Outil.objects.create(code="OUT-N7-1-A", nom="Porte-patin", parent=self.chargeur)
        self.patin = creer_article("PAT-M")
        PieceOutil.objects.create(outil=self.chargeur, article=self.patin, quantite=2)

    def test_racine_d_un_sous_ensemble(self):
        self.assertEqual(self.porte_patin.racine(), self.jeu)
        self.assertEqual(self.jeu.racine(), self.jeu)

    def test_chemin_de_la_racine_jusqu_a_l_outil(self):
        self.assertEqual(self.porte_patin.chemin(), [self.jeu, self.chargeur, self.porte_patin])

    def test_arbre_imbrique_avec_les_pieces(self):
        arbre = construire_arbre(self.jeu)
        self.assertEqual(arbre["outil"], self.jeu)
        self.assertEqual(arbre["pieces"], [])
        noeud_chargeur = arbre["sous_ensembles"][0]
        self.assertEqual(noeud_chargeur["outil"], self.chargeur)
        self.assertEqual([piece.article for piece in noeud_chargeur["pieces"]], [self.patin])
        self.assertEqual(noeud_chargeur["sous_ensembles"][0]["outil"], self.porte_patin)

    def test_piece_partagee_entre_plusieurs_outils(self):
        autre_jeu = Outil.objects.create(code="OUT-N8", nom="Jeu d'outils N8")
        PieceOutil.objects.create(outil=autre_jeu, article=self.patin)
        self.assertEqual({outil.code for outil in self.patin.outils.all()}, {"OUT-N7-1", "OUT-N8"})

    def test_une_piece_n_est_listee_qu_une_fois_par_outil(self):
        with self.assertRaises(IntegrityError):
            PieceOutil.objects.create(outil=self.chargeur, article=self.patin)


class FicheProduitTests(TestCase):
    def setUp(self):
        self.produit = Produit.objects.create(reference="N7", designation="Produit N7")
        self.meule = Machine.objects.create(code="S5", nom="Machine S5")
        self.bandes = Machine.objects.create(code="MAD1", nom="Machine à bandes 1")

    def test_un_produit_sur_plusieurs_machines_avec_cadences_differentes(self):
        ProduitMachine.objects.create(produit=self.produit, machine=self.meule, cadence=360)
        ProduitMachine.objects.create(produit=self.produit, machine=self.bandes, cadence=430)
        cadences = {f.machine.code: f.cadence for f in self.produit.fabrications.all()}
        self.assertEqual(cadences, {"S5": 360, "MAD1": 430})
        self.assertEqual(set(self.meule.produits.all()), {self.produit})

    def test_une_seule_fiche_par_couple_produit_machine(self):
        ProduitMachine.objects.create(produit=self.produit, machine=self.meule)
        with self.assertRaises(IntegrityError):
            ProduitMachine.objects.create(produit=self.produit, machine=self.meule)

    def test_fiche_regroupe_outils_et_consommables(self):
        fabrication = ProduitMachine.objects.create(produit=self.produit, machine=self.meule)
        jeu = Outil.objects.create(code="OUT-N7", nom="Jeu d'outils N7")
        fabrication.outils.add(jeu)
        huile = creer_article("HUI-01", categorie="conso")
        Consommation.objects.create(fabrication=fabrication, article=huile, quantite="1 bidon / semaine")
        self.assertEqual(list(fabrication.outils.all()), [jeu])
        self.assertEqual(list(huile.consommations.values_list("quantite", flat=True)), ["1 bidon / semaine"])
        self.assertEqual(str(fabrication), "N7 sur S5")
