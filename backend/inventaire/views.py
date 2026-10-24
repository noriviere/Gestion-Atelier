from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from commandes.models import Commande, renseigner_commandes_en_cours
from comptes import roles
from outillage.models import Outil
from produits.models import Produit

from .forms import MouvementForm
from .models import Article, Mouvement, TypeInventaire


def articles_sous_le_mini():
    return (
        Article.objects.filter(stock__lte=F("stock_mini"))
        .select_related("type_inventaire")
        .prefetch_related("liens_fournisseurs__fournisseur")
    )


def articles_a_compter(type_inventaire, tous_les_articles=False):
    """Articles du type, rangés par emplacement ; seulement ceux dont le comptage est dû, sauf demande contraire."""
    articles = type_inventaire.articles.order_by("emplacement", "reference")
    if tous_les_articles:
        return list(articles)
    return [article for article in articles if article.inventaire_du]


def regrouper_par_fournisseur_prefere(articles):
    """Liste de (fournisseur, [(article, lien_fournisseur), ...]), fournisseurs triés par nom, sans fournisseur en dernier."""
    commandes = defaultdict(list)
    for article in articles:
        lien_prefere = next((lien for lien in article.liens_fournisseurs.all() if lien.prefere), None)
        fournisseur = lien_prefere.fournisseur if lien_prefere else None
        commandes[fournisseur].append((article, lien_prefere))
    fournisseurs_tries = sorted((fournisseur for fournisseur in commandes if fournisseur is not None), key=lambda fournisseur: fournisseur.nom)
    resultat = [(fournisseur, commandes[fournisseur]) for fournisseur in fournisseurs_tries]
    if None in commandes:
        resultat.append((None, commandes[None]))
    return resultat


PERIODES_ECARTS = [(30, "30 derniers jours"), (90, "3 derniers mois"), (365, "12 derniers mois")]
PERIODE_ECARTS_PAR_DEFAUT = 90


def formater_ecart(ecart):
    """+2, −1,5 : l'écart avec son signe, en notation française."""
    texte = f"{abs(ecart).normalize():f}".replace(".", ",")
    return f"+{texte}" if ecart > 0 else f"−{texte}" if ecart < 0 else "0"


def resumer_ecarts(comptages):
    """Chiffres clés d'une liste de comptages : nombre, écarts, part des comptages justes et valeur des écarts."""
    comptages = list(comptages)
    avec_ecart = [comptage for comptage in comptages if comptage.ecart]
    valeurs = [comptage.valeur_ecart for comptage in avec_ecart if comptage.valeur_ecart is not None]
    return {
        "nombre_comptages": len(comptages),
        "nombre_ecarts": len(avec_ecart),
        "taux_exactitude": round(100 * (len(comptages) - len(avec_ecart)) / len(comptages)) if comptages else None,
        "valeur_manquants": sum((valeur for valeur in valeurs if valeur < 0), Decimal(0)),
        "valeur_surplus": sum((valeur for valeur in valeurs if valeur > 0), Decimal(0)),
        "valeur_nette": sum(valeurs, Decimal(0)),
    }


def lire_quantite(texte):
    """Convertit une saisie (« 12 », « 3,5 ») en Decimal ; None si vide, ValueError si illisible."""
    texte = texte.strip().replace(",", ".")
    if not texte:
        return None
    try:
        return Decimal(texte)
    except InvalidOperation:
        raise ValueError(texte)


def accueil(request):
    liste_a_commander = renseigner_commandes_en_cours(articles_sous_le_mini())
    commandes_en_cours = Commande.objects.en_cours().prefetch_related("lignes")
    return render(
        request,
        "inventaire/accueil.html",
        {
            "articles_a_commander": liste_a_commander[:8],
            "nombre_a_commander": len(liste_a_commander),
            "nombre_non_couverts": sum(1 for article in liste_a_commander if not article.couvert_par_commande),
            "nombre_commandes_en_cours": len(commandes_en_cours),
            "nombre_commandes_en_retard": sum(1 for commande in commandes_en_cours if commande.en_retard),
            "nombre_inventaires_dus": sum(1 for article in Article.objects.all() if article.inventaire_du),
            "nombre_articles": Article.objects.count(),
            "nombre_outils": Outil.objects.filter(parent__isnull=True).count(),
            "nombre_produits": Produit.objects.count(),
            "derniers_mouvements": Mouvement.objects.select_related("article", "utilisateur")[:6],
        },
    )


