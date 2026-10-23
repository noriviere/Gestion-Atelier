from django.shortcuts import get_object_or_404, render

from .models import Outil


def _arbre(outil):
    """Outil et sous-ensembles imbriqués, avec leurs pièces, pour l'affichage en arborescence."""
    return {
        "outil": outil,
        "pieces": list(outil.liens_pieces.select_related("article")),
        "enfants": [_arbre(e) for e in outil.sous_ensembles.all()],
    }


def outils(request):
    racines = Outil.objects.filter(parent__isnull=True).prefetch_related("fabrications__produit")
    return render(request, "outillage/outils.html", {"arbres": [_arbre(o) for o in racines]})


def outil(request, pk):
    outil = get_object_or_404(Outil, pk=pk)
    racine = outil.racine()
    return render(
        request,
        "outillage/outil.html",
        {
            "outil": outil,
            "chemin": outil.chemin(),
            "arbre": _arbre(outil),
            "fabrications": racine.fabrications.select_related("produit", "machine"),
        },
    )
