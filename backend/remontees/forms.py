from django import forms
from django.utils import timezone

from inventaire.models import Article
from produits.models import Machine, Produit

from . import regles
from .models import LONGUEUR_MATRICULE, FormatMatiere, Matricule

SEPARATEUR_AVERTISSEMENTS = "\n"


class ChampMatricule(forms.CharField):
    """Matricule choisi dans la liste (datalist) ou tapé : « 534 » devient « 0534 »."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", LONGUEUR_MATRICULE)
        kwargs.setdefault("help_text", "Choisissez dans la liste ou saisissez les 4 chiffres.")
        super().__init__(**kwargs)
        self.widget.attrs.update({"list": "matricules", "inputmode": "numeric", "autocomplete": "off",
                                  "class": "champ-matricule"})

    def clean(self, value):
        numero = Matricule.normaliser(super().clean(value))
        if numero and not (numero.isdigit() and len(numero) == LONGUEUR_MATRICULE):
            raise forms.ValidationError(f"Un matricule a {LONGUEUR_MATRICULE} chiffres.")
        return numero


class SaisieAvecAvertissementsForm(forms.Form):
    """Les avertissements ne bloquent pas : ils s'affichent, puis l'envoi suivant les confirme.

    Le champ caché garde les avertissements déjà montrés ; un nouvel avertissement (valeur changée
    entre-temps) redemande une confirmation.
    """

    avertissements_vus = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.avertissements = []

    def nouveaux_matricules(self, *noms_champs):
        numeros = {self.cleaned_data.get(nom) for nom in noms_champs} - {None, ""}
        connus = set(Matricule.objects.filter(numero__in=numeros).values_list("numero", flat=True))
        return sorted(numeros - connus)

    @property
    def avertissements_a_confirmer(self):
        donnees = getattr(self, "cleaned_data", {})  # formulaire pas encore envoyé : rien à confirmer
        vus = set(donnees.get("avertissements_vus", "").split(SEPARATEUR_AVERTISSEMENTS))
        return [texte for texte in self.avertissements if texte not in vus]

    def marquer_avertissements_vus(self):
        """Prépare le formulaire réaffiché : le prochain envoi vaut confirmation de ces avertissements."""
        donnees = self.data.copy()
        donnees["avertissements_vus"] = SEPARATEUR_AVERTISSEMENTS.join(self.avertissements)
        self.data = donnees

    def ajouter_erreurs(self, erreurs):
        for erreur in erreurs:
            self.add_error(None, erreur)


class MontageForm(SaisieAvecAvertissementsForm):
    machine = forms.ModelChoiceField(Machine.objects.all(), label="N° de machine")
    matricule_monteur = ChampMatricule(label="Matricule monteur")
    produit = forms.ModelChoiceField(Produit.objects.none(), label="Format (produit)")
    matiere = forms.ChoiceField(choices=FormatMatiere.MATIERES, label="Matière", widget=forms.RadioSelect)
    face = forms.ChoiceField(choices=[("A", "A"), ("B", "B")], label="Face", widget=forms.RadioSelect)
    meule = forms.ModelChoiceField(Article.objects.none(), label="N° article meule")
    lot_fournisseur = forms.CharField(label="Lot fournisseur / N° FA / Beleg", max_length=60,
                                      help_text="Le numéro FA ou Beleg inscrit sur l'étiquette de la meule.")
    date_montage = forms.DateField(label="Date de montage",
                                   widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                                   help_text="Aujourd'hui par défaut, modifiable.")
    ma5 = forms.ChoiceField(choices=[("oui", "Oui"), ("non", "Non")], label="MA5", required=False,
                            widget=forms.RadioSelect,
                            help_text="Choisi automatiquement, sauf quand la table indique « peut-être ».")
    pression_arrosage = forms.IntegerField(label="Pression d'arrosage", min_value=0,
                                           help_text="Lue sur le manomètre ; 0 si le manomètre est hors service.")
    vitesse_rotation = forms.IntegerField(label="Vitesse de rotation (m/s)", min_value=0)
    vitesse_avance = forms.IntegerField(label="Vitesse d'avance (mm/min)", min_value=0)
    hauteur_initiale = forms.DecimalField(label="Hauteur initiale de la meule (mm)", min_value=0, max_digits=6,
                                          decimal_places=2)
    compteur_debut = forms.IntegerField(label="Compteur machine au montage", min_value=0,
                                        help_text="Normalement 0 : le compteur est remis à zéro au montage.")
    commentaire_montage = forms.CharField(label="Commentaire", required=False,
                                          widget=forms.Textarea(attrs={"rows": 2}),
                                          help_text="Obligatoire si la machine n'est pas prévue pour ce format.")
    sortir_du_stock = forms.BooleanField(label="Sortir la meule du stock", required=False,
                                         help_text="Décochez si la meule a déjà été sortie du magasin.")

    def __init__(self, *args, peut_sortir_du_stock=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["produit"].queryset = Produit.objects.filter(formats_meule__isnull=False).distinct()
        self.fields["meule"].queryset = Article.objects.filter(formats_meule__isnull=False).distinct()
        if not peut_sortir_du_stock:
            del self.fields["sortir_du_stock"]
        for nom in ("pression_arrosage", "vitesse_rotation", "vitesse_avance", "hauteur_initiale", "compteur_debut"):
            self.fields[nom].widget.attrs["inputmode"] = "decimal" if nom == "hauteur_initiale" else "numeric"
        self.format_matiere = None

    def clean(self):
        donnees = super().clean()
        produit, matiere = donnees.get("produit"), donnees.get("matiere")
        if produit and matiere:
            self.format_matiere = (FormatMatiere.objects.prefetch_related("meules", "machines")
                                   .filter(produit=produit, matiere=matiere).first())
            if self.format_matiere is None:
                self.add_error(None, f"Format + matière : {produit.reference} en "
                                     f"{dict(FormatMatiere.MATIERES)[matiere].lower()} est absent de la table "
                                     f"« Formats et matière ».")
            elif self.format_matiere.ma5 == FormatMatiere.MA5_PEUT_ETRE:
                if donnees.get("ma5") not in ("oui", "non"):
                    self.add_error("ma5", "La table indique « peut-être » : choisissez Oui ou Non.")
            else:
                donnees["ma5"] = self.format_matiere.ma5  # choisi automatiquement
        if self.errors:
            return donnees
        valeurs = {champ: donnees.get(champ) for champ, _ in regles.CHAMPS_HABITUELS_MONTAGE}
        erreurs, self.avertissements = regles.controler_montage(
            donnees["machine"], self.format_matiere, donnees["meule"], donnees["date_montage"], valeurs,
            donnees.get("commentaire_montage", ""), self.nouveaux_matricules("matricule_monteur"),
        )
        self.ajouter_erreurs(erreurs)
        return donnees


class DemontageForm(SaisieAvecAvertissementsForm):
    PROBLEME_NON = "non"
    PROBLEME_OUI = "oui"

    matricule_demonteur = ChampMatricule(label="Matricule démonteur")
    compteur_fin = forms.IntegerField(label="Compteur machine au démontage", min_value=0,
                                      help_text="La valeur affichée par le compteur au moment du démontage.")
    hauteur_finale = forms.DecimalField(label="Hauteur finale de la meule (mm)", min_value=0, max_digits=6,
                                        decimal_places=2, help_text="Il faut aller jusqu'à 0 mm.")
    probleme = forms.ChoiceField(label="Tout s'est-il bien passé ?", widget=forms.RadioSelect,
                                 choices=[(PROBLEME_NON, "Oui, rien à signaler"), (PROBLEME_OUI, "Non, j'ai une remarque")])
    themes = forms.MultipleChoiceField(label="Qu'est-ce qui a posé problème ? (plusieurs choix possibles)",
                                       choices=[(theme, theme) for theme in regles.THEMES], required=False,
                                       widget=forms.CheckboxSelectMultiple)
    commentaire = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}),
                                  help_text="Obligatoire si la meule est démontée avant usure totale.")

    def __init__(self, *args, saisie, **kwargs):
        super().__init__(*args, **kwargs)
        self.saisie = saisie
        for nom in ("compteur_fin", "hauteur_finale"):
            self.fields[nom].widget.attrs["inputmode"] = "decimal" if nom == "hauteur_finale" else "numeric"

    def clean(self):
        donnees = super().clean()
        if self.errors:
            return donnees
        donnees["probleme"] = donnees["probleme"] == self.PROBLEME_OUI
        if not donnees["probleme"]:
            donnees["themes"] = []
        erreurs, self.avertissements = regles.controler_demontage(
            self.saisie, donnees["compteur_fin"], donnees["hauteur_finale"], donnees["probleme"], donnees["themes"],
            donnees.get("commentaire", ""), self.nouveaux_matricules("matricule_demonteur"),
        )
        self.ajouter_erreurs(erreurs)
        return donnees


def valeurs_initiales_montage(machine=None):
    return {"machine": machine, "date_montage": timezone.localdate(), "pression_arrosage": 6, "compteur_debut": 0,
            "sortir_du_stock": True}
