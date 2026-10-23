from django.contrib import admin

from .models import Consommation, Machine, Produit, ProduitMachine


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ["code", "nom"]


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ["reference", "designation", "client"]
    search_fields = ["reference", "designation"]


class ConsommationInline(admin.TabularInline):
    model = Consommation
    extra = 1
    autocomplete_fields = ["article"]


@admin.register(ProduitMachine)
class ProduitMachineAdmin(admin.ModelAdmin):
    list_display = ["produit", "machine", "cadence"]
    list_filter = ["machine"]
    filter_horizontal = ["outils"]
    inlines = [ConsommationInline]
