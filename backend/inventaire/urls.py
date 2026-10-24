from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("articles/", views.articles, name="articles"),
    path("articles/<int:pk>/", views.article, name="article"),
    path("a-commander/", views.a_commander, name="a_commander"),
    path("inventaires/", views.inventaires, name="inventaires"),
    path("inventaires/ecarts/", views.ecarts, name="ecarts"),
    path("inventaires/<int:pk>/", views.comptage, name="comptage"),
    path("inventaires/<int:pk>/feuille/", views.feuille_comptage, name="feuille_comptage"),
]
