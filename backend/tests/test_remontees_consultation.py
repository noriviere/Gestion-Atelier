"""Remontées, étape 2 : consultation, statistiques, contrôle qualité, règles réglables et correction."""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from openpyxl import load_workbook

from comptes import roles
from remontees import regles, statistiques
from remontees.models import HistoriqueRegle, RegleMeule, SaisieMeule, ThemeProbleme

from .fabriques import creer_utilisateur
from .test_remontees import DonneesMeulesMixin


class ReglagesTests(SimpleTestCase):
    def test_valeurs_d_origine(self):
        self.assertTrue(regles.DEFAUTS.actif("doublon"))
        self.assertEqual(regles.DEFAUTS.seuil_non_finie, Decimal("2"))
        self.assertEqual(regles.DEFAUTS.valeur("prix_meule"), Decimal("150"))

    def test_valeurs_enregistrees(self):
        reglages = regles.Reglages({"non_finie": (True, {"seuil": "5"}), "doublon": (False, {})})
        self.assertEqual(reglages.seuil_non_finie, Decimal("5"))
        self.assertFalse(reglages.actif("doublon"))
        self.assertFalse(regles.demontee_avant_usure(Decimal("4"), reglages))
        self.assertTrue(regles.demontee_avant_usure(Decimal("4")))

    def test_regle_sans_interrupteur_toujours_active(self):
        self.assertTrue(regles.Reglages({"prix_meule": (False, {})}).actif("prix_meule"))

    def test_perte_estimee(self):
        self.assertEqual(regles.perte_estimee(Decimal("100"), Decimal("25"), Decimal("150")), Decimal("37.5"))
        self.assertEqual(regles.perte_estimee(Decimal("100"), Decimal("0"), Decimal("150")), 0)


class StatistiquesTests(DonneesMeulesMixin, TestCase):
    def demonter(self, faces, hauteur_finale="0", jours=0, **modifications):
        saisie = self.monter(compteur_fin=faces, hauteur_finale=Decimal(hauteur_finale), demonte_le=timezone.now(),
                             **modifications)
        if jours:
            saisie.date_montage = timezone.localdate() - timedelta(days=jours)
        saisie.marquer(regles.DEFAUTS)
        saisie.save()
        return saisie

    def toutes(self):
        return list(SaisieMeule.objects.demontees().select_related("machine", "meule", "format_matiere__produit")
                    .prefetch_related("format_matiere__machines", "format_matiere__meules"))

    def test_mediane_attendue_elargit_le_critere(self):
        # 100 mm usés : faces pour 89 mm = faces × 0,89.
        for faces in (1000, 2000, 3000):
            self.demonter(faces)
        attendue = statistiques.mediane_attendue(self.toutes(), self.meule, self.s1, "I", "A")
        self.assertEqual(attendue["mediane"], 1780)
        self.assertEqual(attendue["nombre"], 3)
        self.assertFalse(attendue["fiable"])
        for faces in (1000, 1000, 1000):
            SaisieMeule.objects.filter(pk=self.demonter(faces).pk).update(machine=self.s9)
        attendue = statistiques.mediane_attendue(self.toutes(), self.meule, self.s1, "I", "A")
        self.assertEqual(attendue["critere"], "meule + matière")
        self.assertTrue(attendue["fiable"])

    def test_lignes_pour_les_statistiques(self):
        self.demonter(1000)
        self.demonter(0)
        saisies = sorted(self.toutes(), key=lambda saisie: saisie.pk)
        [ligne, sans_face] = statistiques.lignes_pour_les_statistiques(saisies, {self.meule.pk: "Tyrolit"})
        self.assertEqual((ligne["format"], ligne["matiere"], ligne["machine"], ligne["article"], ligne["fournisseur"]),
                         ("N2", "Inox", "S1", "MEU-200", "Tyrolit"))
        self.assertEqual((ligne["faces_89"], ligne["faces_mm"], ligne["usure"], ligne["x"]), (890.0, 10.0, 100.0, False))
        self.assertIsNone(sans_face["faces_89"])  # aucune face : erreur de saisie, pas une durée de vie

    def test_perte_par_machine(self):
        self.demonter(1000, hauteur_finale="25", commentaire="Changement de série")
        self.demonter(1000)
        perte = statistiques.perte(self.toutes(), timezone.localdate().year, Decimal("100"))
        self.assertEqual((perte["total"], perte["nombre"]), (Decimal("25"), 1))
        self.assertEqual(perte["par_machine"], [("S1", Decimal("25"))])

    def test_anomalies(self):
        inverse = self.demonter(10, compteur_debut=50)
        sans_commentaire = self.demonter(1000, hauteur_finale="20")
        premier = self.demonter(500)
        doublon = self.demonter(500)
        anomalies = statistiques.anomalies(self.toutes(), regles.DEFAUTS)
        motifs = {(anomalie["saisie"].pk, anomalie["gravite"]): anomalie["motif"] for anomalie in anomalies}
        self.assertIn("inférieur au compteur au montage", motifs[(inverse.pk, statistiques.GRAVE)])
        self.assertEqual(motifs[(sans_commentaire.pk, statistiques.MINEUR)], "meule non finie sans explication")
        self.assertIn(f"identique à la saisie n° {premier.pk}", motifs[(doublon.pk, statistiques.VERIF)])
        self.assertEqual(anomalies[0]["gravite"], statistiques.GRAVE)

    def test_duree_eloignee(self):
        for numero in range(9):
            self.demonter(1000 + numero)  # compteurs différents : pas de doublon
        eloignee = self.demonter(9000)
        anomalies = statistiques.anomalies(self.toutes(), regles.DEFAUTS)
        self.assertEqual([anomalie["saisie"] for anomalie in anomalies], [eloignee])
        reglages = regles.Reglages({"duree_eloignee": (False, {})})
        self.assertEqual(statistiques.anomalies(self.toutes(), reglages), [])


