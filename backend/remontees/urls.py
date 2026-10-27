from django.urls import path

from . import views

urlpatterns = [
    path("", views.remontees, name="remontees"),
    path("meules/montage/", views.montage_meule, name="montage_meule"),
    path("meules/<int:pk>/", views.saisie_meule, name="saisie_meule"),
    path("meules/<int:pk>/demontage/", views.demontage_meule, name="demontage_meule"),
]
