from django.urls import path

from . import views

urlpatterns = [
    path("", views.production, name="production"),
    path("shift/<int:pk>/", views.shift, name="shift"),
    path("rapport/", views.rapport_production, name="rapport_production"),
    path("rapport/export.xlsx", views.export_rapport_production, name="export_rapport_production"),
]
