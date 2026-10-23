from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ConnexionObligatoireMiddleware:
    """Toute l'application demande une connexion, sauf la page de connexion, l'admin et les fichiers statiques."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        page_connexion = reverse(settings.LOGIN_URL)
        chemins_publics = (page_connexion, "/admin/", "/" + settings.STATIC_URL.lstrip("/"))
        if not request.user.is_authenticated and not request.path.startswith(chemins_publics):
            return redirect(f"{page_connexion}?next={request.path}")
        return self.get_response(request)
