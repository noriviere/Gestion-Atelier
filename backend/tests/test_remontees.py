"""Remontées terrain : calculs et contrôles repris de l'application suivi-usure-meules, saisies et droits."""
from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from comptes import roles
from inventaire.models import Mouvement
from produits.models import Machine, Produit
from remontees import regles
from remontees.models import FormatMatiere, Matricule, SaisieMeule

from .fabriques import creer_article, creer_utilisateur

MINIMUM_HISTORIQUE = int(regles.DEFAUTS.valeur("hors_habitude", "minimum"))


class CalculsTests(SimpleTestCase):
    """Les colonnes que le classeur calculait par formules."""

    def test_valeurs_calculees_d_une_meule_finie(self):
        saisie = SaisieMeule(compteur_debut=0, compteur_fin=9000, hauteur_initiale=Decimal("100"),
                             hauteur_finale=Decimal("0"))
        self.assertEqual(saisie.nombre_faces_brut, 9000)
        self.assertEqual(saisie.hauteur_usee, Decimal("100"))
        self.assertEqual(saisie.faces_par_mm, Decimal("90"))
        self.assertEqual(saisie.faces_par_meule_reference, Decimal("8010"))
        self.assertEqual(saisie.hauteur_usee_par_face, Decimal("100") / 9000)
        self.assertFalse(regles.demontee_avant_usure(saisie.hauteur_finale))

    def test_compteur_qui_ne_part_pas_de_zero(self):
        saisie = SaisieMeule(compteur_debut=150, compteur_fin=1150, hauteur_initiale=Decimal("100"),
                             hauteur_finale=Decimal("90"))
        self.assertEqual(saisie.nombre_faces_brut, 1000)
        self.assertEqual(saisie.faces_par_mm, Decimal("100"))

    def test_pas_de_division_par_zero(self):
        saisie = SaisieMeule(compteur_debut=0, compteur_fin=0, hauteur_initiale=Decimal("100"),
                             hauteur_finale=Decimal("100"))
        self.assertIsNone(saisie.faces_par_mm)
        self.assertIsNone(saisie.faces_par_meule_reference)
        self.assertIsNone(saisie.hauteur_usee_par_face)

    def test_meule_montee_sans_demontage(self):
        saisie = SaisieMeule(compteur_debut=0, hauteur_initiale=Decimal("100"))
        self.assertIsNone(saisie.nombre_faces_brut)
        self.assertIsNone(saisie.hauteur_usee)
        self.assertFalse(regles.demontee_avant_usure(saisie.hauteur_finale))

    def test_marque_x_au_dela_du_seuil(self):
        self.assertFalse(regles.demontee_avant_usure(Decimal("2")))
        self.assertTrue(regles.demontee_avant_usure(Decimal("2.5")))

    def test_defaut_seulement_si_cassee_et_pas_finie(self):
        self.assertTrue(regles.est_un_defaut(True, [regles.THEME_DEFAUT], Decimal("30")))
        self.assertFalse(regles.est_un_defaut(True, [regles.THEME_DEFAUT], Decimal("0.5")))
        self.assertFalse(regles.est_un_defaut(True, ["Bruit / vibrations"], Decimal("30")))
        self.assertFalse(regles.est_un_defaut(False, [], Decimal("30")))


class ValeurInhabituelleTests(SimpleTestCase):
    HISTORIQUE = [10, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 15, 16, 16, 17, 17, 18, 18, 19, 20]

    def test_zone_habituelle_regle_de_tukey(self):
        q1, q3, bas, haut = regles.zone_habituelle(self.HISTORIQUE, 1.5)
        self.assertEqual((q1, q3), (13.0, 17.0))
        self.assertAlmostEqual(bas, 13 - 1.5 * 4)
        self.assertAlmostEqual(haut, 17 + 1.5 * 4)

    def test_valeur_hors_zone_signalee(self):
        texte = regles.avertissement_inhabituel("Vitesse", 40, self.HISTORIQUE, "toutes les saisies", 20, 1.5)
        self.assertIn("40 est inhabituel", texte)
        self.assertIn("entre 13 et 17", texte)
        self.assertEqual(regles.avertissement_inhabituel("Vitesse", 16, self.HISTORIQUE, "toutes les saisies", 20, 1.5), "")

    def test_pas_assez_d_historique_pour_juger(self):
        self.assertEqual(regles.avertissement_inhabituel("Vitesse", 400, self.HISTORIQUE[:19], "toutes", 20, 1.5), "")


