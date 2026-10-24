from django.contrib import admin

from .models import Article, ArticleFournisseur, Fournisseur, Mouvement, TypeInventaire


class ArticleFournisseurInline(admin.TabularInline):
    model = ArticleFournisseur
    extra = 1


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["reference", "designation", "categorie", "origine", "numero_plan", "type_inventaire", "stock", "stock_mini",
                    "mini_commande"]
    list_filter = ["categorie", "origine", "type_inventaire"]
    search_fields = ["reference", "designation", "numero_plan"]
    inlines = [ArticleFournisseurInline]


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ["nom", "contact", "telephone", "email"]
    search_fields = ["nom"]


admin.site.register(TypeInventaire)


@admin.register(Mouvement)
class MouvementAdmin(admin.ModelAdmin):
    list_display = ["date", "article", "type", "quantite", "stock_apres", "utilisateur"]
    list_filter = ["type"]
    readonly_fields = ["stock_apres"]
