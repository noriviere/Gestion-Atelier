from datetime import date

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from comptes import roles
from comptes.decorators import modification_requise
from inventaire.models import Fournisseur
from inventaire.views import articles_sous_le_mini, lire_quantite

from .models import Commande, renseigner_commandes_en_cours

EN_COURS = "en_cours"


def trier_pour_le_suivi(commandes):
    """Commandes en cours d'abord, la livraison la plus urgente en tête ; puis les autres, des plus récentes aux plus anciennes."""
    commandes = list(commandes)
    en_cours = sorted((commande for commande in commandes if commande.est_en_cours),
                      key=lambda commande: (commande.date_prevue or date.max, commande.numero))
    terminees = [commande for commande in commandes if not commande.est_en_cours]
    return en_cours + terminees


def correspond_a_la_recherche(commande, recherche):
    textes = [commande.numero, commande.numero_fournisseur, commande.fournisseur.nom]
    textes += [ligne.article.reference for ligne in commande.lignes.all()]
    return any(recherche.lower() in texte.lower() for texte in textes)


def filtrer_commandes(commandes, etat="", fournisseur_id="", seulement_en_retard=False, recherche=""):
    selection = []
    for commande in commandes:
        if recherche and not correspond_a_la_recherche(commande, recherche):
            continue
        if etat == EN_COURS and not commande.est_en_cours:
            continue
        if etat and etat != EN_COURS and commande.etat != etat:
            continue
        if fournisseur_id and str(commande.fournisseur_id) != fournisseur_id:
            continue
        if seulement_en_retard and not commande.en_retard:
            continue
        selection.append(commande)
    return selection


def commandes(request):
    toutes_les_commandes = trier_pour_le_suivi(
        Commande.objects.select_related("fournisseur").prefetch_related("lignes__article")
    )
    commandes_en_cours = [commande for commande in toutes_les_commandes if commande.est_en_cours]
    etat = request.GET.get("etat", EN_COURS)
    fournisseur_id = request.GET.get("fournisseur", "")
    seulement_en_retard = bool(request.GET.get("retard"))
    if settings.DEMO_STATIQUE:
        # Démo statique : toutes les lignes sont dans la page, demo.js masque celles hors filtre.
        commandes_affichees = toutes_les_commandes
    else:
        commandes_affichees = filtrer_commandes(toutes_les_commandes, etat, fournisseur_id, seulement_en_retard,
                                                request.GET.get("q", "").strip())
    return render(
        request,
        "commandes/commandes.html",
        {
            "commandes": commandes_affichees,
            "nombre_en_cours": len(commandes_en_cours),
            "nombre_en_retard": sum(1 for commande in commandes_en_cours if commande.en_retard),
            "nombre_a_receptionner": sum(1 for commande in commandes_en_cours if commande.etat == Commande.RECUE),
            "montant_en_cours": sum(commande.montant_total for commande in commandes_en_cours),
            "fournisseurs": Fournisseur.objects.filter(commandes__isnull=False).distinct(),
            "etats": Commande.ETATS,
            "etat_choisi": etat,
            "filtres": request.GET,
        },
    )


def lire_quantites_recues(commande, donnees_formulaire):
    """{ligne: quantité} d'après les champs recu_<id de ligne> ; ValueError si une saisie est illisible ou négative."""
    quantites_recues = {}
    for ligne in commande.lignes.select_related("article"):
        texte = donnees_formulaire.get(f"recu_{ligne.pk}", "")
        try:
            quantite = lire_quantite(texte)
        except ValueError:
            raise ValueError(f"Quantité illisible pour {ligne.article.reference} : « {texte} ».")
        if quantite is not None and quantite < 0:
            raise ValueError(f"Quantité négative pour {ligne.article.reference}.")
        if quantite is not None:
            quantites_recues[ligne] = quantite
    return quantites_recues


def commande(request, pk):
    commande = get_object_or_404(Commande.objects.select_related("fournisseur", "cree_par"), pk=pk)
    if request.method == "POST":
        action = request.POST.get("action")
        reservee_methode = action in (Commande.PASSEE, Commande.ANNULEE)
        autorise = roles.peut_modifier(request.user) if reservee_methode else roles.peut_mouvementer(request.user)
        if not autorise:
            raise PermissionDenied
        try:
            if action == Commande.RECEPTIONNEE:
                commande.receptionner(lire_quantites_recues(commande, request.POST), utilisateur=request.user)
                messages.success(request, "Commande réceptionnée : les quantités sont entrées en stock.")
            else:
                if action == Commande.PASSEE:
                    commande.numero_fournisseur = request.POST.get("numero_fournisseur", "").strip()
                    if request.POST.get("date_prevue"):
                        commande.date_prevue = date.fromisoformat(request.POST["date_prevue"])
                commande.changer_etat(action, utilisateur=request.user)
                messages.success(request, f"Commande {commande.get_etat_display().lower()}.")
        except ValueError as erreur:
            messages.error(request, str(erreur))
        return redirect(commande)
    return render(
        request,
        "commandes/commande.html",
        {
            "commande": commande,
            "lignes": commande.lignes.select_related("article"),
            "peut_passer": roles.peut_modifier(request.user) and Commande.PASSEE in commande.etats_suivants,
            "peut_annuler": roles.peut_modifier(request.user) and Commande.ANNULEE in commande.etats_suivants,
            "peut_marquer_recue": roles.peut_mouvementer(request.user) and Commande.RECUE in commande.etats_suivants,
            "peut_receptionner": roles.peut_mouvementer(request.user) and Commande.RECEPTIONNEE in commande.etats_suivants,
        },
    )


@require_POST
@modification_requise
def creer_commande(request, fournisseur_pk):
    """Prépare une commande en attente avec ce qui reste à commander chez ce fournisseur préféré."""
    fournisseur = get_object_or_404(Fournisseur, pk=fournisseur_pk)
    articles_du_fournisseur = [
        article for article in renseigner_commandes_en_cours(articles_sous_le_mini())
        if article.reste_a_commander > 0
        and any(lien.prefere and lien.fournisseur_id == fournisseur.pk for lien in article.liens_fournisseurs.all())
    ]
    if not articles_du_fournisseur:
        messages.error(request, f"Rien à commander chez {fournisseur} : les besoins sont déjà couverts.")
        return redirect("a_commander")
    nouvelle_commande = Commande.creer_pour_les_besoins(fournisseur, articles_du_fournisseur, utilisateur=request.user)
    messages.success(request, f"Commande {nouvelle_commande.numero} préparée. Vérifiez-la puis passez-la.")
    return redirect(nouvelle_commande)