class DonneesMeulesMixin:
    """Une machine S1 prévue pour N2 inox avec la meule MEU-200, et une machine S9 non prévue."""

    @classmethod
    def setUpTestData(cls):
        cls.s1 = Machine.objects.create(code="S1", nom="Machine S1")
        cls.s9 = Machine.objects.create(code="S9", nom="Machine S9")
        cls.n2 = Produit.objects.create(reference="N2", designation="Produit N2")
        cls.meule = creer_article("MEU-200", stock=6, unite="meule")
        cls.autre_meule = creer_article("MEU-300", stock=3, unite="meule")
        cls.format_inox = FormatMatiere.objects.create(produit=cls.n2, matiere="I", code_lame="L2I", ma5="oui")
        cls.format_inox.meules.set([cls.meule])
        cls.format_inox.machines.set([cls.s1])
        cls.format_carbone = FormatMatiere.objects.create(produit=cls.n2, matiere="C", code_lame="L2C",
                                                          ma5="peut_etre")
        cls.format_carbone.meules.set([cls.autre_meule])
        cls.matricule = Matricule.objects.create(numero="0534")
        cls.operateur = creer_utilisateur("operateur", roles.OPERATEUR)

    def setUp(self):
        self.client.force_login(self.operateur)

    def donnees_montage(self, **modifications):
        donnees = {
            "machine": self.s1.pk, "matricule_monteur": "534", "produit": self.n2.pk, "matiere": "I", "face": "A",
            "meule": self.meule.pk, "lot_fournisseur": "FA123456", "date_montage": timezone.localdate().isoformat(),
            "pression_arrosage": 6, "vitesse_rotation": 35, "vitesse_avance": 140, "hauteur_initiale": "104",
            "compteur_debut": 0, "commentaire_montage": "", "sortir_du_stock": "on",
        }
        donnees.update(modifications)
        return donnees

    def monter(self, **modifications):
        return SaisieMeule.objects.create(
            machine=self.s1, format_matiere=self.format_inox, face="A", meule=self.meule, lot_fournisseur="FA1",
            date_montage=timezone.localdate(), vitesse_rotation=35, vitesse_avance=140,
            hauteur_initiale=Decimal("100"), matricule_monteur=self.matricule, **modifications,
        )


