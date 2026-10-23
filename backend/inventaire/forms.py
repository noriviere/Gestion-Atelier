from django import forms

from .models import Mouvement


class MouvementForm(forms.Form):
    type = forms.ChoiceField(
        choices=[(Mouvement.SORTIE, "Sortie"), (Mouvement.ENTREE, "Entrée (réception)")],
        widget=forms.RadioSelect,
        initial=Mouvement.SORTIE,
    )
    quantite = forms.DecimalField(label="Quantité", min_value=0.01, decimal_places=2)
    commentaire = forms.CharField(label="Commentaire", required=False, max_length=200)
