from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render

from commandes.models import Commande, renseigner_commandes_en_cours
from comptes import roles
from outillage.models import Outil
from produits.models import Produit

from .forms import MouvementForm
from .models import Article, Mouvement, TypeInventaire
from .recherche import rechercher


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


def recherche(request):
    texte_recherche = request.GET.get("q", "").strip()
    return render(
        request,
        "inventaire/recherche.html",
        {"texte_recherche": texte_recherche, "groupes": rechercher(texte_recherche)},
    )


def articles(request):
    selection = Article.objects.select_related("type_inventaire")
    recherche = request.GET.get("q", "").strip()
    if recherche:
        selection = selection.filter(
            Q(reference__icontains=recherche) | Q(designation__icontains=recherche) | Q(emplacement__icontains=recherche)
        )
    categorie = request.GET.get("categorie", "")
    if categorie:
        selection = selection.filter(categorie=categorie)
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
        if not roles.peut_mouvementer(request.user):
            raise PermissionDenied
        nombre_comptages = 0
        for article in type_inventaire.articles.all():
            try:
                quantite_comptee = lire_quantite(request.POST.get(f"compte_{article.pk}", ""))
            except ValueError as erreur:
                messages.error(request, f"Quantité illisible pour {article.reference} : « {erreur} ».")
                continue
            if quantite_comptee is None:
                continue
            Mouvement.enregistrer(article, Mouvement.INVENTAIRE, quantite_comptee, utilisateur=request.user)
            nombre_comptages += 1
        messages.success(request, f"{nombre_comptages} comptage(s) enregistré(s), stocks corrigés.")
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
