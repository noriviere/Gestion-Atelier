from django.contrib import admin

from .models import Outil, PieceOutil


class PieceOutilInline(admin.TabularInline):
    model = PieceOutil
    extra = 1
    autocomplete_fields = ["article"]


@admin.register(Outil)
class OutilAdmin(admin.ModelAdmin):
    list_display = ["code", "nom", "parent"]
    search_fields = ["code", "nom"]
    inlines = [PieceOutilInline]
