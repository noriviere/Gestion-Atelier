from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import floatformat
from django.urls import reverse
from django.views.decorators.http import require_POST

from comptes.decorators import modification_requise, mouvement_requis
from inventaire.models import Mouvement

from .forms import OutilForm, PiecesOutilFormSet, SortiePieceForm
from .models import Outil, PieceOutil


def construire_arbre(outil):
    """Outil et sous-ensembles imbriqués, avec leurs pièces, pour l'affichage en arborescence."""
    return {
        "outil": outil,
        "pieces": list(outil.liens_pieces.select_related("article")),
        "sous_ensembles": [construire_arbre(sous_ensemble) for sous_ensemble in outil.sous_ensembles.all()],
    }


def outils(request):
    outils_principaux = Outil.objects.filter(parent__isnull=True).prefetch_related("fabrications__produit")
    return render(request, "outillage/outils.html", {"arbres": [construire_arbre(outil) for outil in outils_principaux]})


def outil(request, pk):
    outil = get_object_or_404(Outil, pk=pk)
    return render(
        request,
        "outillage/outil.html",
        {
            "outil": outil,
            "chemin": outil.chemin(),
            "arbre": construire_arbre(outil),
            "fabrications": outil.racine().fabrications.select_related("produit", "machine"),
        },
    )


def enregistrer_outil(request, outil, page_retour):
    """Formulaire de l'outil et de ses pièces d'usure, commun à la création et à la modification."""
    parent_propose = {"parent": request.GET["parent"]} if request.GET.get("parent") else {}
    formulaire = OutilForm(request.POST or None, instance=outil, initial=parent_propose)
    pieces = PiecesOutilFormSet(request.POST or None, instance=outil)
    if request.method == "POST" and formulaire.is_valid() and pieces.is_valid():
        with transaction.atomic():
            outil = formulaire.save()
            pieces.instance = outil
            pieces.save()
        messages.success(request, f"Outil {outil.code} enregistré.")
        return redirect(outil)
    return render(
        request,
        "outillage/modifier.html",
        {"outil": outil, "form": formulaire, "pieces": pieces, "page_retour": page_retour},
    )


@modification_requise
def nouvel_outil(request):
    parent = Outil.objects.filter(pk=request.GET.get("parent") or None).first()
    return enregistrer_outil(request, Outil(), parent.get_absolute_url() if parent else reverse("outils"))


@modification_requise
def modifier_outil(request, pk):
    outil = get_object_or_404(Outil, pk=pk)
    return enregistrer_outil(request, outil, outil.get_absolute_url())


@require_POST
@modification_requise
def supprimer_outil(request, pk):
    outil = get_object_or_404(Outil, pk=pk)
    parent = outil.parent
    outil.delete()
    messages.success(request, f"Outil {outil.code} supprimé, avec ses sous-ensembles.")
    return redirect(parent or "outils")


@require_POST
@mouvement_requis
def sortie_piece(request, pk):
    """Sortie de stock d'une pièce d'usure montée sur l'outil ou un de ses sous-ensembles."""
    outil = get_object_or_404(Outil, pk=pk)
    formulaire = SortiePieceForm(request.POST)
    if not formulaire.is_valid():
        messages.error(request, "Saisissez une quantité positive.")
        return redirect(outil)
    piece_montee = get_object_or_404(
        PieceOutil.objects.select_related("article", "outil"),
        pk=formulaire.cleaned_data["piece"],
        outil__in=[outil] + outil.descendants(),
    )
    quantite = formulaire.cleaned_data["quantite"]
    mouvement = Mouvement.enregistrer(
        piece_montee.article,
        Mouvement.SORTIE,
        quantite,
        utilisateur=request.user,
        commentaire=f"Remplacement sur {piece_montee.outil.code}",
    )
    messages.success(
        request,
        f"Sortie de {floatformat(quantite, -2)} {piece_montee.article.reference} enregistrée : "
        f"nouveau stock {floatformat(mouvement.stock_apres, -2)}.",
    )
    return redirect(outil)
