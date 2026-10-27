from django.urls import path

from . import views

urlpatterns = [
    path("", views.remontees, name="remontees"),
    path("meules/", views.saisies_meules, name="saisies_meules"),
    path("meules/montage/", views.montage_meule, name="montage_meule"),
    path("meules/statistiques/", views.statistiques_meules, name="statistiques_meules"),
    path("meules/controle/", views.controle_meules, name="controle_meules"),
    path("meules/controle/controle-meules.xlsx", views.export_controle_meules, name="export_controle_meules"),
    path("meules/regles/", views.regles_meules, name="regles_meules"),
    path("meules/<int:pk>/", views.saisie_meule, name="saisie_meule"),
    path("meules/<int:pk>/demontage/", views.demontage_meule, name="demontage_meule"),
    path("meules/<int:pk>/modifier/", views.modifier_saisie_meule, name="modifier_saisie_meule"),
    path("meules/<int:pk>/supprimer/", views.supprimer_saisie_meule, name="supprimer_saisie_meule"),
]
