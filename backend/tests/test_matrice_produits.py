"""Matrice produits × machines, duplication de fiches et de produits, paramètres, documents et formulaires."""
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from comptes.roles import ATELIER, METHODE, REGLEUR
from outillage.models import Outil
from produits import matrice
from produits.models import Consommation, Document, Machine, Parametre, Produit, ProduitMachine

from .fabriques import creer_article, creer_utilisateur


class EtatAfficheTests(TestCase):
    def test_a_faire_devient_a_securiser_si_le_produit_tourne_deja_ailleurs(self):
        self.assertEqual(matrice.etat_affiche(ProduitMachine.A_FAIRE, 0), ProduitMachine.A_FAIRE)
        self.assertEqual(matrice.etat_affiche(ProduitMachine.A_FAIRE, 1), matrice.A_SECURISER)

    def test_possible_s_affiche_vide_et_les_autres_etats_ne_changent_pas(self):
        self.assertEqual(matrice.etat_affiche(ProduitMachine.POSSIBLE, 2), matrice.VIDE)
        self.assertEqual(matrice.etat_affiche(ProduitMachine.PROGRAMME, 2), ProduitMachine.PROGRAMME)
        self.assertEqual(matrice.etat_affiche(ProduitMachine.NON_FAISABLE, 0), ProduitMachine.NON_FAISABLE)


class MatriceTests(TestCase):
    def setUp(self):
        self.s1, self.s2, self.mad1 = (Machine.objects.create(code=code, nom=code) for code in ("S1", "S2", "MAD1"))
        self.n2 = Produit.objects.create(reference="N2", designation="Produit N2")
        self.n3 = Produit.objects.create(reference="N3", designation="Produit N3", client="Client X")
        self.n4 = Produit.objects.create(reference="N4", designation="Produit N4")
        ProduitMachine.objects.create(produit=self.n2, machine=self.s1, etat=ProduitMachine.PROGRAMME)
        ProduitMachine.objects.create(produit=self.n2, machine=self.s2, etat=ProduitMachine.A_FAIRE)
        ProduitMachine.objects.create(produit=self.n2, machine=self.mad1, etat=ProduitMachine.NON_FAISABLE)
        ProduitMachine.objects.create(produit=self.n3, machine=self.s1, etat=ProduitMachine.PROGRAMME)
        ProduitMachine.objects.create(produit=self.n3, machine=self.s2, etat=ProduitMachine.PROGRAMME)
        ProduitMachine.objects.create(produit=self.n4, machine=self.s2, etat=ProduitMachine.A_FAIRE)

    def construire(self):
        return matrice.construire_matrice(Produit.objects.all(), list(Machine.objects.all()), ProduitMachine.objects.all())

    def test_une_ligne_par_produit_et_une_case_par_machine_dans_l_ordre(self):
        lignes = self.construire()
        self.assertEqual([ligne["produit"].reference for ligne in lignes], ["N2", "N3", "N4"])
        self.assertEqual([case["machine"].code for case in lignes[0]["cases"]], ["MAD1", "S1", "S2"])
        self.assertEqual([case["etat"] for case in lignes[0]["cases"]],
                         [ProduitMachine.NON_FAISABLE, ProduitMachine.PROGRAMME, matrice.A_SECURISER])
        self.assertEqual([case["etat"] for case in lignes[2]["cases"]], [matrice.VIDE, matrice.VIDE, ProduitMachine.A_FAIRE])

    def test_vues_et_totaux(self):
        lignes = self.construire()
        self.assertEqual([ligne["vues"] for ligne in lignes], [["non_securise", "a_faire"], [], ["sans_machine", "a_faire"]])
        self.assertEqual(matrice.totaux(lignes),
                         {"produits": 3, "programmees": 3, "non_securises": 1, "sans_machine": 1, "a_faire": 2})

    def test_filtres_par_recherche_et_par_vue(self):
        lignes = self.construire()
        self.assertEqual([ligne["produit"].reference for ligne in matrice.filtrer_lignes(lignes, "client x")], ["N3"])
        self.assertEqual([ligne["produit"].reference for ligne in matrice.filtrer_lignes(lignes, vue="a_faire")], ["N2", "N4"])
        self.assertEqual(matrice.filtrer_lignes(lignes, "N3", "a_faire"), [])

    def test_fiches_de_la_ligne_seulement_pour_programme_et_a_faire(self):
        ligne = self.construire()[0]
        self.assertEqual([case["machine"].code for case in ligne["fiches"]], ["S1", "S2"])


