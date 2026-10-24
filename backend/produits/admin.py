from django.contrib import admin

from .models import Consommation, Document, Machine, Parametre, Produit, ProduitMachine


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ["code", "nom"]


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ["reference", "designation", "client"]
    search_fields = ["reference", "designation"]


class ParametreInline(admin.TabularInline):
    model = Parametre
    extra = 1


class ConsommationInline(admin.TabularInline):
    model = Consommation
    extra = 1
    autocomplete_fields = ["article"]


class DocumentInline(admin.TabularInline):
    model = Document
    extra = 0
    fields = ["titre", "fichier", "produit"]


@admin.register(ProduitMachine)
class ProduitMachineAdmin(admin.ModelAdmin):
    list_display = ["produit", "machine", "etat", "cadence"]
    list_filter = ["etat", "machine"]
    filter_horizontal = ["outils"]
    inlines = [ParametreInline, ConsommationInline, DocumentInline]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["titre", "produit", "fabrication", "ajoute_le"]
    list_filter = ["produit"]
