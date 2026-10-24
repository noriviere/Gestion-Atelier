from django.conf import settings

from . import roles


def profil(request):
    return {
        "profil": roles.profil(request.user),
        "peut_modifier": roles.peut_modifier(request.user),
        "peut_mouvementer": roles.peut_mouvementer(request.user),
        "peut_compter": roles.peut_compter(request.user),
        "demo_statique": settings.DEMO_STATIQUE,
    }
