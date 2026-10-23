from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from outillage.views import _arbre

from .models import Machine, Produit, ProduitMachine


def produits(request):
    qs = Produit.objects.prefetch_related("fabrications__machine")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(reference__icontains=q) | Q(designation__icontains=q) | Q(client__icontains=q))
    return render(request, "produits/produits.html", {"produits": qs, "q": q})


def produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    return render(
        request,
        "produits/produit.html",
        {"produit": produit, "fabrications": produit.fabrications.select_related("machine")},
    )


def fiche(request, pk):
    fab = get_object_or_404(ProduitMachine.objects.select_related("produit", "machine"), pk=pk)
    return render(
        request,
        "produits/fiche.html",
        {
            "fab": fab,
            "arbres": [_arbre(o) for o in fab.outils.all()],
            "consommations": fab.consommations.select_related("article"),
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
