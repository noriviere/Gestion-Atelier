"""Les niveaux d'accès de l'application, portés par des groupes Django."""

ADMIN = "Admin"
METHODE = "Méthode et management"
INTENDANT = "Intendant"
REGLEUR = "Régleur"
OPERATEUR = "Opérateur"
# Nom historique du profil atelier, gardé pour le code qui s'en sert : c'est le profil opérateur.
ATELIER = OPERATEUR
ANCIEN_NOM_ATELIER = "Régleur et opérateur"

# Du plus haut au plus bas : un utilisateur dans plusieurs groupes a le profil le plus élevé.
GROUPES = [ADMIN, METHODE, INTENDANT, REGLEUR, OPERATEUR]


def profil(user):
    """Renvoie le nom du profil le plus élevé de l'utilisateur, ou None."""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return ADMIN
    noms = set(user.groups.values_list("name", flat=True))
    for nom in GROUPES:
        if nom in noms:
            return nom
    return None


def peut_modifier(user):
    """Admin et Méthode et management créent et modifient les données de référence."""
    return profil(user) in (ADMIN, METHODE)


def peut_documenter(user):
    """Ajouter ou retirer les photos et documents des fiches : Admin, Méthode et management, et les régleurs."""
    return profil(user) in (ADMIN, METHODE, REGLEUR)


def peut_mouvementer(user):
    """Tous les profils peuvent saisir une sortie ou une entrée de stock."""
    return profil(user) is not None


def peut_compter(user):
    """Les comptages d'inventaire corrigent le stock : réservés à l'intendant, avec Admin et Méthode et management."""
    return profil(user) in (ADMIN, METHODE, INTENDANT)


APPS_METIER = ["inventaire", "outillage", "produits", "commandes"]


def configurer_permissions(**kwargs):
    """Méthode et management : droits complets sur les données métier, via l'admin Django.

    Intendant : lecture, saisie des mouvements de stock et des comptages d'inventaire.
    Régleur : lecture, saisie des mouvements de stock, photos et documents des fiches.
    Opérateur : lecture, plus la saisie des mouvements de stock.
    Les comptages d'inventaire, propres à l'intendant, sont contrôlés par peut_compter.
    """
    from django.contrib.auth.models import Group, Permission

    # L'ancien groupe commun « Régleur et opérateur » devient le groupe Opérateur, avec ses membres.
    if not Group.objects.filter(name=OPERATEUR).exists():
        Group.objects.filter(name=ANCIEN_NOM_ATELIER).update(name=OPERATEUR)

    metier = Permission.objects.filter(content_type__app_label__in=APPS_METIER)
    methode, _ = Group.objects.get_or_create(name=METHODE)
    methode.permissions.set(metier)
    lecture_et_mouvements = metier.filter(codename__startswith="view_") | metier.filter(codename="add_mouvement")
    for nom in (INTENDANT, OPERATEUR):
        groupe, _ = Group.objects.get_or_create(name=nom)
        groupe.permissions.set(lecture_et_mouvements)
    regleur, _ = Group.objects.get_or_create(name=REGLEUR)
    regleur.permissions.set(lecture_et_mouvements | metier.filter(codename__in=["add_document", "delete_document"]))
    Group.objects.get_or_create(name=ADMIN)
