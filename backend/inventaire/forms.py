from django import forms
from django.core.exceptions import ValidationError

from .models import Article, ArticleFournisseur, Fournisseur, Mouvement


class MouvementForm(forms.Form):
    type = forms.ChoiceField(
        choices=[(Mouvement.SORTIE, "Sortie"), (Mouvement.ENTREE, "Entrée (réception)")],
        widget=forms.RadioSelect,
        initial=Mouvement.SORTIE,
    )
    quantite = forms.DecimalField(label="Quantité", min_value=0.01, max_digits=10, decimal_places=2)
    commentaire = forms.CharField(label="Commentaire", required=False, max_length=200)


class ArticleForm(forms.ModelForm):
    """Données de référence de l'article. Le stock, lui, ne change que par les mouvements et les comptages."""

    stock_initial = forms.DecimalField(
        label="Stock initial", min_value=0, max_digits=10, decimal_places=2, required=False,
        help_text="Quantité en magasin à la création, enregistrée comme une entrée de stock.",
    )

    class Meta:
        model = Article
        fields = ["reference", "designation", "categorie", "origine", "numero_plan", "type_inventaire", "emplacement",
                  "unite", "stock_mini", "mini_commande", "frequence_inventaire"]
        labels = {"reference": "Référence", "designation": "Désignation", "categorie": "Catégorie",
                  "type_inventaire": "Type d'inventaire", "unite": "Unité"}
        widgets = {"origine": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            del self.fields["stock_initial"]
            # 4 plutôt que 4.00 dans les champs de quantité.
            for nom_champ in ("stock_mini", "mini_commande"):
                self.initial[nom_champ] = getattr(self.instance, nom_champ).normalize()


class LienFournisseurFormSetBase(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        formulaires_gardes = [formulaire for formulaire in self.forms
                              if formulaire.cleaned_data and not formulaire.cleaned_data.get("DELETE")]
        if sum(1 for formulaire in formulaires_gardes if formulaire.cleaned_data.get("prefere")) > 1:
            raise ValidationError("Un seul fournisseur peut être le fournisseur préféré.")

    def save(self, commit=True):
        """Enregistre d'abord les liens qui perdent la préférence, pour ne jamais avoir deux préférés en base."""
        liens = super().save(commit=False)
        for lien in self.deleted_objects:
            lien.delete()
        for lien in sorted(liens, key=lambda lien: lien.prefere):
            lien.save()
        return liens


LiensFournisseursFormSet = forms.inlineformset_factory(
    Article, ArticleFournisseur, formset=LienFournisseurFormSetBase,
    fields=["fournisseur", "reference_fournisseur", "prix", "delai", "prefere"],
    labels={"reference_fournisseur": "Réf. fournisseur", "prix": "Prix unitaire (€)", "delai": "Délai (jours)",
            "prefere": "Préféré"},
    extra=2, can_delete=True,
)


class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ["nom", "contact", "telephone", "email"]
        labels = {"telephone": "Téléphone", "email": "E-mail"}