class ChangementEtatTests(TestCase):
    def setUp(self):
        self.produit = Produit.objects.create(reference="N2", designation="Produit N2")
        self.machine = Machine.objects.create(code="S1", nom="S1")

    def test_une_case_vide_prend_un_etat_puis_redevient_vide_sans_laisser_de_ligne(self):
        case = ProduitMachine.changer_etat(self.produit, self.machine, ProduitMachine.NON_FAISABLE)
        self.assertEqual(case.etat, ProduitMachine.NON_FAISABLE)
        self.assertIsNone(ProduitMachine.changer_etat(self.produit, self.machine, ""))
        self.assertFalse(ProduitMachine.objects.exists())

    def test_vider_une_fiche_remplie_la_garde_en_possible(self):
        case = ProduitMachine.objects.create(produit=self.produit, machine=self.machine, cadence=300)
        self.assertEqual(ProduitMachine.changer_etat(self.produit, self.machine, "").etat, ProduitMachine.POSSIBLE)
        case.refresh_from_db()
        self.assertEqual(case.cadence, 300)

    def test_etat_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            ProduitMachine.changer_etat(self.produit, self.machine, "bientot")


class DuplicationTests(TestCase):
    def setUp(self):
        self.s1 = Machine.objects.create(code="S1", nom="S1")
        self.s2 = Machine.objects.create(code="S2", nom="S2")
        self.produit = Produit.objects.create(reference="N2", designation="Produit N2", notes="Contrôle visuel")
        self.fiche = ProduitMachine.objects.create(produit=self.produit, machine=self.s1, cadence=480, notes="Dresser la meule")
        self.jeu = Outil.objects.create(code="OUT-N2", nom="Jeu N2")
        self.fiche.outils.add(self.jeu)
        self.huile = creer_article("HUI-01")
        Consommation.objects.create(fabrication=self.fiche, article=self.huile, quantite="1 bidon / semaine")
        Parametre.objects.create(fabrication=self.fiche, libelle="Vitesse meule", valeur="35", unite="m/s", ordre=0)
        Parametre.objects.create(fabrication=self.fiche, libelle="Avance", valeur="140", unite="mm/min", ordre=1)
        self.photo = Document.objects.create(produit=self.produit, fabrication=self.fiche, titre="Réglage",
                                             fichier=ContentFile(b"<svg/>", name="reglage.svg"))
        self.plan = Document.objects.create(produit=self.produit, titre="Plan", fichier=ContentFile(b"%PDF", name="plan.pdf"))

    def test_copie_d_une_fiche_vers_une_autre_machine(self):
        copie = self.fiche.dupliquer_vers_machine(self.s2)
        self.assertEqual((copie.machine, copie.etat, copie.cadence, copie.notes),
                         (self.s2, ProduitMachine.A_FAIRE, 480, "Dresser la meule"))
        self.assertEqual(list(copie.outils.all()), [self.jeu])
        self.assertEqual([str(parametre) for parametre in copie.parametres.all()], ["Vitesse meule : 35 m/s", "Avance : 140 mm/min"])
        self.assertEqual(list(copie.consommations.values_list("article__reference", "quantite")), [("HUI-01", "1 bidon / semaine")])
        # Les photos montrent le réglage de S1 : elles ne suivent pas vers S2.
        self.assertFalse(copie.documents.exists())
        # La fiche d'origine n'a pas bougé.
        self.assertEqual(self.fiche.parametres.count(), 2)

    def test_copie_sur_une_case_deja_marquee_a_faire_et_vide(self):
        ProduitMachine.changer_etat(self.produit, self.s2, ProduitMachine.A_FAIRE)
        copie = self.fiche.dupliquer_vers_machine(self.s2)
        self.assertEqual(copie.parametres.count(), 2)
        self.assertEqual(ProduitMachine.objects.filter(produit=self.produit).count(), 2)

    def test_copie_refusee_sur_une_fiche_deja_remplie_ou_la_meme_machine(self):
        ProduitMachine.objects.create(produit=self.produit, machine=self.s2, cadence=200)
        with self.assertRaises(ValueError):
            self.fiche.dupliquer_vers_machine(self.s2)
        with self.assertRaises(ValueError):
            self.fiche.dupliquer_vers_machine(self.s1)

    def test_copie_sur_une_case_non_faisable_la_rend_a_faire(self):
        ProduitMachine.changer_etat(self.produit, self.s2, ProduitMachine.NON_FAISABLE)
        self.assertEqual(self.fiche.dupliquer_vers_machine(self.s2).etat, ProduitMachine.A_FAIRE)

    def test_duplication_d_un_produit_complet(self):
        ProduitMachine.changer_etat(self.produit, self.s2, ProduitMachine.NON_FAISABLE)
        copie = self.produit.dupliquer("N2B", "Produit N2 variante")
        self.assertEqual((copie.reference, copie.notes), ("N2B", "Contrôle visuel"))
        etats = dict(copie.fabrications.values_list("machine__code", "etat"))
        self.assertEqual(etats, {"S1": ProduitMachine.PROGRAMME, "S2": ProduitMachine.NON_FAISABLE})
        fiche_copiee = copie.fabrications.get(machine=self.s1)
        self.assertEqual(fiche_copiee.parametres.count(), 2)
        self.assertEqual(sorted(copie.documents.values_list("titre", "fabrication__machine__code")),
                         [("Plan", None), ("Réglage", "S1")])
        self.assertEqual(self.produit.fabrications.count(), 2)


