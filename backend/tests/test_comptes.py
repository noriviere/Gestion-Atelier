"""Les niveaux d'accès et leurs droits."""
from django.contrib.auth.models import AnonymousUser, Group
from django.test import TestCase

from comptes import roles
from comptes.menu import entrees_menu

from .fabriques import creer_utilisateur


class ProfilsTests(TestCase):
    def test_superutilisateur_est_admin(self):
        administrateur = creer_utilisateur("admin", superutilisateur=True)
        self.assertEqual(roles.profil(administrateur), roles.ADMIN)
        self.assertTrue(roles.peut_modifier(administrateur))

    def test_methode_peut_modifier_et_mouvementer(self):
        methodiste = creer_utilisateur("methode", roles.METHODE)
        self.assertEqual(roles.profil(methodiste), roles.METHODE)
        self.assertTrue(roles.peut_modifier(methodiste))
        self.assertTrue(roles.peut_mouvementer(methodiste))

    def test_atelier_mouvemente_sans_modifier(self):
        operateur = creer_utilisateur("operateur", roles.ATELIER)
        self.assertFalse(roles.peut_modifier(operateur))
        self.assertTrue(roles.peut_mouvementer(operateur))

    def test_seuls_intendant_methode_et_admin_comptent_les_inventaires(self):
        self.assertTrue(roles.peut_compter(creer_utilisateur("intendante", roles.INTENDANT)))
        self.assertTrue(roles.peut_compter(creer_utilisateur("methode", roles.METHODE)))
        self.assertTrue(roles.peut_compter(creer_utilisateur("admin", superutilisateur=True)))
        self.assertFalse(roles.peut_compter(creer_utilisateur("operateur", roles.ATELIER)))
        self.assertFalse(roles.peut_compter(creer_utilisateur("inconnu")))

    def test_intendant_mouvemente_sans_modifier(self):
        intendante = creer_utilisateur("intendante", roles.INTENDANT)
        self.assertEqual(roles.profil(intendante), roles.INTENDANT)
        self.assertTrue(roles.peut_mouvementer(intendante))
        self.assertFalse(roles.peut_modifier(intendante))

    def test_regleur_au_dessus_de_l_operateur_pour_les_documents(self):
        regleur = creer_utilisateur("regleur", roles.REGLEUR)
        operateur = creer_utilisateur("operateur", roles.OPERATEUR)
        self.assertEqual(roles.profil(regleur), roles.REGLEUR)
        self.assertTrue(roles.peut_documenter(regleur))
        self.assertFalse(roles.peut_modifier(regleur))
        self.assertFalse(roles.peut_documenter(operateur))
        self.assertTrue(roles.peut_documenter(creer_utilisateur("methode", roles.METHODE)))
        operateur.groups.add(Group.objects.get(name=roles.REGLEUR))
        self.assertEqual(roles.profil(operateur), roles.REGLEUR)

    def test_l_ancien_groupe_commun_devient_operateur_avec_ses_membres(self):
        Group.objects.filter(name=roles.OPERATEUR).update(name=roles.ANCIEN_NOM_ATELIER)
        ancien = creer_utilisateur("ancien", roles.ANCIEN_NOM_ATELIER)
        roles.configurer_permissions()
        self.assertEqual(roles.profil(ancien), roles.OPERATEUR)
        self.assertFalse(Group.objects.filter(name=roles.ANCIEN_NOM_ATELIER).exists())

    def test_le_profil_le_plus_eleve_l_emporte(self):
        chef = creer_utilisateur("chef", roles.ATELIER)
        chef.groups.add(Group.objects.get(name=roles.METHODE))
        self.assertEqual(roles.profil(chef), roles.METHODE)

    def test_sans_groupe_ni_connexion_aucun_droit(self):
        sans_profil = creer_utilisateur("inconnu")
        self.assertIsNone(roles.profil(sans_profil))
        self.assertFalse(roles.peut_mouvementer(sans_profil))
        self.assertIsNone(roles.profil(AnonymousUser()))


class PermissionsDesGroupesTests(TestCase):
    def test_atelier_ne_peut_que_consulter_et_saisir_des_mouvements(self):
        operateur = creer_utilisateur("operateur", roles.ATELIER)
        self.assertTrue(operateur.has_perm("inventaire.view_article"))
        self.assertTrue(operateur.has_perm("inventaire.add_mouvement"))
        self.assertFalse(operateur.has_perm("inventaire.change_article"))
        self.assertFalse(operateur.has_perm("produits.delete_produit"))

    def test_intendant_consulte_et_saisit_des_mouvements(self):
        intendante = creer_utilisateur("intendante", roles.INTENDANT)
        self.assertTrue(intendante.has_perm("inventaire.add_mouvement"))
        self.assertFalse(intendante.has_perm("inventaire.change_article"))

    def test_methode_a_tous_les_droits_metier_mais_pas_sur_les_comptes(self):
        methodiste = creer_utilisateur("methode", roles.METHODE)
        self.assertTrue(methodiste.has_perm("outillage.change_outil"))
        self.assertTrue(methodiste.has_perm("produits.delete_produitmachine"))
        self.assertFalse(methodiste.has_perm("auth.change_user"))


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
