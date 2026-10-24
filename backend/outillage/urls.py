from django.urls import path

from . import views

urlpatterns = [
    path("", views.outils, name="outils"),
    path("nouveau/", views.nouvel_outil, name="nouvel_outil"),
    path("<int:pk>/", views.outil, name="outil"),
    path("<int:pk>/modifier/", views.modifier_outil, name="modifier_outil"),
    path("<int:pk>/supprimer/", views.supprimer_outil, name="supprimer_outil"),
    path("<int:pk>/sortie/", views.sortie_piece, name="sortie_piece"),
]
