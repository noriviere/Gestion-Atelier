from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from comptes import roles
from outillage.views import construire_arbre

from . import matrice
from .forms import (ConsommationsFormSet, DocumentForm, DuplicationProduitForm, FicheForm, ProduitForm, ReglagesForm,
                    formset_parametres)
from .models import Document, Machine, Produit, ProduitMachine


def objet_ou_404(modele, identifiant):
    """L'objet dont l'identifiant vient d'un formulaire ou de l'adresse ; 404 s'il est illisible ou inconnu."""
    if not str(identifiant or "").isdigit():
        raise Http404
    return get_object_or_404(modele, pk=identifiant)


def produits(request):
    """Matrice produits × machines : une ligne par produit, une case par machine."""
    machines = sorted(Machine.objects.all(), key=lambda machine: matrice.cle_naturelle(machine.code))
    produits_tries = sorted(Produit.objects.all(), key=lambda produit: matrice.cle_naturelle(produit.reference))
    toutes_les_lignes = matrice.construire_matrice(produits_tries, machines, ProduitMachine.objects.all())
    recherche = request.GET.get("q", "").strip()
    vue = request.GET.get("vue", "")
    if settings.DEMO_STATIQUE:
        # Démo statique : toutes les lignes sont dans la page, demo.js masque celles hors filtre.
        lignes = toutes_les_lignes
    else:
        lignes = matrice.filtrer_lignes(toutes_les_lignes, recherche, vue)
    return render(
        request,
        "produits/produits.html",
        {
            "machines": machines,
            "lignes": lignes,
            "totaux": matrice.totaux(toutes_les_lignes),
            "recherche": recherche,
            "vue": vue,
            "vues": matrice.VUES,
            "etats": [(code, matrice.LIBELLES[code]) for code in
                      (ProduitMachine.PROGRAMME, ProduitMachine.A_FAIRE, ProduitMachine.NON_FAISABLE, matrice.VIDE)],
        },
    )


def reponse_case(case):
    """Ce que la matrice doit savoir d'une case après un changement d'état ; matrice.js recalcule l'affichage de la ligne."""
    avec_fiche = case is not None and case.a_une_fiche
    return {
        "etat": case.etat if case else "",
        "fiche": case.get_absolute_url() if avec_fiche else "",
        "modifier": reverse("modifier_fiche", args=[case.pk]) if avec_fiche else "",
        "dupliquer": reverse("dupliquer_fiche", args=[case.pk]) if avec_fiche else "",
    }


@require_POST
def changer_etat(request):
    produit = objet_ou_404(Produit, request.POST.get("produit"))
    machine = objet_ou_404(Machine, request.POST.get("machine"))
    etat = request.POST.get("etat", "")
    try:
        case = ProduitMachine.changer_etat(produit, machine, etat)
    except ValueError as erreur:
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"erreur": str(erreur)}, status=400)
        messages.error(request, str(erreur))
        return redirect("produits")
    if request.headers.get("Accept") == "application/json":
        return JsonResponse(reponse_case(case))
    return redirect(f"{reverse('produits')}#produit-{produit.pk}")


def produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    fabrications = list(produit.fabrications.select_related("machine"))
    nombre_programmees = sum(1 for fabrication in fabrications if fabrication.etat == ProduitMachine.PROGRAMME)
    for fabrication in fabrications:
        fabrication.etat_affiche = matrice.etat_affiche(fabrication.etat, nombre_programmees)
        fabrication.libelle_etat = matrice.LIBELLES[fabrication.etat_affiche]
    return render(
        request,
        "produits/produit.html",
        {
            "produit": produit,
            "fabrications": [fabrication for fabrication in fabrications if fabrication.a_une_fiche],
            "non_faisables": [fabrication.machine for fabrication in fabrications
                              if fabrication.etat == ProduitMachine.NON_FAISABLE],
            "documents": produit.documents.filter(fabrication__isnull=True),
            "formulaire_duplication": DuplicationProduitForm(
                initial={"designation": f"Copie de {produit.designation}"}
            ),
        },
    )


def modifier_produit(request, pk=None):
    produit = get_object_or_404(Produit, pk=pk) if pk else Produit()
    formulaire = ProduitForm(request.POST or None, instance=produit)
    if request.method == "POST" and formulaire.is_valid():
        produit = formulaire.save()
        messages.success(request, f"Produit {produit.reference} enregistré.")
        return redirect(produit)
    return render(request, "produits/produit_formulaire.html", {"produit": produit, "formulaire": formulaire})