class MontageTests(DonneesMeulesMixin, TestCase):
    def test_montage_enregistre_et_sort_la_meule_du_stock(self):
        reponse = self.client.post("/remontees/meules/montage/", self.donnees_montage())
        self.assertRedirects(reponse, "/remontees/?machine=S1")
        saisie = SaisieMeule.objects.get()
        self.assertEqual((saisie.machine, saisie.format_matiere, saisie.code_lame), (self.s1, self.format_inox, "L2I"))
        self.assertTrue(saisie.ma5)  # choisi automatiquement : la table dit « oui »
        self.assertEqual(saisie.matricule_monteur, self.matricule)  # « 534 » devient « 0534 »
        self.assertEqual(saisie.monte_par, self.operateur)
        self.meule.refresh_from_db()
        self.assertEqual(self.meule.stock, 5)
        self.assertEqual(saisie.sortie_stock.type, Mouvement.SORTIE)
        self.assertNotIn("S1", saisie.sortie_stock.commentaire)  # les sorties ne sont pas rattachées à une machine

    def test_case_decochee_pas_de_sortie_de_stock(self):
        donnees = self.donnees_montage()
        del donnees["sortir_du_stock"]
        self.client.post("/remontees/meules/montage/", donnees)
        self.assertIsNone(SaisieMeule.objects.get().sortie_stock)
        self.meule.refresh_from_db()
        self.assertEqual(self.meule.stock, 6)

    def test_sans_droit_de_sortie_la_case_disparait(self):
        regleur = creer_utilisateur("regleur", roles.REGLEUR)
        regleur.groups.get().droits.filter(code="stock_mouvements").delete()
        self.client.force_login(regleur)
        self.assertNotContains(self.client.get("/remontees/meules/montage/"), 'name="sortir_du_stock"')
        self.client.post("/remontees/meules/montage/", self.donnees_montage())
        self.assertIsNone(SaisieMeule.objects.get().sortie_stock)

    def test_format_absent_de_la_table_refuse(self):
        FormatMatiere.objects.filter(matiere="C").delete()
        reponse = self.client.post("/remontees/meules/montage/", self.donnees_montage(matiere="C"))
        self.assertContains(reponse, "est absent de la table")
        self.assertFalse(SaisieMeule.objects.exists())

    def test_ma5_peut_etre_demande_un_choix(self):
        reponse = self.client.post("/remontees/meules/montage/",
                                   self.donnees_montage(matiere="C", meule=self.autre_meule.pk))
        self.assertContains(reponse, "choisissez Oui ou Non")
        self.client.post("/remontees/meules/montage/",
                         self.donnees_montage(matiere="C", meule=self.autre_meule.pk, ma5="non"))
        self.assertFalse(SaisieMeule.objects.get().ma5)

    def test_limites_bloquantes(self):
        reponse = self.client.post("/remontees/meules/montage/",
                                   self.donnees_montage(vitesse_rotation=60, hauteur_initiale="120"))
        self.assertContains(reponse, "Vitesse de rotation : 60 dépasse le maximum de 50 m/s")
        self.assertContains(reponse, "Hauteur initiale de la meule : 120 dépasse le maximum de 110 mm")
        self.assertFalse(SaisieMeule.objects.exists())

    def test_machine_non_prevue_demande_un_commentaire_puis_une_confirmation(self):
        reponse = self.client.post("/remontees/meules/montage/", self.donnees_montage(machine=self.s9.pk))
        self.assertContains(reponse, "Commentaire obligatoire : S9 n&#x27;est pas prévue")
        reponse = self.client.post("/remontees/meules/montage/",
                                   self.donnees_montage(machine=self.s9.pk, commentaire_montage="S1 en panne"))
        self.assertContains(reponse, "Enregistrer quand même")
        self.assertFalse(SaisieMeule.objects.exists())
        avertissements_vus = reponse.context["form"].data["avertissements_vus"]
        self.client.post("/remontees/meules/montage/", self.donnees_montage(
            machine=self.s9.pk, commentaire_montage="S1 en panne", avertissements_vus=avertissements_vus))
        self.assertIn("S9 n'est pas prévue", SaisieMeule.objects.get().avertissements)

    def test_un_nouvel_avertissement_redemande_confirmation(self):
        reponse = self.client.post("/remontees/meules/montage/", self.donnees_montage(meule=self.autre_meule.pk))
        avertissements_vus = reponse.context["form"].data["avertissements_vus"]
        demain = (timezone.localdate() + timedelta(days=1)).isoformat()
        reponse = self.client.post("/remontees/meules/montage/", self.donnees_montage(
            meule=self.autre_meule.pk, date_montage=demain, avertissements_vus=avertissements_vus))
        self.assertContains(reponse, "est dans le futur")
        self.assertFalse(SaisieMeule.objects.exists())

    def test_nouveau_matricule_ajoute_apres_confirmation(self):
        reponse = self.client.post("/remontees/meules/montage/", self.donnees_montage(matricule_monteur="0999"))
        self.assertContains(reponse, "Matricule 0999 : jamais utilisé")
        self.assertFalse(Matricule.objects.filter(numero="0999").exists())
        self.client.post("/remontees/meules/montage/", self.donnees_montage(
            matricule_monteur="0999", avertissements_vus=reponse.context["form"].data["avertissements_vus"]))
        self.assertEqual(SaisieMeule.objects.get().matricule_monteur.numero, "0999")

    def test_matricule_illisible_refuse(self):
        reponse = self.client.post("/remontees/meules/montage/", self.donnees_montage(matricule_monteur="12a"))
        self.assertContains(reponse, "Un matricule a 4 chiffres")

    def test_valeur_inhabituelle_par_rapport_a_l_historique(self):
        for _ in range(MINIMUM_HISTORIQUE):
            self.monter()
        reponse = self.client.post("/remontees/meules/montage/", self.donnees_montage(vitesse_avance=400))
        self.assertContains(reponse, "Vitesse d&#x27;avance : 400 est inhabituel")
        self.assertEqual(SaisieMeule.objects.count(), MINIMUM_HISTORIQUE)

    def test_pression_zero_jamais_signalee(self):
        for _ in range(MINIMUM_HISTORIQUE):
            self.monter(pression_arrosage=6)
        # Les autres valeurs sont celles de l'historique : seule la pression pourrait être signalée.
        self.client.post("/remontees/meules/montage/", self.donnees_montage(pression_arrosage=0, hauteur_initiale="100"))
        self.assertTrue(SaisieMeule.objects.filter(pression_arrosage=0).exists())