class PagesConsultationTests(DonneesMeulesMixin, TestCase):
    def test_liste_filtree(self):
        montee = self.monter()
        demontee = self.monter(compteur_fin=1000, hauteur_finale=Decimal("10"), non_finie=True,
                               demonte_le=timezone.now(), commentaire="Changement de série")
        reponse = self.client.get("/remontees/meules/")
        self.assertEqual(list(reponse.context["saisies"]), [demontee, montee])
        reponse = self.client.get("/remontees/meules/?etat=non_finie")
        self.assertEqual(list(reponse.context["saisies"]), [demontee])
        reponse = self.client.get("/remontees/meules/?q=changement")
        self.assertEqual(list(reponse.context["saisies"]), [demontee])
        self.assertEqual(list(self.client.get("/remontees/meules/?machine=S9").context["saisies"]), [])
        self.assertEqual(self.client.get("/remontees/meules/?meule=abc").status_code, 200)

    def test_statistiques_et_controle_pour_tous(self):
        self.monter(compteur_fin=1000, hauteur_finale=Decimal("0"), demonte_le=timezone.now())
        for adresse in ("/remontees/meules/statistiques/", "/remontees/meules/controle/",
                        "/remontees/meules/controle/?gravite=a-verifier"):
            self.assertEqual(self.client.get(adresse).status_code, 200, adresse)

    def test_export_excel_du_controle(self):
        self.monter(compteur_debut=50, compteur_fin=10, hauteur_finale=Decimal("0"), demonte_le=timezone.now())
        reponse = self.client.get("/remontees/meules/controle/controle-meules.xlsx")
        feuille = load_workbook(BytesIO(reponse.content)).active
        self.assertEqual(feuille["A1"].value, "Gravité")
        self.assertEqual(feuille["A2"].value, statistiques.GRAVE)
        self.assertEqual(feuille["H2"].value, "Compteur au démontage")

    def test_duree_de_vie_habituelle_sur_la_page_de_la_saisie(self):
        self.monter(compteur_fin=1000, hauteur_finale=Decimal("0"), demonte_le=timezone.now())
        saisie = self.monter(compteur_fin=2000, hauteur_finale=Decimal("0"), demonte_le=timezone.now())
        reponse = self.client.get(saisie.get_absolute_url())
        self.assertContains(reponse, "<strong>890 faces</strong>")
        self.assertNotContains(reponse, "Corriger ou supprimer")


