from django.contrib import admin

from .models import Commande, LigneCommande


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 1
    autocomplete_fields = ["article"]


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ["numero", "fournisseur", "etat", "date_passage", "date_prevue", "date_reception"]
    list_filter = ["etat", "fournisseur"]
    search_fields = ["numero", "numero_fournisseur", "lignes__article__reference"]
    readonly_fields = ["date_entree_stock"]
    inlines = [LigneCommandeInline]