def articles(request):
    selection = Article.objects.select_related("type_inventaire")
    recherche = request.GET.get("q", "").strip()
    if recherche:
        selection = selection.filter(
            Q(reference__icontains=recherche) | Q(designation__icontains=recherche) | Q(emplacement__icontains=recherche)
            | Q(numero_plan__icontains=recherche)
        )
    categorie = request.GET.get("categorie", "")
    if categorie:
        selection = selection.filter(categorie=categorie)
    origine = request.GET.get("origine", "")
    if origine:
        selection = selection.filter(origine=origine)
    type_inventaire_id = request.GET.get("type", "")
    if type_inventaire_id:
        selection = selection.filter(type_inventaire_id=type_inventaire_id)
    if request.GET.get("alerte"):
        selection = selection.filter(stock__lte=F("stock_mini"))
    return render(
        request,
        "inventaire/articles.html",
        {
            "articles": renseigner_commandes_en_cours(selection),
            "types_inventaire": TypeInventaire.objects.all(),
            "categories": Article.CATEGORIES,
            "origines": Article.ORIGINES,
            "filtres": request.GET,
        },
    )


def article(request, pk):
    article = get_object_or_404(Article.objects.select_related("type_inventaire"), pk=pk)
    formulaire = MouvementForm(request.POST or None)
    if request.method == "POST":
        if not roles.peut_mouvementer(request.user):
            raise PermissionDenied
        if formulaire.is_valid():
            Mouvement.enregistrer(
                article,
                formulaire.cleaned_data["type"],
                formulaire.cleaned_data["quantite"],
                utilisateur=request.user,
                commentaire=formulaire.cleaned_data["commentaire"],
            )
            messages.success(request, "Mouvement enregistré.")
            return redirect(article)
    return render(
        request,
        "inventaire/article.html",
        {
            "article": article,
            "form": formulaire,
            "liens_fournisseurs": article.liens_fournisseurs.select_related("fournisseur"),
            "liens_outils": article.liens_outils.select_related("outil"),
            "consommations": article.consommations.select_related("fabrication__produit", "fabrication__machine"),
            "mouvements": article.mouvements.select_related("utilisateur")[:15],
            "lignes_en_cours": renseigner_commandes_en_cours([article])[0].lignes_en_cours,
        },
    )


def a_commander(request):
    commandes_par_fournisseur = [
        (fournisseur, lignes_commande, any(article.reste_a_commander > 0 for article, _ in lignes_commande))
        for fournisseur, lignes_commande in regrouper_par_fournisseur_prefere(
            renseigner_commandes_en_cours(articles_sous_le_mini())
        )
    ]
    return render(request, "inventaire/a_commander.html", {"commandes_par_fournisseur": commandes_par_fournisseur})


def inventaires(request):
    resumes_par_type = []
    for type_inventaire in TypeInventaire.objects.all():
        articles_du_type = list(type_inventaire.articles.all())
        resumes_par_type.append({
            "type_inventaire": type_inventaire,
            "nombre_articles": len(articles_du_type),
            "nombre_a_compter": sum(1 for article in articles_du_type if article.inventaire_du),
        })
    return render(request, "inventaire/inventaires.html", {"resumes_par_type": resumes_par_type})


