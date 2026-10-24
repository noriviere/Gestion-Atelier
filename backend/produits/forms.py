from django import forms

from outillage.models import Outil

from .models import TAILLE_MAXI_DOCUMENT, Consommation, Document, Parametre, Produit, ProduitMachine


class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = ["reference", "designation", "client", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}


class DuplicationProduitForm(forms.Form):
    reference = forms.CharField(label="Référence du nouveau produit", max_length=40)
    designation = forms.CharField(label="Désignation", max_length=160)

    def clean_reference(self):
        reference = self.cleaned_data["reference"].strip()
        if Produit.objects.filter(reference__iexact=reference).exists():
            raise forms.ValidationError(f"Le produit {reference} existe déjà.")
        return reference


class FicheForm(forms.ModelForm):
    class Meta:
        model = ProduitMachine
        fields = ["machine", "etat", "cadence", "outils", "notes"]
        widgets = {
            "etat": forms.RadioSelect,
            "outils": forms.CheckboxSelectMultiple,
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Seuls les outils principaux se choisissent : leurs sous-ensembles et pièces suivent dans la fiche.
        self.fields["outils"].queryset = Outil.objects.filter(parent__isnull=True)
        self.fields["etat"].choices = [choix for choix in ProduitMachine.ETATS if choix[0] in ProduitMachine.ETATS_AVEC_FICHE]
        if self.instance.pk and self.instance.a_une_fiche:
            # La machine d'une fiche existante ne change pas : on duplique la fiche vers une autre machine.
            self.fields["machine"].disabled = True

    def clean_machine(self):
        machine = self.cleaned_data["machine"]
        doublon = (ProduitMachine.objects.filter(produit=self.instance.produit, machine=machine)
                   .exclude(pk=self.instance.pk).first())
        if doublon:
            raise forms.ValidationError(
                f"{self.instance.produit.reference} est déjà renseigné sur {machine.code} "
                f"({doublon.get_etat_display().lower()}) : ouvrez cette case depuis la matrice."
            )
        return machine


class ParametreForm(forms.ModelForm):
    class Meta:
        model = Parametre
        fields = ["libelle", "valeur", "unite"]
        widgets = {
            "libelle": forms.TextInput(attrs={"placeholder": "Ex. Vitesse meule"}),
            "valeur": forms.TextInput(attrs={"placeholder": "35"}),
            "unite": forms.TextInput(attrs={"placeholder": "m/s", "class": "champ-court"}),
        }


class ConsommationForm(forms.ModelForm):
    class Meta:
        model = Consommation
        fields = ["article", "quantite"]
        widgets = {"quantite": forms.TextInput(attrs={"placeholder": "Ex. 1 bande / poste"})}


def formset_parametres(lignes_vides=1):
    return forms.inlineformset_factory(
        ProduitMachine, Parametre, form=ParametreForm, extra=lignes_vides, can_delete=True,
    )
ConsommationsFormSet = forms.inlineformset_factory(
    ProduitMachine, Consommation, form=ConsommationForm, extra=1, can_delete=True,
)


class DocumentForm(forms.ModelForm):
    POUR_LA_FICHE = "fiche"
    POUR_LE_PRODUIT = "produit"
    portee = forms.ChoiceField(
        label="Concerne",
        choices=[(POUR_LA_FICHE, "cette machine seulement"), (POUR_LE_PRODUIT, "le produit sur toutes ses machines")],
        initial=POUR_LA_FICHE,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Document
        fields = ["titre", "fichier"]
        widgets = {"titre": forms.TextInput(attrs={"placeholder": "Ex. Photo du réglage pince"})}

    def clean_fichier(self):
        fichier = self.cleaned_data["fichier"]
        if fichier and fichier.size > TAILLE_MAXI_DOCUMENT:
            raise forms.ValidationError("Le fichier dépasse 20 Mo.")
        return fichier
