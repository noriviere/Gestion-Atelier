from django.contrib import messages
from django.contrib.auth.models import Group, User
from django.shortcuts import redirect, render

from . import roles


def droits(request):
    """Page « Droits » : sous-fonctions de chaque profil et profil de chaque compte (ouverte par admin_droits)."""
    if request.method == "POST":
        if request.POST.get("formulaire") == "comptes":
            enregistrer_profils_des_comptes(request.POST)
            messages.success(request, "Profils des comptes enregistrés.")
        else:
            _, profils = roles.tableau_des_droits()
            roles.enregistrer_droits({
                groupe: {code for code in request.POST.getlist(f"droits_{groupe.pk}")} for groupe, _ in profils
            })
            messages.success(request, "Droits des profils enregistrés.")
        return redirect("droits")

    blocs, profils = roles.tableau_des_droits()
    lignes = [
        {
            "bloc": bloc,
            "cases_bloc": [(groupe, all(f.code in codes for f in bloc.fonctions)) for groupe, codes in profils],
            "fonctions": [
                (fonction, [(groupe, fonction.code in codes) for groupe, codes in profils]) for fonction in bloc.fonctions
            ],
        }
        for bloc in blocs
    ]
    return render(request, "comptes/droits.html", {
        "profils": [groupe for groupe, _ in profils],
        "lignes": lignes,
        "comptes": [(compte, roles.profil(compte)) for compte in User.objects.filter(is_active=True).order_by("username")],
        "groupes": sorted(Group.objects.filter(name__in=roles.GROUPES), key=lambda groupe: roles.GROUPES.index(groupe.name)),
    })


def enregistrer_profils_des_comptes(donnees):
    """Un seul profil par compte ; les super-utilisateurs restent Admin quoi qu'il arrive."""
    groupes = {str(groupe.pk): groupe for groupe in Group.objects.filter(name__in=roles.GROUPES)}
    for compte in User.objects.filter(is_active=True, is_superuser=False):
        choix = donnees.get(f"profil_{compte.pk}")
        if choix is None:
            continue
        autres_groupes = compte.groups.exclude(name__in=roles.GROUPES)
        compte.groups.set(list(autres_groupes) + ([groupes[choix]] if choix in groupes else []))
