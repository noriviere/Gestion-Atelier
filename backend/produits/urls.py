from django.urls import path

from . import views

urlpatterns = [
    path("", views.produits, name="produits"),
    path("etat/", views.changer_etat, name="changer_etat"),
    path("nouveau/", views.modifier_produit, name="nouveau_produit"),
    path("<int:pk>/", views.produit, name="produit"),
    path("<int:pk>/modifier/", views.modifier_produit, name="modifier_produit"),
    path("<int:pk>/dupliquer/", views.dupliquer_produit, name="dupliquer_produit"),
    path("<int:produit_pk>/fiche/nouvelle/", views.modifier_fiche, name="nouvelle_fiche"),
    path("fiche/<int:pk>/", views.fiche, name="fiche"),
    path("fiche/<int:pk>/modifier/", views.modifier_fiche, name="modifier_fiche"),
    path("fiche/<int:pk>/dupliquer/", views.dupliquer_fiche, name="dupliquer_fiche"),
    path("fiche/<int:pk>/documents/", views.ajouter_document, name="ajouter_document"),
    path("documents/<int:pk>/supprimer/", views.supprimer_document, name="supprimer_document"),
    path("documents/<int:pk>/<str:nom>", views.document, name="document"),
    path("machines/<int:pk>/", views.machine, name="machine"),
]
