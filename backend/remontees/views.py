from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from comptes import roles
from inventaire.models import Mouvement
from produits.matrice import cle_naturelle
from produits.models import Machine

from . import regles
from .forms import DemontageForm, MontageForm, valeurs_initiales_montage
from .models import FormatMatiere, Matricule, SaisieMeule

NOMBRE_DERNIERES_SAISIES = 10


def machines_avec_meules_montees():
    """Machines dans l'ordre naturel (S2 avant S10), avec le nombre de meules montées et pas encore démontées."""
    machines = Machine.objects.annotate(meules_montees=Count(
        "saisies_meules", filter=Q(saisies_meules__demonte_le__isnull=True)))
    return sorted(machines, key=lambda machine: cle_naturelle(machine.code))


def remontees(request):
    """Écran commun des remontées : la machine d'abord, puis le sujet et ce qui attend sur cette machine."""
    machines = machines_avec_meules_montees()
    machine = next((machine for machine in machines if machine.code == request.GET.get("machine")), None)
    contexte = {"machines": machines, "machine_choisie": machine}
    if machine:
        saisies = SaisieMeule.objects.filter(machine=machine).select_related("meule", "format_matiere__produit")
        contexte["meules_montees"] = saisies.montees()
        contexte["dernieres_demontees"] = saisies.demontees().order_by("-demonte_le")[:NOMBRE_DERNIERES_SAISIES]
    return render(request, "remontees/remontees.html", contexte)


def contexte_formulaire(formulaire):
    """Ce que les gabarits de saisie ajoutent au formulaire : la liste des matricules."""
    return {"form": formulaire, "matricules": Matricule.objects.filter(actif=True)}


def table_formats():
    """Pour remontees.js : code lame, MA5 et meules prévues de chaque format et matière."""
    table = {}
    for ligne in FormatMatiere.objects.prefetch_related("meules"):
        table.setdefault(str(ligne.produit_id), {})[ligne.matiere] = {
            "code_lame": ligne.code_lame,
            "ma5": ligne.ma5,
            "meules": [str(meule.pk) for meule in ligne.meules.all()],
        }
    return table


def matricule(numero):
    return Matricule.objects.get_or_create(numero=numero)[0]


def montage_meule(request):
    peut_sortir_du_stock = roles.a_le_droit(request.user, "stock_mouvements")
    machine = Machine.objects.filter(code=request.GET.get("machine")).first()
    formulaire = MontageForm(request.POST or None, initial=valeurs_initiales_montage(machine),
                             peut_sortir_du_stock=peut_sortir_du_stock)
    if request.method == "POST" and formulaire.is_valid():
        if formulaire.avertissements_a_confirmer:
            formulaire.marquer_avertissements_vus()
        else:
            saisie = enregistrer_montage(formulaire, request.user)
            message = f"Montage enregistré : meule {saisie.meule.reference} face {saisie.face} sur {saisie.machine.code}."
            if saisie.sortie_stock:
                message += f" Sortie de stock faite, nouveau stock {saisie.sortie_stock.stock_apres:g}."
            messages.success(request, message)
            return redirect(f"{reverse('remontees')}?machine={saisie.machine.code}")
    contexte = contexte_formulaire(formulaire)
    contexte.update({"machine": machine, "table_formats": table_formats()})
    return render(request, "remontees/montage_meule.html", contexte)


@transaction.atomic
def enregistrer_montage(formulaire, utilisateur):
    donnees = formulaire.cleaned_data
    saisie = SaisieMeule.objects.create(
        machine=donnees["machine"], format_matiere=formulaire.format_matiere, face=donnees["face"],
        meule=donnees["meule"], lot_fournisseur=donnees["lot_fournisseur"], date_montage=donnees["date_montage"],
        ma5=donnees["ma5"] == FormatMatiere.MA5_OUI, pression_arrosage=donnees["pression_arrosage"],
        vitesse_rotation=donnees["vitesse_rotation"], vitesse_avance=donnees["vitesse_avance"],
        hauteur_initiale=donnees["hauteur_initiale"], compteur_debut=donnees["compteur_debut"],
        matricule_monteur=matricule(donnees["matricule_monteur"]),
        commentaire_montage=donnees["commentaire_montage"], monte_par=utilisateur,
        avertissements="\n".join(formulaire.avertissements),
    )
    if donnees.get("sortir_du_stock"):
        # Sortie ordinaire : les sorties de stock ne sont pas rattachées à une machine.
        saisie.sortie_stock = Mouvement.enregistrer(saisie.meule, Mouvement.SORTIE, 1, utilisateur=utilisateur,
                                                    commentaire=f"Montage de meule (remontée n° {saisie.pk})")
        saisie.save(update_fields=["sortie_stock"])
    return saisie


def demontage_meule(request, pk):
    saisie = get_object_or_404(SaisieMeule.objects.select_related("machine", "meule", "format_matiere__produit",
                                                                  "matricule_monteur"), pk=pk)
    if saisie.est_demontee:
        messages.info(request, "Cette meule est déjà démontée.")
        return redirect(saisie)
    formulaire = DemontageForm(request.POST or None, saisie=saisie)
    if request.method == "POST" and formulaire.is_valid():
        if formulaire.avertissements_a_confirmer:
            formulaire.marquer_avertissements_vus()
        else:
            enregistrer_demontage(saisie, formulaire, request.user)
            message = f"Démontage enregistré : {saisie.nombre_faces_brut} faces"
            if saisie.faces_par_meule_reference is not None:
                message += (f", soit {saisie.faces_par_meule_reference:.0f} faces pour une meule de "
                            f"{regles.REGLAGES['hauteur_reference_mm']} mm")
            messages.success(request, message + ".")
            return redirect(saisie)
    contexte = contexte_formulaire(formulaire)
    contexte.update({"saisie": saisie, "aide_commentaire": regles.AIDE_COMMENTAIRE,
                     "seuil_non_finie": regles.REGLAGES["seuil_non_finie_mm"]})
    return render(request, "remontees/demontage_meule.html", contexte)


@transaction.atomic
def enregistrer_demontage(saisie, formulaire, utilisateur):
    donnees = formulaire.cleaned_data
    saisie.matricule_demonteur = matricule(donnees["matricule_demonteur"])
    saisie.compteur_fin = donnees["compteur_fin"]
    saisie.hauteur_finale = donnees["hauteur_finale"]
    saisie.probleme = donnees["probleme"]
    saisie.themes = donnees["themes"]
    saisie.commentaire = donnees["commentaire"]
    saisie.demonte_par = utilisateur
    saisie.demonte_le = timezone.now()
    saisie.defaut = regles.est_un_defaut(saisie.probleme, saisie.themes, saisie.hauteur_finale)
    saisie.avertissements = "\n".join(filter(None, [saisie.avertissements, *formulaire.avertissements]))
    saisie.save()


def saisie_meule(request, pk):
    saisie = get_object_or_404(
        SaisieMeule.objects.select_related("machine", "meule", "format_matiere__produit", "matricule_monteur",
                                           "matricule_demonteur", "monte_par", "demonte_par"), pk=pk)
    return render(request, "remontees/saisie_meule.html", {
        "saisie": saisie, "hauteur_reference": regles.REGLAGES["hauteur_reference_mm"],
    })
