from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from comptes import roles
from produits.matrice import cle_naturelle
from produits.models import Machine, ProduitMachine
from remontees.models import Matricule

from . import calculs, excel
from .forms import ArretForm, FiltresRapportForm, OuvrirShiftForm, ProduitForm, QuantiteForm
from .models import Arret, Correction, Creneau, Shift, Troncon
from .rapport import construire_rapport, periodes_rapides, selectionner_shifts, veille

NOMBRE_DERNIERS_SHIFTS = 6


def creneau_en_cours():
    return calculs.creneau_a_l_heure(timezone.now(), Creneau.objects.filter(actif=True))


def production(request):
    """Saisie : la machine d'abord, puis son shift en cours ou l'ouverture d'un shift."""
    jour, creneau = creneau_en_cours()
    machines = sorted(Machine.objects.all(), key=lambda machine: cle_naturelle(machine.code))
    en_cours = {}
    if creneau:
        en_cours = {shift.machine_id: shift for shift in
                    Shift.objects.filter(jour=jour, creneau=creneau).select_related("equipe")}
    for machine in machines:
        machine.shift_en_cours = en_cours.get(machine.pk)
    machine = next((machine for machine in machines if machine.code == request.GET.get("machine")), None)
    contexte = {"machines": machines, "machine_choisie": machine, "jour": jour, "creneau": creneau}
    if machine:
        initial = {"machine": machine, "jour": jour or timezone.localdate(), "creneau": creneau}
        formulaire = OuvrirShiftForm(request.POST or None, initial=initial)
        if request.method == "POST" and formulaire.is_valid():
            shift = ouvrir_shift(formulaire.cleaned_data, request.user)
            messages.success(request, f"Shift ouvert : {shift}.")
            return redirect(shift)
        contexte.update({
            "form": formulaire,
            "matricules": Matricule.objects.filter(actif=True),
            "derniers_shifts": (Shift.objects.filter(machine=machine).select_related("creneau", "equipe")
                                .prefetch_related("troncons", "arrets")[:NOMBRE_DERNIERS_SHIFTS]),
        })
    return render(request, "production/production.html", contexte)


def ouvrir_shift(donnees, utilisateur):
    debut, fin = donnees["creneau"].bornes(donnees["jour"])
    return Shift.objects.create(
        machine=donnees["machine"], jour=donnees["jour"], creneau=donnees["creneau"], equipe=donnees["equipe"],
        matricule=Matricule.objects.get_or_create(numero=donnees["matricule"])[0], debut=debut, fin=fin,
        ouvert_par=utilisateur,
    )


def peut_voir_le_rapport(user):
    return roles.a_le_droit(user, "production_consulter") or roles.a_le_droit(user, "production_saisir")


def peut_modifier(user, shift):
    """Le shift se complète jusqu'à sa fin ; ensuite, seuls les profils qui corrigent le modifient."""
    if roles.a_le_droit(user, "production_corriger"):
        return True
    return roles.a_le_droit(user, "production_saisir") and not shift.est_termine()


def charger_shift(pk):
    return get_object_or_404(
        Shift.objects.select_related("machine", "creneau", "equipe", "matricule", "ouvert_par")
        .prefetch_related("troncons__produit", "arrets__cause", "arrets__troncon__produit", "corrections__par"),
        pk=pk)


def shift(request, pk):
    if not peut_voir_le_rapport(request.user):
        raise PermissionDenied
    le_shift = charger_shift(pk)
    modifiable = peut_modifier(request.user, le_shift)
    if request.method == "POST":
        if not modifiable:
            raise PermissionDenied
        reponse = traiter_saisie(request, le_shift)
        if reponse:
            return reponse
    formulaires = getattr(request, "formulaires_en_erreur", {})
    contexte = {
        "shift": le_shift,
        "bilan": le_shift.bilan(),
        "modifiable": modifiable,
        "correction": modifiable and le_shift.est_termine(),
        "form_produit": formulaires.get("produit") or ProduitForm(shift=le_shift, initial=initial_produit(le_shift)),
        "form_arret": formulaires.get("arret") or ArretForm(shift=le_shift),
        "troncon_en_erreur": formulaires.get("troncon"),
        "form_quantite_en_erreur": formulaires.get("quantite"),
        "peut_sortir_du_stock": roles.a_le_droit(request.user, "stock_mouvements"),
        "peut_faire_une_remontee": roles.a_le_droit(request.user, "remontees_saisir"),
    }
    return render(request, "production/shift.html", contexte)


def initial_produit(le_shift):
    """Premier produit : début du shift et produit de la dernière fiche ; changement : maintenant."""
    if le_shift.troncon_en_cours() is None:
        return {"heure": timezone.localtime(le_shift.debut).time()}
    maintenant = timezone.now()
    if le_shift.debut <= maintenant < le_shift.fin:
        return {"heure": timezone.localtime(maintenant).time().replace(second=0, microsecond=0)}
    return {}


