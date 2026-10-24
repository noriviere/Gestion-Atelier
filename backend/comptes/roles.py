"""Les profils de l'application, portés par des groupes Django, et leurs droits."""
from django.db import transaction

from .droits import BLOCS, DEFAUTS, FONCTIONS, TOUS_LES_CODES

ADMIN = "Admin"
METHODE = "Méthode et management"
INTENDANT = "Intendant"
REGLEUR = "Régleur"
OPERATEUR = "Opérateur"
# Nom historique du profil atelier, gardé pour le code qui s'en sert : c'est le profil opérateur.
ATELIER = OPERATEUR
ANCIEN_NOM_ATELIER = "Régleur et opérateur"

# Du plus haut au plus bas : un utilisateur dans plusieurs groupes affiche le profil le plus élevé.
GROUPES = [ADMIN, METHODE, INTENDANT, REGLEUR, OPERATEUR]
# Profils dont les droits se règlent sur la page « Droits » (Admin a toujours tout).
PROFILS_REGLABLES = [METHODE, INTENDANT, REGLEUR, OPERATEUR]


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


def droits(user):
    """Ensemble des codes de sous-fonctions de l'utilisateur, mis en cache sur l'objet user."""
    if not user.is_authenticated:
        return frozenset()
    if not hasattr(user, "_droits_atelier"):
        from .models import Droit

        if user.is_superuser or user.groups.filter(name=ADMIN).exists():
            codes = TOUS_LES_CODES
        else:
            codes = Droit.objects.filter(profil__user=user).values_list("code", flat=True)
        user._droits_atelier = frozenset(codes)
    return user._droits_atelier


def a_le_droit(user, code):
    if code not in FONCTIONS:
        raise ValueError(f"Droit inconnu : {code}")
    return code in droits(user)


def acces_parametrage(user):
    """L'administration Django s'ouvre dès qu'une sous-fonction permet d'y modifier des données."""
    return any(".change_" in permission for code in droits(user) for permission in FONCTIONS[code].permissions_django)


def tableau_des_droits():
    """Pour la page « Droits » : les blocs et, pour chaque profil réglable, ses codes accordés."""
    from django.contrib.auth.models import Group

    profils = list(Group.objects.filter(name__in=PROFILS_REGLABLES).prefetch_related("droits"))
    profils.sort(key=lambda groupe: PROFILS_REGLABLES.index(groupe.name))
    return BLOCS, [(groupe, {droit.code for droit in groupe.droits.all()}) for groupe in profils]


@transaction.atomic
def enregistrer_droits(codes_par_profil):
    """Remplace les droits des profils donnés ({Group: codes}) et met à jour leurs permissions Django."""
    from .models import Droit

    for groupe, codes in codes_par_profil.items():
        codes = {code for code in codes if code in FONCTIONS}
        groupe.droits.exclude(code__in=codes).delete()
        deja = set(groupe.droits.values_list("code", flat=True))
        Droit.objects.bulk_create([Droit(profil=groupe, code=code) for code in codes - deja])
        synchroniser_permissions(groupe)


def synchroniser_permissions(groupe):
    """Les permissions Django du groupe découlent de ses droits (écrans de l'administration)."""
    from django.contrib.auth.models import Permission

    noms = {
        nom
        for code in groupe.droits.values_list("code", flat=True)
        if code in FONCTIONS
        for nom in FONCTIONS[code].permissions_django
    }
    permissions = Permission.objects.none()
    for nom in noms:
        app, codename = nom.split(".")
        permissions |= Permission.objects.filter(content_type__app_label=app, codename=codename)
    groupe.permissions.set(permissions)


def configurer_permissions(reinitialiser=False, **kwargs):
    """Crée les profils manquants avec leurs droits de départ, puis aligne les permissions Django.

    Les droits déjà réglés sur la page « Droits » ne sont pas touchés, sauf avec reinitialiser=True.
    """
    from django.contrib.auth.models import Group

    from .models import Droit

    # L'ancien groupe commun « Régleur et opérateur » devient le groupe Opérateur, avec ses membres.
    if not Group.objects.filter(name=OPERATEUR).exists():
        Group.objects.filter(name=ANCIEN_NOM_ATELIER).update(name=OPERATEUR)
    Group.objects.get_or_create(name=ADMIN)
    for nom in PROFILS_REGLABLES:
        groupe, cree = Group.objects.get_or_create(name=nom)
        if cree or reinitialiser:
            groupe.droits.all().delete()
            Droit.objects.bulk_create([Droit(profil=groupe, code=code) for code in DEFAUTS[nom]])
        synchroniser_permissions(groupe)
