from django.urls import path

from . import views

urlpatterns = [
    path("", views.outils, name="outils"),
    path("<int:pk>/", views.outil, name="outil"),
]