def traiter_saisie(request, le_shift):
    """Actions du formulaire de saisie ; renvoie une redirection, ou None pour réafficher les erreurs."""
    action = request.POST.get("action")
    if action == "produit":
        formulaire = ProduitForm(request.POST, shift=le_shift)
        if formulaire.is_valid():
            description = enregistrer_produit(le_shift, formulaire)
            return apres_saisie(request, le_shift, description)
        request.formulaires_en_erreur = {"produit": formulaire}
    elif action == "quantite":
        troncon = get_object_or_404(le_shift.troncons, pk=request.POST.get("troncon"))
        formulaire = QuantiteForm(request.POST)
        if formulaire.is_valid():
            troncon.compteur_debut = formulaire.cleaned_data["compteur_debut"]
            troncon.compteur_fin = formulaire.cleaned_data["compteur_fin"]
            troncon.save(update_fields=["compteur_debut", "compteur_fin"])
            return apres_saisie(request, le_shift, f"Quantité de {troncon.produit.reference} : {troncon.quantite}.")
        request.formulaires_en_erreur = {"troncon": troncon.pk, "quantite": formulaire}
    elif action == "retirer_produit":
        troncon = get_object_or_404(le_shift.troncons.select_related("produit"), pk=request.POST.get("troncon"))
        troncon.delete()
        return apres_saisie(request, le_shift, f"Produit {troncon.produit.reference} retiré du shift.")
    elif action == "arret":
        formulaire = ArretForm(request.POST, shift=le_shift)
        if formulaire.is_valid():
            donnees = formulaire.cleaned_data
            arret = Arret.objects.create(shift=le_shift, troncon=donnees["troncon"], cause=donnees["cause"],
                                         duree=donnees["duree"], commentaire=donnees["commentaire"],
                                         saisi_par=request.user)
            return apres_saisie(request, le_shift, f"Arrêt ajouté : {arret.cause} {arret.duree} min.")
        request.formulaires_en_erreur = {"arret": formulaire}
    elif action == "retirer_arret":
        arret = get_object_or_404(le_shift.arrets.select_related("cause"), pk=request.POST.get("arret"))
        arret.delete()
        return apres_saisie(request, le_shift, f"Arrêt retiré : {arret.cause} {arret.duree} min.")
    else:
        messages.error(request, "Action inconnue.")
        return redirect(le_shift)
    return None


@transaction.atomic
def enregistrer_produit(le_shift, formulaire):
    donnees = formulaire.cleaned_data
    precedent = formulaire.precedent
    if precedent and donnees.get("compteur_fin_precedent") is not None:
        precedent.compteur_fin = donnees["compteur_fin_precedent"]
        precedent.save(update_fields=["compteur_fin"])
    fiche = ProduitMachine.objects.filter(produit=donnees["produit"], machine=le_shift.machine).first()
    Troncon.objects.create(shift=le_shift, produit=donnees["produit"], debut=donnees["debut"],
                           compteur_debut=donnees.get("compteur_debut") or 0, cadence=fiche.cadence if fiche else None)
    heure = f"{timezone.localtime(donnees['debut']):%H:%M}"
    if precedent:
        return f"Changement de produit à {heure} : {precedent.produit.reference} → {donnees['produit'].reference}."
    return f"Produit {donnees['produit'].reference} démarré à {heure}."


def apres_saisie(request, le_shift, description):
    if le_shift.est_termine():
        Correction.objects.create(shift=le_shift, par=request.user, description=description)
        description += " Correction notée dans l'historique du shift."
    messages.success(request, description)
    return redirect(le_shift)


def filtres_du_rapport(request):
    """Filtres lus dans l'adresse ; sans le droit de consulter, la période est forcée sur la veille."""
    formulaire = FiltresRapportForm(request.GET or None)
    filtres = formulaire.cleaned_data if formulaire.is_valid() else {}
    hier = veille()
    du, au = filtres.get("du") or hier, filtres.get("au") or hier
    restreint = not roles.a_le_droit(request.user, "production_consulter")
    if restreint:
        du = au = hier
    if au < du:
        du, au = au, du
    autres = {cle: filtres.get(cle) for cle in ("machine", "equipe", "creneau", "produit", "cause")}
    return formulaire, du, au, autres, restreint


def rapport_production(request):
    if not peut_voir_le_rapport(request.user):
        raise PermissionDenied
    formulaire, du, au, autres, restreint = filtres_du_rapport(request)
    contexte = construire_rapport(selectionner_shifts(du, au, **autres), du, au)
    contexte.update({
        "form": formulaire, "du": du, "au": au, "restreint": restreint, "filtres_actifs": any(autres.values()),
        "periodes": [] if restreint else periodes_rapides(),
        "adresse_export": adresse_export(request),
    })
    return render(request, "production/rapport.html", contexte)


def adresse_export(request):
    """L'export reprend les filtres de la page ; la démo statique n'exporte que la veille (un seul fichier)."""
    adresse = reverse("export_rapport_production")
    if request.GET and not settings.DEMO_STATIQUE:
        adresse += f"?{request.GET.urlencode()}"
    return adresse


def export_rapport_production(request):
    if not peut_voir_le_rapport(request.user):
        raise PermissionDenied
    _, du, au, autres, _ = filtres_du_rapport(request)
    contenu = excel.exporter(selectionner_shifts(du, au, **autres))
    reponse = HttpResponse(contenu, content_type=excel.TYPE_XLSX)
    reponse["Content-Disposition"] = f'attachment; filename="rapport-production-{du:%Y%m%d}-{au:%Y%m%d}.xlsx"'
    return reponse
