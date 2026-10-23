from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render

from comptes import roles
from outillage.models import Outil
from produits.models import Produit

from .forms import MouvementForm
from .models import Article, Fournisseur, Mouvement, TypeInventaire


def _articles_a_commander():
    return (
        Article.objects.filter(stock__lte=F("stock_mini"))
        .select_related("type_inventaire")
        .prefetch_related("liens_fournisseurs__fournisseur")
    )


def _articles_a_compter(type_inventaire, tous=False):
    articles = type_inventaire.articles.order_by("emplacement", "reference")
    if tous:
        return list(articles)
    return [a for a in articles if a.inventaire_du]


def accueil(request):
    a_commander = list(_articles_a_commander())
    inventaires_dus = sum(1 for a in Article.objects.all() if a.inventaire_du)
    return render(
        request,
        "inventaire/accueil.html",
        {
            "a_commander": a_commander[:8],
            "nb_a_commander": len(a_commander),
            "nb_inventaires_dus": inventaires_dus,
            "nb_articles": Article.objects.count(),
            "nb_outils": Outil.objects.filter(parent__isnull=True).count(),
            "nb_produits": Produit.objects.count(),
            "derniers_mouvements": Mouvement.objects.select_related("article", "utilisateur")[:6],
        },
    )


def articles(request):
    qs = Article.objects.select_related("type_inventaire")
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(reference__icontains=q) | Q(designation__icontains=q) | Q(emplacement__icontains=q))
    categorie = request.GET.get("categorie", "")
    if categorie:
        qs = qs.filter(categorie=categorie)
    type_id = request.GET.get("type", "")
    if type_id:
        qs = qs.filter(type_inventaire_id=type_id)
    if request.GET.get("alerte"):
        qs = qs.filter(stock__lte=F("stock_mini"))
    return render(
        request,
        "inventaire/articles.html",
        {
            "articles": qs,
            "types": TypeInventaire.objects.all(),
            "categories": Article.CATEGORIES,
            "filtres": request.GET,
        },
    )


def article(request, pk):
    article = get_object_or_404(Article.objects.select_related("type_inventaire"), pk=pk)
    form = MouvementForm(request.POST or None)
    if request.method == "POST":
        if not roles.peut_mouvementer(request.user):
            raise PermissionDenied
        if form.is_valid():
            Mouvement.enregistrer(
                article,
                form.cleaned_data["type"],
                form.cleaned_data["quantite"],
                utilisateur=request.user,
                commentaire=form.cleaned_data["commentaire"],
            )
            messages.success(request, "Mouvement enregistré.")
            return redirect(article)
    return render(
        request,
        "inventaire/article.html",
        {
            "article": article,
            "form": form,
            "liens_fournisseurs": article.liens_fournisseurs.select_related("fournisseur"),
            "liens_outils": article.liens_outils.select_related("outil"),
            "consommations": article.consommations.select_related("fabrication__produit", "fabrication__machine"),
            "mouvements": article.mouvements.select_related("utilisateur")[:15],
        },
    )


def a_commander(request):
    """Articles sous le stock mini, regroupés par fournisseur préféré."""
    groupes = defaultdict(list)
    for art in _articles_a_commander():
        prefere = next((l for l in art.liens_fournisseurs.all() if l.prefere), None)
        groupes[prefere.fournisseur if prefere else None].append((art, prefere))
    fournisseurs = sorted((f for f in groupes if f), key=lambda f: f.nom)
    lignes = [(f, groupes[f]) for f in fournisseurs]
    if None in groupes:
        lignes.append((None, groupes[None]))
    return render(request, "inventaire/a_commander.html", {"groupes": lignes})


def inventaires(request):
    types = []
    for t in TypeInventaire.objects.all():
        articles = list(t.articles.all())
        types.append({"type": t, "total": len(articles), "dus": sum(1 for a in articles if a.inventaire_du)})
    return render(request, "inventaire/inventaires.html", {"types": types})


def comptage(request, pk):
    type_inventaire = get_object_or_404(TypeInventaire, pk=pk)
    tous = bool(request.GET.get("tous"))
    articles = _articles_a_compter(type_inventaire, tous)
    if request.method == "POST":
        if not roles.peut_mouvementer(request.user):
            raise PermissionDenied
        nb = 0
        for art in type_inventaire.articles.all():
            valeur = request.POST.get(f"compte_{art.pk}", "").strip().replace(",", ".")
            if not valeur:
                continue
            try:
                quantite = Decimal(valeur)
            except InvalidOperation:
                messages.error(request, f"Quantité illisible pour {art.reference} : « {valeur} ».")
                continue
            Mouvement.enregistrer(art, Mouvement.INVENTAIRE, quantite, utilisateur=request.user)
            nb += 1
        messages.success(request, f"{nb} comptage(s) enregistré(s), stocks corrigés.")
        return redirect("comptage", pk=pk)
    return render(
        request,
        "inventaire/comptage.html",
        {"type_inventaire": type_inventaire, "articles": articles, "tous": tous},
    )


def feuille_comptage(request, pk):
    type_inventaire = get_object_or_404(TypeInventaire, pk=pk)
    tous = bool(request.GET.get("tous"))
    return render(
        request,
        "inventaire/feuille_comptage.html",
        {
            "type_inventaire": type_inventaire,
            "articles": _articles_a_compter(type_inventaire, tous),
            "tous": tous,
        },
    )
