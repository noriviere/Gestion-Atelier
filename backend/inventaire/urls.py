from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("recherche/", views.recherche, name="recherche"),
    path("articles/", views.articles, name="articles"),
    path("articles/nouveau/", views.article_formulaire, name="article_nouveau"),
    path("articles/import/", views.import_articles, name="import_articles"),
    path("articles/export.xlsx", views.export_articles, name="export_articles"),
    path("articles/modele-import.xlsx", views.modele_import, name="modele_import"),
    path("articles/<int:pk>/", views.article, name="article"),
    path("articles/<int:pk>/modifier/", views.article_formulaire, name="article_modifier"),
    path("fournisseurs/", views.fournisseurs, name="fournisseurs"),
    path("fournisseurs/nouveau/", views.fournisseur_formulaire, name="fournisseur_nouveau"),
    path("fournisseurs/<int:pk>/", views.fournisseur, name="fournisseur"),
    path("fournisseurs/<int:pk>/modifier/", views.fournisseur_formulaire, name="fournisseur_modifier"),
    path("a-commander/", views.a_commander, name="a_commander"),
    path("inventaires/", views.inventaires, name="inventaires"),
    path("inventaires/ecarts/", views.ecarts, name="ecarts"),
    path("inventaires/<int:pk>/", views.comptage, name="comptage"),
    path("inventaires/<int:pk>/feuille/", views.feuille_comptage, name="feuille_comptage"),
]
