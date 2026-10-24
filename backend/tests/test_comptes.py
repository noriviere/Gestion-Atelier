"""Les profils, leurs droits par sous-fonction et la page « Droits »."""
from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase

from comptes import roles
from comptes.droits import DEFAUTS, TOUS_LES_CODES
from comptes.menu import entrees_menu
from produits.models import Machine

from .fabriques import creer_utilisateur


def groupe(nom):
    return Group.objects.get(name=nom)


class ProfilsTests(TestCase):
    def test_superutilisateur_est_admin_et_a_tout(self):
        administrateur = creer_utilisateur("admin", superutilisateur=True)
        self.assertEqual(roles.profil(administrateur), roles.ADMIN)
        self.assertEqual(roles.droits(administrateur), frozenset(TOUS_LES_CODES))

    def test_groupe_admin_a_tout_sans_etre_superutilisateur(self):
        self.assertEqual(roles.droits(creer_utilisateur("admin2", roles.ADMIN)), frozenset(TOUS_LES_CODES))

    def test_methode_modifie_tout_mais_ne_gere_pas_les_droits(self):
        methodiste = creer_utilisateur("methode", roles.METHODE)
        self.assertTrue(roles.a_le_droit(methodiste, "stock_articles"))
        self.assertTrue(roles.a_le_droit(methodiste, "produits_modifier"))
        self.assertFalse(roles.a_le_droit(methodiste, "admin_droits"))

    def test_intendant_gere_commandes_et_stock_sans_toucher_aux_produits(self):
        intendante = creer_utilisateur("intendante", roles.INTENDANT)
        for code in ("commandes_preparer", "commandes_receptionner", "stock_comptages", "stock_articles",
                     "stock_fournisseurs"):
            self.assertTrue(roles.a_le_droit(intendante, code), code)
        self.assertFalse(roles.a_le_droit(intendante, "produits_modifier"))
        self.assertFalse(roles.a_le_droit(intendante, "produits_documents_voir"))

    def test_regleur_a_plus_de_droits_que_l_operateur(self):
        regleur = creer_utilisateur("regleur", roles.REGLEUR)
        operateur = creer_utilisateur("operateur", roles.OPERATEUR)
        self.assertGreater(roles.droits(regleur), roles.droits(operateur))
        self.assertTrue(roles.a_le_droit(regleur, "produits_documents_voir"))
        self.assertTrue(roles.a_le_droit(regleur, "produits_documents_gerer"))
        self.assertTrue(roles.a_le_droit(regleur, "produits_reglages"))
        self.assertFalse(roles.a_le_droit(operateur, "produits_documents_voir"))

    def test_operateur_sort_du_stock_sans_compter_ni_commander(self):
        operateur = creer_utilisateur("operateur", roles.OPERATEUR)
        self.assertTrue(roles.a_le_droit(operateur, "stock_mouvements"))
        self.assertFalse(roles.a_le_droit(operateur, "stock_comptages"))
        self.assertFalse(roles.a_le_droit(operateur, "commandes_preparer"))

    def test_plusieurs_profils_cumulent_leurs_droits_et_affichent_le_plus_eleve(self):
        compte = creer_utilisateur("double", roles.OPERATEUR)
        compte.groups.add(groupe(roles.INTENDANT))
        self.assertEqual(roles.profil(compte), roles.INTENDANT)
        self.assertEqual(roles.droits(compte), frozenset(DEFAUTS[roles.INTENDANT]) | frozenset(DEFAUTS[roles.OPERATEUR]))

    def test_sans_groupe_ni_connexion_aucun_droit(self):
        sans_profil = creer_utilisateur("inconnu")
        self.assertIsNone(roles.profil(sans_profil))
        self.assertEqual(roles.droits(sans_profil), frozenset())
        self.assertIsNone(roles.profil(AnonymousUser()))
        self.assertFalse(roles.a_le_droit(AnonymousUser(), "stock_consulter"))

    def test_l_ancien_groupe_commun_devient_operateur_avec_ses_membres(self):
        Group.objects.filter(name=roles.OPERATEUR).update(name=roles.ANCIEN_NOM_ATELIER)
        ancien = creer_utilisateur("ancien", roles.ANCIEN_NOM_ATELIER)
        roles.configurer_permissions()
        self.assertEqual(roles.profil(ancien), roles.OPERATEUR)
        self.assertFalse(Group.objects.filter(name=roles.ANCIEN_NOM_ATELIER).exists())

    def test_droit_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            roles.a_le_droit(creer_utilisateur("methode", roles.METHODE), "stock_n_importe_quoi")


class ReglageDesDroitsTests(TestCase):
    def test_enregistrer_remplace_les_droits_et_les_permissions_django(self):
        roles.enregistrer_droits({groupe(roles.OPERATEUR): {"stock_consulter", "outillage_modifier"}})
        operateur = creer_utilisateur("operateur", roles.OPERATEUR)
        self.assertEqual(roles.droits(operateur), {"stock_consulter", "outillage_modifier"})
        self.assertTrue(operateur.has_perm("outillage.change_outil"))
        self.assertFalse(operateur.has_perm("inventaire.add_mouvement"))

    def test_codes_inconnus_ignores(self):
        roles.enregistrer_droits({groupe(roles.OPERATEUR): {"stock_consulter", "pirate"}})
        self.assertEqual(set(groupe(roles.OPERATEUR).droits.values_list("code", flat=True)), {"stock_consulter"})

    def test_une_nouvelle_migration_garde_les_reglages_sauf_reinitialisation(self):
        roles.enregistrer_droits({groupe(roles.REGLEUR): {"stock_consulter"}})
        roles.configurer_permissions()
        self.assertEqual(set(groupe(roles.REGLEUR).droits.values_list("code", flat=True)), {"stock_consulter"})
        roles.configurer_permissions(reinitialiser=True)
        self.assertEqual(set(groupe(roles.REGLEUR).droits.values_list("code", flat=True)), set(DEFAUTS[roles.REGLEUR]))


