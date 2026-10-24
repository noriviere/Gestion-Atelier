"""Calculs et lectures de saisie du stock, partagés par les vues du stock, des commandes et les gabarits."""
from decimal import Decimal, InvalidOperation

from django.db.models import F

from .models import Article


def articles_sous_le_mini():
    return (
        Article.objects.filter(stock__lte=F("stock_mini"))
        .select_related("type_inventaire")
        .prefetch_related("liens_fournisseurs__fournisseur")
    )


# Plus grande quantité enregistrable : les champs de quantité ont 10 chiffres dont 2 après la virgule.
QUANTITE_MAXI = Decimal("99999999")


def lire_quantite(texte):
    """Convertit une saisie (« 12 », « 3,5 ») en Decimal ; None si vide.

    ValueError si la saisie est illisible, négative ou trop grande (« NaN » et « Infinity » compris)."""
    texte = texte.strip().replace(",", ".")
    if not texte:
        return None
    try:
        quantite = Decimal(texte)
    except InvalidOperation:
        raise ValueError(texte)
    if not quantite.is_finite() or quantite < 0 or quantite > QUANTITE_MAXI:
        raise ValueError(texte)
    return quantite


def formater_ecart(ecart):
    """+2, −1,5 : l'écart avec son signe, en notation française."""
    texte = f"{abs(ecart).normalize():f}".replace(".", ",")
    return f"+{texte}" if ecart > 0 else f"−{texte}" if ecart < 0 else "0"
