from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from . import roles
from .droits import PAGES


class ConnexionObligatoireMiddleware:
    """Toute l'application demande une connexion, sauf la page de connexion, l'admin et les fichiers statiques."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        page_connexion = reverse(settings.LOGIN_URL)
        chemins_publics = (page_connexion, "/admin/", "/" + settings.STATIC_URL.lstrip("/"))
        if not request.user.is_authenticated and not request.path.startswith(chemins_publics):
            # Adresse complète et encodée : on revient sur la page demandée avec ses filtres.
            return redirect_to_login(request.get_full_path(), page_connexion)
        return self.get_response(request)


class DroitsDeConsultationMiddleware:
    """Chaque page de consultation demande la sous-fonction indiquée dans droits.PAGES."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, vue, args, kwargs):
        code = PAGES.get(request.resolver_match.url_name)
        if code and request.user.is_authenticated and not roles.a_le_droit(request.user, code):
            raise PermissionDenied
        return None
