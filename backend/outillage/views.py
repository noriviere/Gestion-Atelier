from django.shortcuts import get_object_or_404, render

from .models import Outil


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
