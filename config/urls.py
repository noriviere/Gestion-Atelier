from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

admin.site.site_header = "Gestion Atelier – administration"
admin.site.site_title = "Gestion Atelier"

urlpatterns = [
    path("connexion/", auth_views.LoginView.as_view(template_name="connexion.html"), name="connexion"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="deconnexion"),
    path("admin/", admin.site.urls),
    path("", include("inventaire.urls")),
    path("outils/", include("outillage.urls")),
    path("produits/", include("produits.urls")),
]
