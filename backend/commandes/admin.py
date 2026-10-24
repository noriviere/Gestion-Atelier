from django.contrib import admin

from .models import Commande, LigneCommande


def commande_en_attente(commande):
    return commande is None or commande.etat == Commande.EN_ATTENTE


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 1
    autocomplete_fields = ["article"]

    # Une fois la commande passée, ses lignes ne bougent plus : la réception se fait dans l'application.
    def has_add_permission(self, request, obj=None):
        return commande_en_attente(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return commande_en_attente(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return commande_en_attente(obj) and super().has_delete_permission(request, obj)


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ["numero", "fournisseur", "etat", "date_passage", "date_prevue", "date_reception"]
    list_filter = ["etat", "fournisseur"]
    search_fields = ["numero", "numero_fournisseur", "lignes__article__reference"]
    inlines = [LigneCommandeInline]

    def get_readonly_fields(self, request, obj=None):
        # L'état avance dans l'application, qui note les dates et fait entrer la livraison en stock.
        champs = ["etat", "date_passage", "date_reception", "date_entree_stock"]
        if not commande_en_attente(obj):
            champs += ["fournisseur", "date_creation"]
        return champs