def comptage(request, pk):
    type_inventaire = get_object_or_404(TypeInventaire, pk=pk)
    tous_les_articles = bool(request.GET.get("tous"))
    if request.method == "POST":
        if not roles.peut_compter(request.user):
            raise PermissionDenied
        comptages = []
        for article in type_inventaire.articles.all():
            try:
                quantite_comptee = lire_quantite(request.POST.get(f"compte_{article.pk}", ""))
            except ValueError as erreur:
                messages.error(request, f"Quantité illisible pour {article.reference} : « {erreur} ».")
                continue
            if quantite_comptee is None:
                continue
            comptages.append(
                Mouvement.enregistrer(article, Mouvement.INVENTAIRE, quantite_comptee, utilisateur=request.user)
            )
        ecarts = [f"{comptage.article.reference} {formater_ecart(comptage.ecart)}" for comptage in comptages if comptage.ecart]
        bilan = f"{len(comptages)} comptage(s) enregistré(s), stocks corrigés."
        if ecarts:
            bilan += f" {len(ecarts)} écart(s) : {', '.join(ecarts)}."
        elif comptages:
            bilan += " Aucun écart."
        messages.success(request, bilan)
        return redirect("comptage", pk=pk)
    return render(
        request,
        "inventaire/comptage.html",
        {
            "type_inventaire": type_inventaire,
            "articles": articles_a_compter(type_inventaire, tous_les_articles),
            "tous_les_articles": tous_les_articles,
        },
    )


def feuille_comptage(request, pk):
    type_inventaire = get_object_or_404(TypeInventaire, pk=pk)
    tous_les_articles = bool(request.GET.get("tous"))
    return render(
        request,
        "inventaire/feuille_comptage.html",
        {
            "type_inventaire": type_inventaire,
            "articles": articles_a_compter(type_inventaire, tous_les_articles),
            "tous_les_articles": tous_les_articles,
        },
    )


def ecarts(request):
    filtres_envoyes = "periode" in request.GET
    periodes_possibles = {str(jours): jours for jours, _ in PERIODES_ECARTS}
    periode = periodes_possibles.get(request.GET.get("periode", ""), PERIODE_ECARTS_PAR_DEFAUT)
    type_inventaire_id = request.GET.get("type", "")
    seulement_les_ecarts = bool(request.GET.get("ecart")) if filtres_envoyes else True

    aujourdhui = timezone.localdate()
    plus_longue_periode = max(jours for jours, _ in PERIODES_ECARTS)
    comptages = list(
        Mouvement.objects.filter(type=Mouvement.INVENTAIRE, ecart__isnull=False,
                                 date__date__gte=aujourdhui - timedelta(days=plus_longue_periode))
        .select_related("article__type_inventaire", "utilisateur")
        .prefetch_related("article__liens_fournisseurs")
    )
    if type_inventaire_id:
        comptages = [comptage for comptage in comptages if str(comptage.article.type_inventaire_id) == type_inventaire_id]
    for comptage in comptages:
        jour_du_comptage = timezone.localtime(comptage.date).date()
        # Périodes dans lesquelles tombe le comptage : sert au filtre de la démo statique.
        comptage.periodes = " ".join(str(jours) for jours, _ in PERIODES_ECARTS
                                     if jour_du_comptage >= aujourdhui - timedelta(days=jours))
    comptages_de_la_periode = [comptage for comptage in comptages if str(periode) in comptage.periodes.split()]
    if settings.DEMO_STATIQUE:
        # Démo statique : toutes les lignes sont dans la page, demo.js masque celles hors filtre.
        comptages_affiches = comptages
    else:
        comptages_affiches = [comptage for comptage in comptages_de_la_periode if comptage.ecart or not seulement_les_ecarts]
    return render(
        request,
        "inventaire/ecarts.html",
        {
            "comptages": comptages_affiches,
            "resume": resumer_ecarts(comptages_de_la_periode),
            "periodes": PERIODES_ECARTS,
            "periode": periode,
            "types_inventaire": TypeInventaire.objects.all(),
            "type_inventaire_id": type_inventaire_id,
            "seulement_les_ecarts": seulement_les_ecarts,
        },
    )