class ReglesPageTests(DonneesMeulesMixin, TestCase):
    def setUp(self):
        self.methode = creer_utilisateur("methode", roles.METHODE)
        self.client.force_login(self.methode)

    def donnees_regles(self, **modifications):
        donnees = {"formulaire": "regles"}
        for regle in regles.CATALOGUE:
            if regle.interrupteur:
                donnees[f"actif_{regle.code}"] = "on"
            for parametre in regle.parametres:
                donnees[f"{regle.code}__{parametre.cle}"] = str(parametre.defaut)
        donnees.update(modifications)
        return {cle: valeur for cle, valeur in donnees.items() if valeur is not None}

    def test_reserve_au_parametrage(self):
        self.client.force_login(self.operateur)
        self.assertEqual(self.client.get("/remontees/meules/regles/").status_code, 403)
        self.assertNotContains(self.client.get("/remontees/meules/"), "/remontees/meules/regles/")

    def test_changer_une_regle_et_historique(self):
        self.client.post("/remontees/meules/regles/", self.donnees_regles(non_finie__seuil="5", actif_doublon=None,
                                                                         prix_meule__valeur="200"))
        reglages = regles.lire_reglages()
        self.assertEqual(reglages.seuil_non_finie, Decimal("5"))
        self.assertFalse(reglages.actif("doublon"))
        self.assertEqual(RegleMeule.objects.get(code="prix_meule").valeurs, {"valeur": "200"})
        textes = set(HistoriqueRegle.objects.values_list("texte", flat=True))
        self.assertIn("Meule démontée avant usure totale, seuil de hauteur finale : 2 → 5 mm", textes)
        self.assertIn("Saisie identique à une saisie existante : désactivée", textes)
        self.assertEqual(len(textes), 3)

    def test_valeur_hors_limites_refusee(self):
        reponse = self.client.post("/remontees/meules/regles/", self.donnees_regles(rotation_max__valeur="0"))
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(RegleMeule.objects.exists())

    def test_regle_desactivee_ne_previent_plus(self):
        self.client.post("/remontees/meules/regles/", self.donnees_regles(actif_nouveau_matricule=None))
        self.client.force_login(self.operateur)
        saisie = self.monter()
        reponse = self.client.post(f"/remontees/meules/{saisie.pk}/demontage/", {
            "matricule_demonteur": "9999", "compteur_fin": 9000, "hauteur_finale": "0.5", "probleme": "non"})
        self.assertRedirects(reponse, saisie.get_absolute_url())

    def test_revenir_aux_valeurs_d_origine(self):
        RegleMeule.objects.create(code="non_finie", valeurs={"seuil": "5"})
        self.client.post("/remontees/meules/regles/", {"formulaire": "origine"})
        self.assertFalse(RegleMeule.objects.exists())
        self.assertEqual(HistoriqueRegle.objects.get().texte, "Toutes les règles remises aux valeurs d'origine")

    def test_themes(self):
        bruit = ThemeProbleme.objects.get(libelle="Bruit / vibrations")
        defaut = ThemeProbleme.objects.get(libelle=regles.THEME_DEFAUT)
        donnees = {"formulaire": "themes", "nouveau": "Lubrification"}
        for theme in ThemeProbleme.objects.all():
            donnees[f"libelle_{theme.pk}"] = theme.libelle
            donnees[f"actif_{theme.pk}"] = "on"
        donnees[f"libelle_{bruit.pk}"] = "Bruit"
        del donnees[f"actif_{defaut.pk}"]  # le thème du défaut ne se retire pas
        donnees[f"libelle_{defaut.pk}"] = "Cassée"  # ni ne se renomme
        self.client.post("/remontees/meules/regles/", donnees)
        bruit.refresh_from_db()
        defaut.refresh_from_db()
        self.assertEqual(bruit.libelle, "Bruit")
        self.assertEqual((defaut.libelle, defaut.actif), (regles.THEME_DEFAUT, True))
        self.assertTrue(ThemeProbleme.objects.filter(libelle="Lubrification", actif=True).exists())
        self.assertEqual(HistoriqueRegle.objects.count(), 2)

    def test_themes_en_double_refuses(self):
        donnees = {"formulaire": "themes", "nouveau": "Autre"}
        for theme in ThemeProbleme.objects.all():
            donnees[f"libelle_{theme.pk}"] = theme.libelle
            donnees[f"actif_{theme.pk}"] = "on"
        reponse = self.client.post("/remontees/meules/regles/", donnees)
        self.assertContains(reponse, "Deux thèmes ont le même libellé : Autre.")