class DemontageTests(DonneesMeulesMixin, TestCase):
    def donnees_demontage(self, **modifications):
        donnees = {"matricule_demonteur": "0534", "compteur_fin": 9000, "hauteur_finale": "0.5", "probleme": "non",
                   "commentaire": ""}
        donnees.update(modifications)
        return donnees

    def test_demontage_enregistre_et_calcule(self):
        saisie = self.monter()
        reponse = self.client.post(f"/remontees/meules/{saisie.pk}/demontage/", self.donnees_demontage())
        self.assertRedirects(reponse, f"/remontees/meules/{saisie.pk}/")
        saisie.refresh_from_db()
        self.assertTrue(saisie.est_demontee)
        self.assertEqual(saisie.nombre_faces_brut, 9000)
        self.assertFalse(saisie.defaut)
        self.assertContains(self.client.get(saisie.get_absolute_url()), "9000")

    def test_controles_bloquants(self):
        saisie = self.monter(compteur_debut=100)
        reponse = self.client.post(f"/remontees/meules/{saisie.pk}/demontage/",
                                   self.donnees_demontage(compteur_fin=50, hauteur_finale="120"))
        self.assertContains(reponse, "est inférieur au compteur au montage (100)")
        self.assertContains(reponse, "est supérieure à la hauteur initiale")
        saisie.refresh_from_db()
        self.assertFalse(saisie.est_demontee)

    def test_meule_non_finie_demande_un_commentaire(self):
        saisie = self.monter()
        reponse = self.client.post(f"/remontees/meules/{saisie.pk}/demontage/", self.donnees_demontage(hauteur_finale="12"))
        self.assertContains(reponse, "il reste 12 mm")
        self.client.post(f"/remontees/meules/{saisie.pk}/demontage/",
                         self.donnees_demontage(hauteur_finale="12", commentaire="Changement de série"))
        saisie.refresh_from_db()
        self.assertTrue(saisie.non_finie)

    def test_meule_cassee_marquee_defaut(self):
        saisie = self.monter()
        self.client.post(f"/remontees/meules/{saisie.pk}/demontage/", self.donnees_demontage(
            hauteur_finale="40", probleme="oui", themes=[regles.THEME_DEFAUT], commentaire="Constat : fissure"))
        saisie.refresh_from_db()
        self.assertTrue(saisie.defaut)
        self.assertEqual(saisie.themes, [regles.THEME_DEFAUT])

    def test_probleme_sans_theme_refuse(self):
        saisie = self.monter()
        reponse = self.client.post(f"/remontees/meules/{saisie.pk}/demontage/", self.donnees_demontage(probleme="oui"))
        self.assertContains(reponse, "Choisissez au moins un thème")

    def test_rien_a_signaler_efface_les_themes(self):
        saisie = self.monter()
        self.client.post(f"/remontees/meules/{saisie.pk}/demontage/",
                         self.donnees_demontage(themes=["Bruit / vibrations"]))
        saisie.refresh_from_db()
        self.assertEqual(saisie.themes, [])

    def test_doublon_signale(self):
        self.monter(compteur_fin=9000, hauteur_finale=Decimal("0"), demonte_le=timezone.now())
        saisie = self.monter()
        reponse = self.client.post(f"/remontees/meules/{saisie.pk}/demontage/", self.donnees_demontage())
        self.assertContains(reponse, "Est-ce un doublon ?")

    def test_meule_deja_demontee_renvoie_a_sa_page(self):
        saisie = self.monter(compteur_fin=10, hauteur_finale=Decimal("0"), demonte_le=timezone.now())
        self.assertRedirects(self.client.get(f"/remontees/meules/{saisie.pk}/demontage/"), saisie.get_absolute_url())


class EcranRemonteesTests(DonneesMeulesMixin, TestCase):
    def test_machines_et_meules_montees(self):
        saisie = self.monter()
        reponse = self.client.get("/remontees/")
        self.assertContains(reponse, "1 meule montée")
        reponse = self.client.get("/remontees/?machine=S1")
        self.assertContains(reponse, f'href="/remontees/meules/{saisie.pk}/demontage/"')
        self.assertContains(reponse, 'href="/remontees/meules/montage/?machine=S1"')

    def test_formulaire_de_montage_prerempli(self):
        reponse = self.client.get("/remontees/meules/montage/?machine=S1")
        self.assertEqual(reponse.context["form"]["machine"].value(), self.s1.pk)
        self.assertEqual(reponse.context["form"]["pression_arrosage"].value(), 6)
        self.assertContains(reponse, '<option value="0534">')
        self.assertContains(reponse, '"code_lame": "L2I"')

    def test_tous_les_profils_saisissent(self):
        for profil in roles.PROFILS_REGLABLES:
            self.client.force_login(creer_utilisateur(f"compte-{len(profil)}-{profil[:3]}", profil))
            self.assertEqual(self.client.get("/remontees/meules/montage/").status_code, 200, profil)

    def test_sans_droit_page_fermee(self):
        self.client.force_login(creer_utilisateur("sans-profil"))
        self.assertEqual(self.client.get("/remontees/").status_code, 403)

    def test_parametrage_reserve_a_methode(self):
        self.assertFalse(roles.a_le_droit(self.operateur, "remontees_parametrer"))
        self.assertTrue(roles.a_le_droit(creer_utilisateur("methode", roles.METHODE), "remontees_parametrer"))