class PermissionsDjangoTests(TestCase):
    def test_operateur_ne_peut_que_consulter_et_saisir_des_mouvements(self):
        operateur = creer_utilisateur("operateur", roles.OPERATEUR)
        self.assertTrue(operateur.has_perm("inventaire.view_article"))
        self.assertTrue(operateur.has_perm("inventaire.add_mouvement"))
        self.assertFalse(operateur.has_perm("inventaire.change_article"))
        self.assertFalse(operateur.has_perm("produits.delete_produit"))
        self.assertFalse(roles.acces_parametrage(operateur))

    def test_methode_a_tous_les_droits_metier_mais_pas_sur_les_comptes(self):
        methodiste = creer_utilisateur("methode", roles.METHODE)
        self.assertTrue(methodiste.has_perm("outillage.change_outil"))
        self.assertTrue(methodiste.has_perm("produits.delete_produitmachine"))
        self.assertFalse(methodiste.has_perm("auth.change_user"))

    def test_intendant_parametre_articles_et_commandes_mais_pas_les_produits(self):
        intendante = creer_utilisateur("intendante", roles.INTENDANT)
        self.client.force_login(intendante)
        self.assertEqual(self.client.get("/admin/inventaire/article/").status_code, 200)
        self.assertEqual(self.client.get("/admin/commandes/commande/").status_code, 200)
        self.assertEqual(self.client.get("/admin/produits/produit/add/").status_code, 403)


class PageDroitsTests(TestCase):
    def setUp(self):
        self.client.force_login(creer_utilisateur("admin", superutilisateur=True))

    def test_reservee_au_droit_admin_droits(self):
        self.assertEqual(self.client.get("/droits/").status_code, 200)
        self.client.force_login(creer_utilisateur("methode", roles.METHODE))
        self.assertEqual(self.client.get("/droits/").status_code, 403)
        self.assertNotContains(self.client.get("/"), 'href="/droits/"')

    def test_enregistrer_les_droits_des_profils(self):
        regleur = groupe(roles.REGLEUR)
        donnees = {"formulaire": "droits", f"droits_{regleur.pk}": ["stock_consulter", "commandes_preparer"]}
        for nom in (roles.METHODE, roles.INTENDANT, roles.OPERATEUR):
            donnees[f"droits_{groupe(nom).pk}"] = DEFAUTS[nom]
        self.assertRedirects(self.client.post("/droits/", donnees), "/droits/")
        self.assertEqual(set(regleur.droits.values_list("code", flat=True)), {"stock_consulter", "commandes_preparer"})
        self.assertEqual(set(groupe(roles.INTENDANT).droits.values_list("code", flat=True)), set(DEFAUTS[roles.INTENDANT]))

    def test_changer_le_profil_d_un_compte(self):
        compte = creer_utilisateur("nouveau", roles.OPERATEUR)
        autre_groupe = Group.objects.create(name="Groupe hors profils")
        compte.groups.add(autre_groupe)
        administrateur = User.objects.get(username="admin")
        self.client.post("/droits/", {"formulaire": "comptes", f"profil_{compte.pk}": groupe(roles.REGLEUR).pk,
                                      f"profil_{administrateur.pk}": ""})
        self.assertEqual(set(compte.groups.all()), {groupe(roles.REGLEUR), autre_groupe})
        administrateur.refresh_from_db()
        self.assertTrue(administrateur.is_superuser)

    def test_retirer_un_bloc_ferme_ses_pages_et_son_menu(self):
        roles.enregistrer_droits({groupe(roles.OPERATEUR): set(DEFAUTS[roles.OPERATEUR]) - {"produits_consulter"}})
        self.client.force_login(creer_utilisateur("operateur", roles.OPERATEUR))
        self.assertEqual(self.client.get("/produits/").status_code, 403)
        machine = Machine.objects.create(code="S1")
        self.assertEqual(self.client.get(f"/produits/machines/{machine.pk}/").status_code, 403)
        self.assertNotContains(self.client.get("/"), 'href="/produits/"')
        self.assertEqual(self.client.get("/outils/").status_code, 200)


class MenuTests(TestCase):
    @staticmethod
    def libelles(entrees):
        return [entree["libelle"] for entree in entrees]

    def test_atelier_voit_les_fiches_d_abord_et_pas_les_commandes(self):
        operateur = creer_utilisateur("operateur", roles.ATELIER)
        self.assertEqual(
            self.libelles(entrees_menu(operateur, "accueil")),
            ["Accueil", "Produits et machines", "Outillage", "Stock", "Inventaires", "Commandes"],
        )

    def test_bureau_voit_toutes_les_entrees(self):
        methodiste = creer_utilisateur("methode", roles.METHODE)
        self.assertIn("À commander", self.libelles(entrees_menu(methodiste, "accueil")))

    def test_entree_courante_couvre_les_pages_de_detail(self):
        methodiste = creer_utilisateur("methode", roles.METHODE)
        actives = [entree["libelle"] for entree in entrees_menu(methodiste, "fiche") if entree["actif"]]
        self.assertEqual(actives, ["Produits et machines"])
