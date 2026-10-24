from django import forms

from inventaire.models import Article

from .models import Outil, PieceOutil


class OutilForm(forms.ModelForm):
    class Meta:
        model = Outil
        fields = ["code", "nom", "parent", "description"]
        labels = {"parent": "Sous-ensemble de"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].empty_label = "— aucun (outil principal) —"
        if self.instance.pk:
            outils_interdits = [self.instance.pk] + [sous_ensemble.pk for sous_ensemble in self.instance.descendants()]
            self.fields["parent"].queryset = Outil.objects.exclude(pk__in=outils_interdits)

    def clean_parent(self):
        parent = self.cleaned_data["parent"]
        if parent and self.instance.pk and self.instance in parent.chemin():
            raise forms.ValidationError("Un outil ne peut pas être rangé sous lui-même ou sous un de ses sous-ensembles.")
        return parent


class PieceOutilForm(forms.ModelForm):
    class Meta:
        model = PieceOutil
        fields = ["article", "quantite"]
        labels = {"article": "Pièce d'usure"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["article"].queryset = Article.objects.order_by("categorie", "reference")
        self.fields["quantite"].widget.attrs.update({"class": "compte", "min": 1})


PiecesOutilFormSet = forms.inlineformset_factory(
    Outil, PieceOutil, form=PieceOutilForm, extra=3, can_delete=True
)


class SortiePieceForm(forms.Form):
    piece = forms.IntegerField(widget=forms.HiddenInput)
    quantite = forms.DecimalField(label="Quantité", min_value=0.01, max_digits=10, decimal_places=2)
