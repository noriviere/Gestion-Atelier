from django.urls import path

from . import views

urlpatterns = [
    path("", views.sommaire, name="aide"),
    path("<slug:code>/", views.sujet, name="aide_sujet"),
]
