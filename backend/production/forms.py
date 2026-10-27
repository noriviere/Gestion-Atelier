from datetime import datetime, timedelta

from django import forms
from django.utils import timezone

from produits.models import Machine, Produit, ProduitMachine
from remontees.forms import ChampMatricule

from .models import CauseArret, Creneau, Equipe, Shift

CHAMP_HEURE = forms.TimeInput(attrs={"type": "time"}, format="%H:%M")
CHAMP_DATE = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


def champs_numeriques(formulaire, *noms):
    for nom in noms:
        formulaire.fields[nom].widget.attrs["inputmode"] = "numeric"


class OuvrirShiftForm(forms.Form):
    machine = forms.ModelChoiceField(Machine.objects.all(), label="Machine")
    jour = forms.DateField(label="Date", widget=CHAMP_DATE, help_text="Date du début du créneau.")
    creneau = forms.ModelChoiceField(Creneau.objects.filter(actif=True), label="Créneau",
                                     help_text="Proposé selon l'heure, modifiable.")
    equipe = forms.ModelChoiceField(Equipe.objects.filter(actif=True), label="Équipe", empty_label="— Choisir —",
                                    help_text="E1 et E2 alternent chaque semaine : choisissez la vôtre.")
    matricule = ChampMatricule(label="Matricule")

    def clean(self):
        donnees = super().clean()
        machine, jour, creneau = donnees.get("machine"), donnees.get("jour"), donnees.get("creneau")
        if machine and jour and creneau:
            if Shift.objects.filter(machine=machine, jour=jour, creneau=creneau).exists():
                raise forms.ValidationError(f"Le shift {creneau.nom.lower()} du {jour:%d/%m/%Y} sur {machine.code} "
                                            "est déjà ouvert.")
        return donnees


def produits_de_la_machine(machine):
    """Produits programmés (ou à sécuriser) sur la machine dans la matrice ; tous les produits si aucun."""
    programmes = Produit.objects.filter(fabrications__machine=machine,
                                        fabrications__etat__in=ProduitMachine.ETATS_AVEC_FICHE)
    return programmes if programmes.exists() else Produit.objects.all()


def moment_dans_le_shift(shift, heure):
    """Heure saisie -> date et heure dans le shift : pour une nuit, 2 h est le lendemain du début."""
    moment = timezone.make_aware(datetime.combine(shift.jour, heure))
    if moment < shift.debut:
        moment += timedelta(days=1)
    return moment


class ProduitForm(forms.Form):
    """Démarrer le premier produit du shift, ou changer de produit."""

    produit = forms.ModelChoiceField(Produit.objects.none(), label="Produit")
    heure = forms.TimeField(label="Heure de début", widget=CHAMP_HEURE)
    compteur_debut = forms.IntegerField(label="Compteur au début", min_value=0, required=False,
                                        help_text="Laissez vide si le compteur a été remis à zéro.")
    compteur_fin_precedent = forms.IntegerField(label="Compteur à la fin du produit précédent", min_value=0,
                                                required=False)

    def __init__(self, *args, shift, **kwargs):
        super().__init__(*args, **kwargs)
        self.shift = shift
        self.precedent = shift.troncon_en_cours()
        self.fields["produit"].queryset = produits_de_la_machine(shift.machine)
        champs_numeriques(self, "compteur_debut", "compteur_fin_precedent")
        if self.precedent is None or self.precedent.compteur_fin is not None:
            del self.fields["compteur_fin_precedent"]
        else:
            self.fields["compteur_fin_precedent"].required = True
            self.fields["compteur_fin_precedent"].label = f"Compteur à la fin de {self.precedent.produit.reference}"

    def clean(self):
        donnees = super().clean()
        if donnees.get("heure") is None:
            return donnees
        moment = moment_dans_le_shift(self.shift, donnees["heure"])
        if not self.shift.debut <= moment < self.shift.fin:
            self.add_error("heure", f"L'heure doit être dans le shift ({timezone.localtime(self.shift.debut):%H:%M}"
                                    f" – {timezone.localtime(self.shift.fin):%H:%M}).")
        elif self.precedent and moment <= self.precedent.debut:
            self.add_error("heure", f"Le produit précédent a commencé à "
                                    f"{timezone.localtime(self.precedent.debut):%H:%M} : le changement est forcément après.")
        fin_precedent = donnees.get("compteur_fin_precedent")
        if fin_precedent is not None and fin_precedent < self.precedent.compteur_debut:
            self.add_error("compteur_fin_precedent", "Le compteur de fin est plus petit que celui du début.")
        donnees["debut"] = moment
        return donnees


class QuantiteForm(forms.Form):
    compteur_debut = forms.IntegerField(label="Compteur au début", min_value=0, required=False)
    compteur_fin = forms.IntegerField(label="Compteur à la fin", min_value=0,
                                      help_text="La quantité lue sur la machine.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        champs_numeriques(self, "compteur_debut", "compteur_fin")

    def clean(self):
        donnees = super().clean()
        if donnees.get("compteur_debut") is None:
            donnees["compteur_debut"] = 0
        if donnees.get("compteur_fin") is not None and donnees["compteur_fin"] < donnees["compteur_debut"]:
            self.add_error("compteur_fin", "Le compteur de fin est plus petit que celui du début.")
        return donnees


class ArretForm(forms.Form):
    cause = forms.ModelChoiceField(CauseArret.objects.filter(actif=True), label="Cause", empty_label="— Choisir —")
    duree = forms.IntegerField(label="Durée (min)", min_value=1)
    troncon = forms.ModelChoiceField(None, label="Produit concerné", required=False, empty_label="—")
    commentaire = forms.CharField(max_length=300, required=False)

    def __init__(self, *args, shift, **kwargs):
        super().__init__(*args, **kwargs)
        self.shift = shift
        self.fields["troncon"].queryset = shift.troncons.select_related("produit")
        self.fields["troncon"].label_from_instance = str
        en_cours = shift.troncon_en_cours()
        if en_cours:
            self.fields["troncon"].initial = en_cours.pk
        champs_numeriques(self, "duree")

    def clean(self):
        donnees = super().clean()
        cause, duree = donnees.get("cause"), donnees.get("duree")
        if cause and cause.commentaire_obligatoire and not donnees.get("commentaire", "").strip():
            self.add_error("commentaire", f"Précisez la cause « {cause} » dans le commentaire.")
        if duree:
            bilan = self.shift.bilan()
            if bilan.arrets + duree > bilan.theorique:
                self.add_error("duree", f"Avec cet arrêt, le shift aurait {bilan.arrets + duree} min d'arrêt pour "
                                        f"{bilan.theorique} min de temps théorique.")
        return donnees


class FiltresRapportForm(forms.Form):
    du = forms.DateField(label="Du", widget=CHAMP_DATE, required=False)
    au = forms.DateField(label="Au", widget=CHAMP_DATE, required=False)
    machine = forms.ModelChoiceField(Machine.objects.all(), required=False, empty_label="Toutes les machines")
    equipe = forms.ModelChoiceField(Equipe.objects.all(), required=False, empty_label="Toutes les équipes")
    creneau = forms.ModelChoiceField(Creneau.objects.all(), required=False, empty_label="Tous les créneaux")
    produit = forms.ModelChoiceField(Produit.objects.all(), required=False, empty_label="Tous les produits")
    cause = forms.ModelChoiceField(CauseArret.objects.all(), required=False, empty_label="Toutes les causes")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["machine"].label_from_instance = lambda machine: machine.code
        self.fields["produit"].label_from_instance = lambda produit: produit.reference
        self.fields["creneau"].label_from_instance = lambda creneau: creneau.nom
