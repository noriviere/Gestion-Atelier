from django.contrib import admin

from .models import Arret, CauseArret, Creneau, Equipe, Shift, Troncon


@admin.register(CauseArret)
class CauseArretAdmin(admin.ModelAdmin):
    list_display = ["libelle", "commentaire_obligatoire", "ordre", "actif"]
    list_editable = ["ordre", "actif"]
    list_filter = ["actif"]
    search_fields = ["libelle"]

    def has_delete_permission(self, request, obj=None):
        # Une cause s'archive (case « actif ») : la supprimer ferait perdre l'historique des arrêts.
        return False


@admin.register(Creneau)
class CreneauAdmin(admin.ModelAdmin):
    list_display = ["nom", "heure_debut", "heure_fin", "libelle_jours", "ordre", "actif"]
    list_editable = ["ordre", "actif"]


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ["code", "nom", "actif"]
    list_editable = ["actif"]


class TronconEnLigne(admin.TabularInline):
    model = Troncon
    extra = 0


class ArretEnLigne(admin.TabularInline):
    model = Arret
    extra = 0
    raw_id_fields = ["saisi_par"]


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["jour", "creneau", "equipe", "machine", "matricule"]
    list_filter = ["creneau", "equipe", "machine"]
    date_hierarchy = "jour"
    inlines = [TronconEnLigne, ArretEnLigne]