@require_POST
def dupliquer_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)
    formulaire = DuplicationProduitForm(request.POST)
    if not formulaire.is_valid():
        for erreurs in formulaire.errors.values():
            messages.error(request, " ".join(erreurs))
        return redirect(produit)
    copie = produit.dupliquer(formulaire.cleaned_data["reference"], formulaire.cleaned_data["designation"])
    messages.success(request, f"{copie.reference} créé à partir de {produit.reference}, avec ses "
                              f"{copie.fabrications.count()} cases de la matrice. Ajustez ce qui diffère.")
    return redirect(copie)


def fiche(request, pk):
    fabrication = get_object_or_404(ProduitMachine.objects.select_related("produit", "machine"), pk=pk)
    if not fabrication.a_une_fiche:
        raise Http404("Cette case de la matrice n'a pas de fiche.")
    documents = Document.objects.filter(
        Q(fabrication__isnull=True) | Q(fabrication=fabrication), produit=fabrication.produit
    ).order_by("fabrication_id", "titre")
    etat = matrice.etat_affiche(
        fabrication.etat, fabrication.produit.fabrications.filter(etat=ProduitMachine.PROGRAMME).count()
    )
    machines_avec_fiche = fabrication.produit.fabrications.filter(
        etat__in=ProduitMachine.ETATS_AVEC_FICHE
    ).values_list("machine_id", flat=True)
    autres_machines = Machine.objects.exclude(pk__in=machines_avec_fiche)
    return render(
        request,
        "produits/fiche.html",
        {
            "fabrication": fabrication,
            "etat": etat,
            "libelle_etat": matrice.LIBELLES[etat],
            "parametres": fabrication.parametres.all(),
            "arbres": [construire_arbre(outil) for outil in fabrication.outils.all()],
            "consommations": fabrication.consommations.select_related("article"),
            "photos": [document for document in documents if document.est_une_image],
            "documents": [document for document in documents if not document.est_une_image],
            "formulaire_document": DocumentForm(),
            "autres_machines": autres_machines,
        },
    )


def parametres_de_depart(machine, produit):
    """Libellés et unités de la dernière fiche de cette machine : la nouvelle fiche n'a plus qu'à remplir les valeurs."""
    modele = (ProduitMachine.objects.filter(machine=machine, parametres__isnull=False).exclude(produit=produit)
              .order_by("-pk").first())
    if not modele:
        return []
    return [{"libelle": parametre.libelle, "unite": parametre.unite} for parametre in modele.parametres.all()]


def enregistrer_parametres_dans_l_ordre(parametres, fabrication):
    """Les paramètres gardent l'ordre des lignes du formulaire ; les lignes laissées vides sont ignorées."""
    parametres.save(commit=False)
    for parametre in parametres.deleted_objects:
        parametre.delete()
    ordre = 0
    for formulaire_parametre in parametres.forms:
        if formulaire_parametre in parametres.deleted_forms:
            continue
        if not formulaire_parametre.instance.pk and not formulaire_parametre.has_changed():
            continue
        formulaire_parametre.instance.fabrication = fabrication
        formulaire_parametre.instance.ordre = ordre
        formulaire_parametre.instance.save()
        ordre += 1


def modifier_fiche(request, pk=None, produit_pk=None):
    """Création (depuis un produit, avec ?machine=) et modification d'une fiche, avec paramètres et consommables.

    Avec le seul droit « réglages », on ne modifie que les paramètres et les notes d'une fiche existante.
    """
    fiche_complete = roles.a_le_droit(request.user, "produits_modifier")
    if not fiche_complete and not (pk and roles.a_le_droit(request.user, "produits_reglages")):
        raise PermissionDenied
    if pk:
        fabrication = get_object_or_404(ProduitMachine.objects.select_related("produit", "machine"), pk=pk)
    else:
        produit = get_object_or_404(Produit, pk=produit_pk)
        machine_id = request.POST.get("machine") or request.GET.get("machine")
        if machine_id:
            machine_id = objet_ou_404(Machine, machine_id).pk
        existante = ProduitMachine.objects.filter(produit=produit, machine_id=machine_id).first() if machine_id else None
        if existante and existante.a_une_fiche and request.method == "GET":
            return redirect("modifier_fiche", existante.pk)
        # Une case « non faisable » ou « possible » devient une fiche : on reprend la ligne existante.
        fabrication = existante or ProduitMachine(produit=produit, machine_id=machine_id or None,
                                                  etat=ProduitMachine.A_FAIRE)
        if existante:
            fabrication.etat = ProduitMachine.A_FAIRE

    lignes_de_depart = []
    if not fabrication.pk and fabrication.machine_id and request.method == "GET":
        lignes_de_depart = parametres_de_depart(fabrication.machine, fabrication.produit)
    ParametresFormSet = formset_parametres(len(lignes_de_depart) or 1)

    donnees = request.POST if request.method == "POST" else None
    formulaire = (FicheForm if fiche_complete else ReglagesForm)(donnees, instance=fabrication)
    parametres = ParametresFormSet(donnees, instance=fabrication, prefix="parametres", initial=lignes_de_depart)
    consommations = ConsommationsFormSet(donnees, instance=fabrication, prefix="consommations") if fiche_complete else None
    if (donnees is not None and formulaire.is_valid() and parametres.is_valid()
            and (consommations is None or consommations.is_valid())):
        with transaction.atomic():
            fabrication = formulaire.save()
            parametres.instance = fabrication
            enregistrer_parametres_dans_l_ordre(parametres, fabrication)
            if consommations is not None:
                consommations.instance = fabrication
                consommations.save()
        messages.success(request, f"Fiche {fabrication} enregistrée.")
        return redirect(fabrication)
    return render(
        request,
        "produits/fiche_formulaire.html",
        {"fabrication": fabrication, "formulaire": formulaire, "fiche_complete": fiche_complete, "parametres": parametres,
         "consommations": consommations, "parametres_repris": bool(lignes_de_depart),
         "titres_parametres": ["Paramètre", "Valeur", "Unité"], "titres_consommations": ["Article", "Quantité / fréquence"]},
    )


