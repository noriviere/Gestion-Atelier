from django.contrib import admin

from .models import FormatMatiere, Matricule, SaisieMeule


@admin.register(Matricule)
class MatriculeAdmin(admin.ModelAdmin):
    list_display = ["numero", "nom", "actif"]
    list_filter = ["actif"]
    search_fields = ["numero", "nom"]


@admin.register(FormatMatiere)
class FormatMatiereAdmin(admin.ModelAdmin):
    list_display = ["produit", "matiere", "code_lame", "ma5"]
    list_filter = ["matiere", "ma5"]
    search_fields = ["produit__reference", "code_lame"]
    filter_horizontal = ["meules", "machines"]


@admin.register(SaisieMeule)
class SaisieMeuleAdmin(admin.ModelAdmin):
    list_display = ["date_montage", "machine", "meule", "face", "format_matiere", "compteur_fin", "hauteur_finale",
                    "defaut"]
    list_filter = ["machine", "defaut", "face"]
    date_hierarchy = "date_montage"
    raw_id_fields = ["sortie_stock"]
