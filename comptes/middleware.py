from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class ConnexionObligatoireMiddleware:
    """Toute l'application demande une connexion, sauf la page de connexion et l'admin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        libres = (reverse(settings.LOGIN_URL), "/admin/", settings.STATIC_URL if settings.STATIC_URL.startswith("/") else "/" + settings.STATIC_URL)
        if not request.user.is_authenticated and not request.path.startswith(libres):
            return redirect(f"{reverse(settings.LOGIN_URL)}?next={request.path}")
        return self.get_response(request)
