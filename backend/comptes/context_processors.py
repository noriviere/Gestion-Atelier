from django.conf import settings

from . import roles
from .droits import TOUS_LES_CODES
from .menu import entrees_menu


def profil(request):
    page_courante = request.resolver_match.url_name if request.resolver_match else None
    droits_utilisateur = roles.droits(request.user)
    return {
        "entrees_menu": entrees_menu(request.user, page_courante) if request.user.is_authenticated else [],
        "profil": roles.profil(request.user),
        # droits.<code> dans les gabarits, par exemple {% if droits.stock_mouvements %}.
        "droits": {code: code in droits_utilisateur for code in TOUS_LES_CODES},
        "acces_parametrage": roles.acces_parametrage(request.user),
        "demo_statique": settings.DEMO_STATIQUE,
        # Les identifiants de démo ne s'affichent pas sur une installation réelle (DEBUG coupé).
        "comptes_demo_visibles": settings.DEBUG or settings.DEMO_STATIQUE,
    }