class PagesProduitsTests(TestCase):
    def setUp(self):
        self.methode = creer_utilisateur("noel", METHODE)
        self.operateur = creer_utilisateur("operateur", ATELIER)
        self.s1 = Machine.objects.create(code="S1", nom="S1")
        self.s2 = Machine.objects.create(code="S2", nom="S2")
        self.produit = Produit.objects.create(reference="N2", designation="Produit N2")
        self.fiche = ProduitMachine.objects.create(produit=self.produit, machine=self.s1, cadence=480)
        Parametre.objects.create(fabrication=self.fiche, libelle="Vitesse meule", valeur="35", unite="m/s")
        self.huile = creer_article("HUI-01")

    def test_changement_d_etat_depuis_la_matrice_en_json(self):
        self.client.force_login(self.methode)
        reponse = self.client.post("/produits/etat/", {"produit": self.produit.pk, "machine": self.s2.pk, "etat": "a_faire"},
                                   HTTP_ACCEPT="application/json")
        case = ProduitMachine.objects.get(produit=self.produit, machine=self.s2)
        self.assertEqual(reponse.json()["etat"], "a_faire")
        self.assertEqual(reponse.json()["fiche"], case.get_absolute_url())

    def test_l_operateur_consulte_mais_ne_modifie_pas(self):
        self.client.force_login(self.operateur)
        self.assertContains(self.client.get("/produits/"), self.fiche.get_absolute_url())
        self.assertNotContains(self.client.get("/produits/"), "dialogue-case")
        self.assertEqual(self.client.post("/produits/etat/", {"produit": self.produit.pk, "machine": self.s2.pk,
                                                              "etat": "a_faire"}).status_code, 403)
        self.assertEqual(self.client.get(f"/produits/fiche/{self.fiche.pk}/modifier/").status_code, 403)

    def donnees_fiche(self, **autres):
        donnees = {
            "machine": self.s1.pk, "etat": "programme", "cadence": "500", "notes": "Nouvelle note",
            "parametres-TOTAL_FORMS": "3", "parametres-INITIAL_FORMS": "1",
            "parametres-MIN_NUM_FORMS": "0", "parametres-MAX_NUM_FORMS": "1000",
            "parametres-0-id": self.fiche.parametres.get().pk, "parametres-0-fabrication": self.fiche.pk,
            "parametres-0-libelle": "Vitesse meule", "parametres-0-valeur": "33", "parametres-0-unite": "m/s",
            "parametres-1-libelle": "Avance", "parametres-1-valeur": "120", "parametres-1-unite": "mm/min",
            "parametres-2-libelle": "", "parametres-2-valeur": "", "parametres-2-unite": "",
            "consommations-TOTAL_FORMS": "1", "consommations-INITIAL_FORMS": "0",
            "consommations-MIN_NUM_FORMS": "0", "consommations-MAX_NUM_FORMS": "1000",
            "consommations-0-article": self.huile.pk, "consommations-0-quantite": "1 bidon / semaine",
        }
        donnees.update(autres)
        return donnees

    def test_modification_d_une_fiche_avec_parametres_et_consommables(self):
        self.client.force_login(self.methode)
        reponse = self.client.post(f"/produits/fiche/{self.fiche.pk}/modifier/", self.donnees_fiche())
        self.assertRedirects(reponse, self.fiche.get_absolute_url())
        self.fiche.refresh_from_db()
        self.assertEqual(self.fiche.cadence, 500)
        self.assertEqual([(parametre.libelle, parametre.valeur, parametre.ordre) for parametre in self.fiche.parametres.all()],
                         [("Vitesse meule", "33", 0), ("Avance", "120", 1)])
        self.assertEqual(self.fiche.consommations.get().article, self.huile)

    def test_retirer_un_parametre(self):
        self.client.force_login(self.methode)
        self.client.post(f"/produits/fiche/{self.fiche.pk}/modifier/",
                         self.donnees_fiche(**{"parametres-0-DELETE": "on", "parametres-1-libelle": "",
                                             "parametres-1-valeur": "", "parametres-1-unite": ""}))
        self.assertFalse(self.fiche.parametres.exists())

    def test_nouvelle_fiche_reprend_les_parametres_de_la_machine(self):
        self.client.force_login(self.methode)
        autre = Produit.objects.create(reference="N3", designation="Produit N3")
        reponse = self.client.get(f"/produits/{autre.pk}/fiche/nouvelle/", {"machine": self.s1.pk})
        self.assertTrue(reponse.context["parametres_repris"])
        self.assertContains(reponse, 'value="Vitesse meule"')

    def test_nouvelle_fiche_sur_une_case_non_faisable_reprend_la_ligne(self):
        self.client.force_login(self.methode)
        ProduitMachine.changer_etat(self.produit, self.s2, ProduitMachine.NON_FAISABLE)
        donnees = self.donnees_fiche(machine=self.s2.pk, etat="a_faire",
                                     **{"parametres-INITIAL_FORMS": "0", "parametres-0-id": "", "parametres-0-fabrication": ""})
        reponse = self.client.post(f"/produits/{self.produit.pk}/fiche/nouvelle/", donnees)
        case = ProduitMachine.objects.get(produit=self.produit, machine=self.s2)
        self.assertRedirects(reponse, case.get_absolute_url())
        self.assertEqual((case.etat, case.cadence), ("a_faire", 500))

    def test_dupliquer_une_fiche_ouvre_la_copie_a_ajuster(self):
        self.client.force_login(self.methode)
        reponse = self.client.post(f"/produits/fiche/{self.fiche.pk}/dupliquer/", {"machine": self.s2.pk})
        copie = ProduitMachine.objects.get(produit=self.produit, machine=self.s2)
        self.assertRedirects(reponse, f"/produits/fiche/{copie.pk}/modifier/")

    def test_dupliquer_un_produit_refuse_une_reference_existante(self):
        self.client.force_login(self.methode)
        self.client.post(f"/produits/{self.produit.pk}/dupliquer/", {"reference": "n2", "designation": "Doublon"})
        self.assertEqual(Produit.objects.count(), 1)
        reponse = self.client.post(f"/produits/{self.produit.pk}/dupliquer/", {"reference": "N2B", "designation": "Variante"})
        self.assertRedirects(reponse, Produit.objects.get(reference="N2B").get_absolute_url())

    def test_creation_et_modification_d_un_produit(self):
        self.client.force_login(self.methode)
        reponse = self.client.post("/produits/nouveau/", {"reference": "N14", "designation": "Produit N14", "client": "", "notes": ""})
        nouveau = Produit.objects.get(reference="N14")
        self.assertRedirects(reponse, nouveau.get_absolute_url())
        self.client.post(f"/produits/{nouveau.pk}/modifier/", {"reference": "N14", "designation": "Renommé", "client": "", "notes": ""})
        nouveau.refresh_from_db()
        self.assertEqual(nouveau.designation, "Renommé")

    def test_depot_affichage_et_retrait_d_une_photo(self):
        self.client.force_login(self.methode)
        image = SimpleUploadedFile("reglage pince.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        self.client.post(f"/produits/fiche/{self.fiche.pk}/documents/", {"titre": "Réglage pince", "fichier": image, "portee": "fiche"})
        photo = Document.objects.get()
        self.assertEqual(photo.fabrication, self.fiche)
        self.assertEqual(photo.ajoute_par, self.methode)
        self.assertContains(self.client.get(self.fiche.get_absolute_url()), f'src="{photo.get_absolute_url()}"')
        self.client.force_login(self.operateur)
        reponse = self.client.get(photo.get_absolute_url())
        self.assertEqual(b"".join(reponse.streaming_content), b"\x89PNG\r\n\x1a\n")
        self.client.force_login(self.methode)
        chemin = photo.fichier.name
        self.client.post(f"/produits/documents/{photo.pk}/supprimer/", {"retour": self.fiche.get_absolute_url()})
        self.assertFalse(Document.objects.exists())
        self.assertFalse(photo.fichier.storage.exists(chemin))

    def test_le_regleur_ajoute_des_photos_mais_pas_l_operateur(self):
        self.client.force_login(creer_utilisateur("regleur", REGLEUR))
        self.assertContains(self.client.get(self.fiche.get_absolute_url()), "Ajouter une photo ou un document")
        self.assertNotContains(self.client.get(self.fiche.get_absolute_url()), "Modifier la fiche")
        image = SimpleUploadedFile("pince.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        self.client.post(f"/produits/fiche/{self.fiche.pk}/documents/", {"titre": "Pince", "fichier": image, "portee": "fiche"})
        photo = Document.objects.get()
        self.client.force_login(self.operateur)
        self.assertNotContains(self.client.get(self.fiche.get_absolute_url()), "Ajouter une photo ou un document")
        image = SimpleUploadedFile("autre.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")
        reponse = self.client.post(f"/produits/fiche/{self.fiche.pk}/documents/", {"titre": "Autre", "fichier": image, "portee": "fiche"})
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(self.client.post(f"/produits/documents/{photo.pk}/supprimer/").status_code, 403)
        self.assertEqual(Document.objects.count(), 1)

    def test_un_fichier_partage_par_une_copie_n_est_pas_efface(self):
        plan = Document.objects.create(produit=self.produit, titre="Plan", fichier=ContentFile(b"%PDF", name="plan.pdf"))
        copie = plan.copier_vers(self.produit, self.fiche)
        self.client.force_login(self.methode)
        self.client.post(f"/produits/documents/{plan.pk}/supprimer/")
        self.assertTrue(copie.fichier.storage.exists(copie.fichier.name))

    def test_extension_refusee(self):
        self.client.force_login(self.methode)
        programme = SimpleUploadedFile("outil.exe", b"MZ", content_type="application/octet-stream")
        self.client.post(f"/produits/fiche/{self.fiche.pk}/documents/", {"titre": "Programme", "fichier": programme, "portee": "fiche"})
        self.assertFalse(Document.objects.exists())

    def test_document_du_produit_visible_sur_toutes_ses_fiches(self):
        autre_fiche = ProduitMachine.objects.create(produit=self.produit, machine=self.s2)
        self.client.force_login(self.methode)
        plan = SimpleUploadedFile("plan.pdf", b"%PDF-1.4", content_type="application/pdf")
        self.client.post(f"/produits/fiche/{self.fiche.pk}/documents/", {"titre": "Plan N2", "fichier": plan, "portee": "produit"})
        self.client.get(self.fiche.get_absolute_url())  # consomme le message de confirmation
        self.assertContains(self.client.get(autre_fiche.get_absolute_url()), "Plan N2</a>")
