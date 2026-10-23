from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from outillage.views import construire_arbre

from .models import Machine, Produit, ProduitMachine


def produits(request):
    selection = Produit.objects.prefetch_related("fabrications__machine")
    recherche = request.GET.get("q", "").strip()
    if recherche:
        selection = selection.filter(
            Q(reference__icontains=recherche) | Q(designation__icontains=recherche) | Q(client__icontains=recherche)
        )
    return render(request, "produits/produits.html", {"produits": selection, "recherche": recherche})


def produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    return render(
        request,
        "produits/produit.html",
        {"produit": produit, "fabrications": produit.fabrications.select_related("machine")},
    )


def fiche(request, pk):
    fabrication = get_object_or_404(ProduitMachine.objects.select_related("produit", "machine"), pk=pk)
    return render(
        request,
        "produits/fiche.html",
        {
            "fabrication": fabrication,
            "arbres": [construire_arbre(outil) for outil in fabrication.outils.all()],
            "consommations": fabrication.consommations.select_related("article"),
        },
    )


def machines(request):
    return render(request, "produits/machines.html", {"machines": Machine.objects.prefetch_related("fabrications")})


def machine(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    return render(
        request,
        "produits/machine.html",
        {"machine": machine, "fabrications": machine.fabrications.select_related("produit")},
    )
