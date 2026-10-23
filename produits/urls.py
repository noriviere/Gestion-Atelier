from django.urls import path

from . import views

urlpatterns = [
    path("", views.produits, name="produits"),
    path("<int:pk>/", views.produit, name="produit"),
    path("fiche/<int:pk>/", views.fiche, name="fiche"),
    path("machines/", views.machines, name="machines"),
    path("machines/<int:pk>/", views.machine, name="machine"),
]