class CorrectionTests(DonneesMeulesMixin, TestCase):
    def donnees_correction(self, saisie, **modifications):
        donnees = {
            "machine": saisie.machine_id, "format_matiere": saisie.format_matiere_id, "face": saisie.face,
            "meule": saisie.meule_id, "lot_fournisseur": saisie.lot_fournisseur,
            "date_montage": saisie.date_montage.isoformat(), "pression_arrosage": 6, "vitesse_rotation": 35,
            "vitesse_avance": 140, "hauteur_initiale": "100", "compteur_debut": 0, "matricule_monteur": "0534",
            "matricule_demonteur": "0534", "compteur_fin": 9000, "hauteur_finale": "0", "commentaire": "",
        }
        donnees.update(modifications)
        return donnees

    def test_reserve_a_methode(self):
        saisie = self.monter()
        self.assertEqual(self.client.get(f"/remontees/meules/{saisie.pk}/modifier/").status_code, 403)
        self.assertEqual(self.client.post(f"/remontees/meules/{saisie.pk}/supprimer/").status_code, 403)

    def test_correction_recalcule_les_marques(self):
        methode = creer_utilisateur("methode", roles.METHODE)
        self.client.force_login(methode)
        saisie = self.monter(compteur_fin=9000, hauteur_finale=Decimal("0"), demonte_le=timezone.now(),
                             matricule_demonteur=self.matricule)
        self.assertContains(self.client.get(saisie.get_absolute_url()), "Corriger ou supprimer")
        reponse = self.client.post(f"/remontees/meules/{saisie.pk}/modifier/", self.donnees_correction(
            saisie, hauteur_finale="30", probleme="on", themes=[regles.THEME_DEFAUT], matricule_demonteur="77"))
        self.assertRedirects(reponse, saisie.get_absolute_url())
        saisie.refresh_from_db()
        self.assertTrue(saisie.non_finie)
        self.assertTrue(saisie.defaut)
        self.assertEqual(saisie.matricule_demonteur.numero, "0077")
        self.assertEqual(saisie.corrige_par, methode)

    def test_correction_incoherente_refusee(self):
        self.client.force_login(creer_utilisateur("methode", roles.METHODE))
        saisie = self.monter(compteur_fin=9000, hauteur_finale=Decimal("0"), demonte_le=timezone.now(),
                             matricule_demonteur=self.matricule)
        reponse = self.client.post(f"/remontees/meules/{saisie.pk}/modifier/",
                                   self.donnees_correction(saisie, hauteur_finale="120"))
        self.assertContains(reponse, "Supérieure à la hauteur initiale")

    def test_correction_d_une_meule_montee(self):
        self.client.force_login(creer_utilisateur("methode", roles.METHODE))
        saisie = self.monter()
        donnees = self.donnees_correction(saisie, lot_fournisseur="FA999")
        reponse = self.client.post(f"/remontees/meules/{saisie.pk}/modifier/", donnees)
        self.assertRedirects(reponse, saisie.get_absolute_url())
        saisie.refresh_from_db()
        self.assertEqual(saisie.lot_fournisseur, "FA999")
        self.assertFalse(saisie.est_demontee)

    def test_suppression(self):
        self.client.force_login(creer_utilisateur("methode", roles.METHODE))
        saisie = self.monter()
        self.assertRedirects(self.client.post(f"/remontees/meules/{saisie.pk}/supprimer/"), "/remontees/meules/")
        self.assertFalse(SaisieMeule.objects.exists())


class ControlesEnDirectTests(DonneesMeulesMixin, TestCase):
    def test_montage(self):
        for numero in range(MINIMUM_ZONE):
            SaisieMeule.objects.filter(pk=self.monter().pk).update(vitesse_rotation=30 + numero % 5)
        self.monter(compteur_fin=1000, hauteur_finale=Decimal("0"), demonte_le=timezone.now())
        controles = regles.controles_en_direct(regles.DEFAUTS)
        self.assertEqual(controles["limites"]["vitesse_rotation"], {"maximum": 50.0, "unite": "m/s"})
        self.assertEqual(controles["matricules"], ["0534"])
        zone = controles["zones"]["vitesse_rotation"]
        self.assertLess(zone["bas"], 30)
        self.assertGreater(zone["haut"], 34)
        self.assertLess(zone["haut"], 40)
        self.assertEqual(controles["durees"], [[self.meule.pk, self.s1.pk, "I", "A", 890.0]])

    def test_regle_desactivee(self):
        reglages = regles.Reglages({"hors_habitude": (False, {}), "rotation_max": (False, {})})
        controles = regles.controles_en_direct(reglages)
        self.assertEqual(controles["zones"], {})
        self.assertNotIn("vitesse_rotation", controles["limites"])
        self.assertFalse(controles["actives"]["hors_habitude"])

    def test_demontage(self):
        self.monter(compteur_fin=1000, hauteur_finale=Decimal("25"), demonte_le=timezone.now())
        saisie = self.monter(compteur_debut=5)
        controles = regles.controles_en_direct(regles.DEFAUTS, saisie)
        self.assertEqual(controles["saisie"], {"compteur_debut": 5, "hauteur_initiale": 100.0, "meule": "MEU-200"})
        self.assertEqual(controles["perte_annee"], 37.5)
        self.assertIsNone(controles["zones"]["compteur_fin"])  # pas assez d'historique

    def test_pages_de_saisie_portent_les_controles(self):
        saisie = self.monter()
        self.assertContains(self.client.get("/remontees/meules/montage/"), 'id="controles-meules"')
        self.assertContains(self.client.get(f"/remontees/meules/{saisie.pk}/demontage/"), 'id="controles-meules"')
        self.assertContains(self.client.get("/remontees/meules/statistiques/"), 'id="lignes-statistiques"')


MINIMUM_ZONE = int(regles.DEFAUTS.valeur("hors_habitude", "minimum"))
