from django.conf import settings

from . import roles
from .menu import entrees_menu


def profil(request):
    page_courante = request.resolver_match.url_name if request.resolver_match else None
    return {
        "entrees_menu": entrees_menu(request.user, page_courante) if request.user.is_authenticated else [],
        "profil": roles.profil(request.user),
        "peut_modifier": roles.peut_modifier(request.user),
        "peut_mouvementer": roles.peut_mouvementer(request.user),
        "peut_documenter": roles.peut_documenter(request.user),
        "demo_statique": settings.DEMO_STATIQUE,
    }
