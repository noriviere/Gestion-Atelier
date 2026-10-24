from django.urls import path

from . import views

urlpatterns = [
    path("", views.commandes, name="commandes"),
    path("<int:pk>/", views.commande, name="commande"),
    path("creer/<int:fournisseur_pk>/", views.creer_commande, name="creer_commande"),
]