@require_POST
def dupliquer_fiche(request, pk):
    source = get_object_or_404(ProduitMachine.objects.select_related("produit", "machine"), pk=pk)
    machine = objet_ou_404(Machine, request.POST.get("machine"))
    try:
        copie = source.dupliquer_vers_machine(machine)
    except ValueError as erreur:
        messages.error(request, str(erreur))
        return redirect(source)
    messages.success(request, f"Fiche copiée de {source.machine.code} vers {machine.code} : ajustez la cadence et "
                              "les paramètres qui changent, puis enregistrez. Les photos propres à "
                              f"{source.machine.code} ne sont pas reprises.")
    return redirect("modifier_fiche", copie.pk)


@require_POST
def ajouter_document(request, pk):
    fabrication = get_object_or_404(ProduitMachine.objects.select_related("produit"), pk=pk)
    formulaire = DocumentForm(request.POST, request.FILES)
    if formulaire.is_valid():
        document = formulaire.save(commit=False)
        document.produit = fabrication.produit
        document.fabrication = fabrication if formulaire.cleaned_data["portee"] == DocumentForm.POUR_LA_FICHE else None
        document.ajoute_par = request.user
        document.save()
        messages.success(request, f"« {document.titre} » ajouté.")
    else:
        for erreurs in formulaire.errors.values():
            messages.error(request, " ".join(erreurs))
    return redirect(f"{fabrication.get_absolute_url()}#documents")


@require_POST
def supprimer_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    retour = request.POST.get("retour") or document.produit.get_absolute_url()
    nom_fichier = document.fichier.name
    document.delete()
    # Un produit ou une fiche dupliqués partagent le fichier : il n'est effacé qu'au dernier document qui s'en sert.
    if not Document.objects.filter(fichier=nom_fichier).exists():
        document.fichier.storage.delete(nom_fichier)
    messages.success(request, f"« {document.titre} » retiré.")
    # Seulement une adresse de ce site : « //autre-site » commence aussi par « / ».
    if not url_has_allowed_host_and_scheme(retour, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        retour = "produits"
    return redirect(retour)


def document(request, pk, nom):
    """Envoie le fichier, après la vérification de connexion faite pour toute l'application."""
    document = get_object_or_404(Document, pk=pk)
    if nom != document.nom_fichier or not document.fichier.storage.exists(document.fichier.name):
        raise Http404
    reponse = FileResponse(document.fichier.open("rb"), filename=document.nom_fichier,
                           as_attachment=not (document.est_une_image or document.extension == "pdf"))
    if document.extension == "svg":
        # Un SVG peut contenir du script : ouvert seul dans un onglet, il ne doit rien pouvoir exécuter.
        reponse["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox"
    return reponse


def machine(request, pk):
    machine = get_object_or_404(Machine, pk=pk)
    fabrications = list(machine.fabrications.select_related("produit"))
    for fabrication in fabrications:
        nombre_programmees = fabrication.produit.fabrications.filter(etat=ProduitMachine.PROGRAMME).count()
        fabrication.etat_affiche = matrice.etat_affiche(fabrication.etat, nombre_programmees)
        fabrication.libelle_etat = matrice.LIBELLES[fabrication.etat_affiche]
    return render(
        request,
        "produits/machine.html",
        {
            "machine": machine,
            "fabrications": [fabrication for fabrication in fabrications if fabrication.a_une_fiche],
            "non_faisables": [fabrication.produit for fabrication in fabrications
                              if fabrication.etat == ProduitMachine.NON_FAISABLE],
        },
    )
