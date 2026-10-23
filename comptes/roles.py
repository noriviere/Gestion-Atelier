"""Les trois niveaux d'accès de l'application, portés par des groupes Django."""

ADMIN = "Admin"
METHODE = "Méthode et management"
ATELIER = "Régleur et opérateur"

GROUPES = [ADMIN, METHODE, ATELIER]


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


def peut_mouvementer(user):
    """Tous les profils peuvent saisir une sortie de stock ou un comptage d'inventaire."""
    return profil(user) is not None


APPS_METIER = ["inventaire", "outillage", "produits"]


def configurer_permissions(**kwargs):
    """Méthode et management : droits complets sur les données métier, via l'admin Django.

    Régleur et opérateur : lecture, plus la saisie des mouvements de stock.
    """
    from django.contrib.auth.models import Group, Permission

    metier = Permission.objects.filter(content_type__app_label__in=APPS_METIER)
    methode, _ = Group.objects.get_or_create(name=METHODE)
    methode.permissions.set(metier)
    atelier, _ = Group.objects.get_or_create(name=ATELIER)
    atelier.permissions.set(
        metier.filter(codename__startswith="view_") | metier.filter(codename="add_mouvement")
    )
    Group.objects.get_or_create(name=ADMIN)
