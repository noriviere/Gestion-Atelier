from django.http import Http404
from django.shortcuts import render

from .sujets import PAR_CODE, SUJETS, voisins


def sommaire(request):
    return render(request, "aide/sommaire.html", {"sujets": SUJETS})


def sujet(request, code):
    if code not in PAR_CODE:
        raise Http404("Sujet d'aide inconnu")
    precedent, suivant = voisins(code)
    return render(
        request,
        f"aide/{code}.html",
        {"sujets": SUJETS, "sujet": PAR_CODE[code], "precedent": precedent, "suivant": suivant},
    )
