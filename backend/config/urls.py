from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from comptes import roles
from comptes import views as comptes_views

admin.site.site_header = "Gestion Atelier – administration"
admin.site.site_title = "Gestion Atelier"
# Le paramétrage s'ouvre selon les droits du profil (page « Droits »), pas selon la case « équipe » du compte.
admin.site.has_permission = lambda request: request.user.is_active and (
    request.user.is_staff or roles.acces_parametrage(request.user)
)

urlpatterns = [
    path("connexion/", auth_views.LoginView.as_view(template_name="connexion.html"), name="connexion"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="deconnexion"),
    path("admin/", admin.site.urls),
    path("droits/", comptes_views.droits, name="droits"),
    path("aide/", include("aide.urls")),
    path("", include("inventaire.urls")),
    path("outils/", include("outillage.urls")),
    path("produits/", include("produits.urls")),
    path("commandes/", include("commandes.urls")),
]
